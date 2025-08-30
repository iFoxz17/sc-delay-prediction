import { SecretsManagerClient, GetSecretValueCommand } from '@aws-sdk/client-secrets-manager';
import knex, { Knex } from 'knex';

interface DatabaseCredentials {
  username: string;
  password: string;
  dbname: string;
  engine: string;
  port: number;
}

interface DatabaseConfig {
  host: string;
  secretArn: string;
  region?: string;
}

export class DatabaseUtil {
  private static instance: DatabaseUtil;
  private knexInstance: Knex | null = null;
  private credentials: DatabaseCredentials | null = null;
  private config: DatabaseConfig;

  private constructor(config: DatabaseConfig) {
    this.config = config;
  }

  // Singleton pattern for reuse across Lambda invocations
  public static getInstance(config?: DatabaseConfig): DatabaseUtil {
    console.log('🔍 Checking for existing DatabaseUtil instance...');
    if (!DatabaseUtil.instance) {
      if (!config) {
        throw new Error('DatabaseUtil config required for first initialization');
      }
      DatabaseUtil.instance = new DatabaseUtil(config);
    }
    return DatabaseUtil.instance;
  }

  // Factory method for easy initialization from environment variables
  public static fromEnvironment(): DatabaseUtil {
    const config: DatabaseConfig = {
      host: process.env.DB_HOST!,
      secretArn: process.env.DATABASE_SECRET_ARN!,
      region: process.env.AWS_REGION || 'us-east-1',
    };

    if (!config.host || !config.secretArn) {
      throw new Error('Missing required environment variables: DB_HOST, DATABASE_SECRET_ARN');
    }

    return DatabaseUtil.getInstance(config);
  }

  // Get Knex instance - main method for database operations
  public async getKnex(): Promise<Knex> {
    if (!this.knexInstance) {
      await this.initialize();
    }
    return this.knexInstance!;
  }

  // Initialize database connection
  private async initialize(): Promise<void> {
    console.log('🔗 Initializing database connection...');
    
    try {
      // Get credentials from Secrets Manager
      if (!this.credentials) {
        this.credentials = await this.getCredentialsFromSecretsManager();
      }

      // Create Knex instance
      this.knexInstance = knex(this.buildKnexConfig());
      
      // Test connection
      await this.testConnection();
      
      console.log('✅ Database connection initialized successfully');
    } catch (error) {
      console.error('❌ Failed to initialize database connection:', error);
      throw error;
    }
  }

  // Get credentials from AWS Secrets Manager
  private async getCredentialsFromSecretsManager(): Promise<DatabaseCredentials> {
    console.log('🔍 Retrieving database credentials from Secrets Manager...');
    const secretsManager = new SecretsManagerClient({
      region: this.config.region,
    });

    try {
      const command = new GetSecretValueCommand({
        SecretId: this.config.secretArn,
      });

      const response = await secretsManager.send(command);
      
      if (!response.SecretString) {
        throw new Error('Secret value is empty');
      }

      const credentials = JSON.parse(response.SecretString) as DatabaseCredentials;
      
      // Validate credentials format
      this.validateCredentials(credentials);
      
      console.log(`✅ Retrieved credentials for user: ${credentials.username}`);
      return credentials;
      
    } catch (error) {
      console.error('❌ Failed to retrieve database credentials:', error);
      throw new Error(`Secrets Manager error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  // Validate credentials have required fields
  private validateCredentials(credentials: any): asserts credentials is DatabaseCredentials {
    const required = ['username', 'password', 'dbname', 'engine', 'port'];
    const missing = required.filter(field => !credentials[field]);
    
    if (missing.length > 0) {
      throw new Error(`Missing required credential fields: ${missing.join(', ')}`);
    }
  }

  // Build Knex configuration
  private buildKnexConfig(): Knex.Config {
    if (!this.credentials) {
      throw new Error('Credentials not loaded');
    }

    return {
      client: 'postgresql',
      connection: {
        host: this.config.host,
        port: 5432, // Default PostgreSQL port
        database: this.credentials.dbname,
        user: this.credentials.username,
        password: this.credentials.password,
        ssl:{
          rejectUnauthorized: false, // Allow self-signed certificates (adjust as needed)
        }, // Usually false for VPC internal connections
        connectionTimeoutMillis: 30000,
      },
      pool: {
        min: 0,
        max: 1, // Single connection for Lambda
        acquireTimeoutMillis: 60000,
        createTimeoutMillis: 30000,
        destroyTimeoutMillis: 5000,
        idleTimeoutMillis: 30000,
      },
      acquireConnectionTimeout: 60000,
    };
  }

  // Test database connection
  public async testConnection(): Promise<boolean> {
    try {
      if (!this.knexInstance) {
        await this.initialize();
      }
      
      await this.knexInstance!.raw('SELECT 1 as test');
      console.log('✅ Database connection test successful');
      return true;
      
    } catch (error) {
      console.error('❌ Database connection test failed:', error);
      return false;
    }
  }

  // Execute raw SQL query
  public async executeRaw(sql: string, bindings?: any[]): Promise<any> {
    const knexInstance = await this.getKnex();
    if (bindings && bindings.length > 0) {
      return await knexInstance.raw(sql, bindings);
    }
    return await knexInstance.raw(sql);
  }

  // Begin transaction
  public async beginTransaction(): Promise<Knex.Transaction> {
    const knexInstance = await this.getKnex();
    return await knexInstance.transaction();
  }

  // Close database connection (important for Lambda)
  public async closeConnection(): Promise<void> {
    if (this.knexInstance) {
      try {
        await this.knexInstance.destroy();
        this.knexInstance = null;
        this.credentials = null;
        console.log('✅ Database connection closed');
      } catch (error) {
        console.error('⚠️ Warning: Error closing database connection:', error);
      }
    }
  }

  // Health check method
  public async healthCheck(): Promise<{
    status: 'healthy' | 'unhealthy';
    timestamp: string;
    database: string;
    error?: string;
  }> {
    try {
      const isHealthy = await this.testConnection();
      return {
        status: isHealthy ? 'healthy' : 'unhealthy',
        timestamp: new Date().toISOString(),
        database: this.credentials?.dbname || 'unknown',
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        timestamp: new Date().toISOString(),
        database: this.credentials?.dbname || 'unknown',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // Helper method to get table names (useful for debugging)
  public async getTableNames(): Promise<string[]> {
    const knexInstance = await this.getKnex();
    const result = await knexInstance.raw(`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' 
      ORDER BY table_name
    `);
    return result.rows.map((row: any) => row.table_name);
  }

  // Helper method to check if table exists
  public async tableExists(tableName: string): Promise<boolean> {
    const knexInstance = await this.getKnex();
    return await knexInstance.schema.hasTable(tableName);
  }

  // Helper method to get table schema information
  public async getTableSchema(tableName: string): Promise<any[]> {
    const knexInstance = await this.getKnex();
    const result = await knexInstance.raw(`
      SELECT 
        column_name,
        data_type,
        is_nullable,
        column_default,
        character_maximum_length,
        numeric_precision,
        numeric_scale
      FROM information_schema.columns 
      WHERE table_name = ? 
      AND table_schema = 'public'
      ORDER BY ordinal_position
    `, [tableName]);
    
    return result.rows;
  }

  // Helper method to get foreign key relationships
  public async getForeignKeys(tableName: string): Promise<any[]> {
    const knexInstance = await this.getKnex();
    const result = await knexInstance.raw(`
      SELECT
        tc.constraint_name,
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
      FROM information_schema.table_constraints AS tc
      JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
      JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
      WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = ?
        AND tc.table_schema = 'public'
    `, [tableName]);
    
    return result.rows;
  }
}


// // =============================================================================
// // EXAMPLE CRUD LAMBDA FUNCTIONS USING THE UTILITY
// // =============================================================================

// // lambda/functions/suppliers/getSupplier.ts
// import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
// import { DatabaseUtil } from '../../utils/DatabaseUtil';

// export const handler = async (
//   event: APIGatewayProxyEvent
// ): Promise<APIGatewayProxyResult> => {
//   let dbUtil: DatabaseUtil | null = null;

//   try {
//     const supplierId = event.pathParameters?.id;
//     if (!supplierId) {
//       return createResponse(400, { error: 'Supplier ID is required' });
//     }

//     // Initialize database utility
//     dbUtil = DatabaseUtil.fromEnvironment();
//     const knex = await dbUtil.getKnex();

//     // Query supplier with joins
//     const supplier = await knex('suppliers')
//       .select([
//         'suppliers.*',
//         'manufacturers.name as manufacturer_name',
//         'locations.city',
//         'locations.name as location_name',
//         'countries.name as country_name'
//       ])
//       .leftJoin('manufacturers', 'suppliers.manufacturer_id', 'manufacturers.id')
//       .leftJoin('locations', 'suppliers.location_id', 'locations.id')
//       .leftJoin('countries', 'locations.country_id', 'countries.id')
//       .where('suppliers.id', parseInt(supplierId))
//       .first();

//     if (!supplier) {
//       return createResponse(404, { error: 'Supplier not found' });
//     }

//     return createResponse(200, {
//       success: true,
//       data: supplier,
//     });

//   } catch (error) {
//     console.error('Error fetching supplier:', error);
//     return createResponse(500, {
//       error: 'Internal server error',
//       message: error instanceof Error ? error.message : 'Unknown error',
//     });
//   } finally {
//     if (dbUtil) {
//       await dbUtil.closeConnection();
//     }
//   }
// };

// // lambda/functions/suppliers/createSupplier.ts
// import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
// import { DatabaseUtil } from '../../utils/DatabaseUtil';
// import Joi from 'joi';

// const supplierSchema = Joi.object({
//   name: Joi.string().required().max(255),
//   manufacturer_id: Joi.number().integer().positive().required(),
//   location_id: Joi.number().integer().positive().required(),
//   alpha: Joi.number().min(0).max(1).default(0),
// });

// export const handler = async (
//   event: APIGatewayProxyEvent
// ): Promise<APIGatewayProxyResult> => {
//   let dbUtil: DatabaseUtil | null = null;

//   try {
//     // Parse and validate request body
//     const body = JSON.parse(event.body || '{}');
//     const { error, value } = supplierSchema.validate(body);

//     if (error) {
//       return createResponse(400, {
//         error: 'Validation failed',
//         details: error.details.map(d => d.message),
//       });
//     }

//     // Initialize database utility
//     dbUtil = DatabaseUtil.fromEnvironment();
//     const knex = await dbUtil.getKnex();

//     // Create supplier
//     const [newSupplier] = await knex('suppliers')
//       .insert(value)
//       .returning('*');

//     return createResponse(201, {
//       success: true,
//       data: newSupplier,
//       message: 'Supplier created successfully',
//     });

//   } catch (error) {
//     console.error('Error creating supplier:', error);
    
//     // Handle database constraint errors
//     if (error instanceof Error && error.message.includes('foreign key')) {
//       return createResponse(400, {
//         error: 'Invalid manufacturer_id or location_id',
//       });
//     }

//     return createResponse(500, {
//       error: 'Failed to create supplier',
//       message: error instanceof Error ? error.message : 'Unknown error',
//     });
//   } finally {
//     if (dbUtil) {
//       await dbUtil.closeConnection();
//     }
//   }
// };

// // lambda/functions/suppliers/updateSupplier.ts
// import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
// import { DatabaseUtil } from '../../utils/DatabaseUtil';

// export const handler = async (
//   event: APIGatewayProxyEvent
// ): Promise<APIGatewayProxyResult> => {
//   let dbUtil: DatabaseUtil | null = null;

//   try {
//     const supplierId = event.pathParameters?.id;
//     if (!supplierId) {
//       return createResponse(400, { error: 'Supplier ID is required' });
//     }

//     const body = JSON.parse(event.body || '{}');
    
//     // Initialize database utility
//     dbUtil = DatabaseUtil.fromEnvironment();
//     const knex = await dbUtil.getKnex();

//     // Check if supplier exists
//     const existingSupplier = await knex('suppliers')
//       .where('id', parseInt(supplierId))
//       .first();

//     if (!existingSupplier) {
//       return createResponse(404, { error: 'Supplier not found' });
//     }

//     // Update supplier
//     const [updatedSupplier] = await knex('suppliers')
//       .where('id', parseInt(supplierId))
//       .update({
//         ...body,
//         updated_at: new Date(),
//       })
//       .returning('*');

//     return createResponse(200, {
//       success: true,
//       data: updatedSupplier,
//       message: 'Supplier updated successfully',
//     });

//   } catch (error) {
//     console.error('Error updating supplier:', error);
//     return createResponse(500, {
//       error: 'Failed to update supplier',
//       message: error instanceof Error ? error.message : 'Unknown error',
//     });
//   } finally {
//     if (dbUtil) {
//       await dbUtil.closeConnection();
//     }
//   }
// };

// // lambda/functions/suppliers/deleteSupplier.ts
// import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
// import { DatabaseUtil } from '../../utils/DatabaseUtil';

// export const handler = async (
//   event: APIGatewayProxyEvent
// ): Promise<APIGatewayProxyResult> => {
//   let dbUtil: DatabaseUtil | null = null;

//   try {
//     const supplierId = event.pathParameters?.id;
//     if (!supplierId) {
//       return createResponse(400, { error: 'Supplier ID is required' });
//     }

//     // Initialize database utility
//     dbUtil = DatabaseUtil.fromEnvironment();
//     const knex = await dbUtil.getKnex();

//     // Check if supplier exists
//     const existingSupplier = await knex('suppliers')
//       .where('id', parseInt(supplierId))
//       .first();

//     if (!existingSupplier) {
//       return createResponse(404, { error: 'Supplier not found' });
//     }

//     // Use transaction for safe deletion
//     await knex.transaction(async (trx) => {
//       // Check for dependent records
//       const orderCount = await trx('orders')
//         .where('supplier_id', parseInt(supplierId))
//         .count('id as count')
//         .first();

//       if (parseInt(orderCount?.count as string) > 0) {
//         throw new Error('Cannot delete supplier with existing orders');
//       }

//       // Delete supplier
//       await trx('suppliers')
//         .where('id', parseInt(supplierId))
//         .del();
//     });

//     return createResponse(200, {
//       success: true,
//       message: 'Supplier deleted successfully',
//     });

//   } catch (error) {
//     console.error('Error deleting supplier:', error);
    
//     if (error instanceof Error && error.message.includes('existing orders')) {
//       return createResponse(400, { error: error.message });
//     }

//     return createResponse(500, {
//       error: 'Failed to delete supplier',
//       message: error instanceof Error ? error.message : 'Unknown error',
//     });
//   } finally {
//     if (dbUtil) {
//       await dbUtil.closeConnection();
//     }
//   }
// };

// // lambda/functions/health/healthCheck.ts
// import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
// import { DatabaseUtil } from '../../utils/DatabaseUtil';

// export const handler = async (
//   event: APIGatewayProxyEvent
// ): Promise<APIGatewayProxyResult> => {
//   let dbUtil: DatabaseUtil | null = null;

//   try {
//     // Initialize database utility
//     dbUtil = DatabaseUtil.fromEnvironment();
    
//     // Perform health check
//     const healthStatus = await dbUtil.healthCheck();
    
//     // Get table count
//     const tableNames = await dbUtil.getTableNames();
    
//     const response = {
//       service: 'M4ESTRO API',
//       database: healthStatus,
//       tables: {
//         count: tableNames.length,
//         expected: 25,
//         status: tableNames.length >= 25 ? 'healthy' : 'incomplete',
//       },
//       timestamp: new Date().toISOString(),
//     };

//     const statusCode = healthStatus.status === 'healthy' ? 200 : 503;
//     return createResponse(statusCode, response);

//   } catch (error) {
//     console.error('Health check failed:', error);
//     return createResponse(503, {
//       service: 'M4ESTRO API',
//       status: 'unhealthy',
//       error: error instanceof Error ? error.message : 'Unknown error',
//       timestamp: new Date().toISOString(),
//     });
//   } finally {
//     if (dbUtil) {
//       await dbUtil.closeConnection();
//     }
//   }
// };

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

// Helper function to create consistent API responses
// function createResponse(statusCode: number, body: any): APIGatewayProxyResult {
//   return {
//     statusCode,
//     headers: {
//       'Content-Type': 'application/json',
//       'Access-Control-Allow-Origin': '*',
//       'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
//       'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
//     },
//     body: JSON.stringify(body),
//   };
// }
