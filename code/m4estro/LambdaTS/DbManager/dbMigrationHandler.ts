import { 
  APIGatewayEvent,
  APIGatewayProxyResult,
  Context 
} from 'aws-lambda';
import { z } from 'zod';
import { DatabaseUtil } from '../utils/DatabaseUtils';
import { DatabaseService } from './databseService';
import { 
  ResponseHelper, 
  handleCorsPreflightRequest, 
  parseRequestBody,
  PaginationSchema,
  BulkRequestSchema,
  generateRequestId,
  sanitizeInput,
  checkRateLimit
} from '../utils/responseHelper';
import { up as runMigrations } from './migrations';

/**
 * Complete Database Management Lambda Handler
 * 
 * Endpoints:
 * GET /db/health - Health check
 * GET /db/migration - Run migrations
 * GET /db/tables - List all tables
 * GET /db/tables/{tableName} - Get table info
 * GET /db/tables/{tableName}/data - Get table data with pagination
 * GET /db/tables/{tableName}/data/{id} - Get record by ID
 * POST /db/tables/{tableName} - Insert data
 * PUT /db/tables/{tableName}/{id} - Update record by ID
 * DELETE /db/tables/{tableName}/{id} - Delete record by ID
 * DELETE /db/tables/{tableName}/all-records - Delete ALL records from table
 * POST /db/bulk - Bulk operations
 * DELETE /db/bulk-delete/{tableName} - Bulk delete records
 * POST /db/query - Execute raw SQL (SELECT only)
 */

// Request validation schemas
const TableDataRequestSchema = z.object({
  tableName: z.string().min(1),
  select: z.array(z.string()).optional(),
  where: z.record(z.any()).optional(),
  orderBy: z.object({
    column: z.string(),
    direction: z.enum(['asc', 'desc']).default('asc'),
  }).optional(),
  limit: z.number().int().positive().max(1000).optional(),
  offset: z.number().int().min(0).optional(),
  joins: z.array(z.object({
    table: z.string(),
    type: z.enum(['inner', 'left', 'right', 'full']).default('inner'),
    on: z.object({
      column1: z.string(),
      column2: z.string(),
    }),
  })).optional(),
});

const InsertDataRequestSchema = z.object({
  data: z.union([z.record(z.any()), z.array(z.record(z.any()))]),
  validateOnly: z.boolean().default(false),
});

const UpdateDataRequestSchema = z.object({
  data: z.record(z.any()),
  validateOnly: z.boolean().default(false),
});

const DeleteDataRequestSchema = z.object({
  confirmDelete: z.boolean().default(false),
});

// Bulk delete schemas
const BulkDeleteRequestSchema = z.object({
  method: z.enum(['ids', 'conditions']),
  ids: z.array(z.number().int().positive()).optional(),
  conditions: z.record(z.any()).optional(),
  confirmDelete: z.boolean().default(false),
}).refine(
  (data) => 
    (data.method === 'ids' && data.ids && data.ids.length > 0) ||
    (data.method === 'conditions' && data.conditions),
  {
    message: "For 'ids' method, 'ids' array is required. For 'conditions' method, 'conditions' object is required.",
  }
);

// Delete all records schema
const DeleteAllRecordsRequestSchema = z.object({
  method: z.enum(['truncate', 'delete']).default('delete'),
  confirmDeleteAll: z.boolean().default(false),
  tableNameConfirmation: z.string().min(1),
}).refine(
  (data) => data.confirmDeleteAll === true,
  {
    message: "confirmDeleteAll must be true to proceed with deleting all records",
  }
);

const RawQueryRequestSchema = z.object({
  sql: z.string().min(1),
  bindings: z.array(z.any()).optional(),
});

export const databaseHandler = async (
  event: APIGatewayEvent,
  context: Context
): Promise<APIGatewayProxyResult> => {
  // Set Lambda context deadline awareness
  context.callbackWaitsForEmptyEventLoop = false;
  
  const requestId = generateRequestId();
  console.log(`🚀 DB Manager Lambda started - Request ID: ${requestId}`);
  console.log(`📍 Path: ${event.path}, Method: ${event.httpMethod}`);

  // Handle CORS preflight requests
  if (event.httpMethod === 'OPTIONS') {
    return handleCorsPreflightRequest();
  }

  // Basic rate limiting (use API Gateway throttling in production)
  const sourceIp = event.requestContext?.identity?.sourceIp || 'unknown';
  const rateLimitCheck = checkRateLimit(sourceIp, 1000, 60000); // 1000 requests per minute
  
  if (!rateLimitCheck.allowed) {
    return ResponseHelper.error('Rate limit exceeded', 429, {
      remaining: rateLimitCheck.remaining,
      resetTime: new Date(rateLimitCheck.resetTime).toISOString(),
    });
  }

  try {
    // Route to specific handlers based on path
    const pathSegments = event.path.split('/').filter(Boolean);
    
    if (pathSegments.length === 0 || pathSegments[0] !== 'db') {
      return ResponseHelper.badRequest('Invalid API path. Must start with /db');
    }

    // Handle specific routes
    switch (pathSegments[1]) {
      case 'health':
        return await handleHealthCheck(requestId);
      
      case 'migration':
        return await handleMigration(requestId);
      
      case 'tables':
        return await handleTablesRoute(event, pathSegments.slice(2), requestId);
      
      case 'bulk':
        return await handleBulkOperations(event, requestId);
      
      case 'bulk-delete':
        return await handleBulkDelete(event, requestId);
      
      case 'query':
        return await handleRawQuery(event, requestId);
      
      default:
        return ResponseHelper.notFound(`Route /${pathSegments.join('/')} not found`);
    }

  } catch (error) {
    console.error(`❌ DB Manager operation failed - Request ID: ${requestId}:`, error);
    
    // Handle specific error types
    if (error instanceof z.ZodError) {
      return ResponseHelper.validationError(error);
    }
    
    if (error instanceof SyntaxError) {
      return ResponseHelper.badRequest('Invalid JSON in request body');
    }
    
    if (error instanceof Error) {
      // Check if it's a database-related error
      if (error.message.includes('connection') || 
          error.message.includes('timeout') ||
          error.message.includes('database')) {
        return ResponseHelper.handleDatabaseError(error);
      }
      
      return ResponseHelper.error(error.message, 400, undefined, requestId);
    }
    
    return ResponseHelper.error('Unknown server error', 500, undefined, requestId);
  }
};

/**
 * Handle health check endpoint
 * GET /db/health
 */
async function handleHealthCheck(requestId: string): Promise<APIGatewayProxyResult> {
  let dbUtil: DatabaseUtil | null = null;
  
  try {
    console.log(`🔍 Health check started - Request ID: ${requestId}`);
    
    dbUtil = DatabaseUtil.fromEnvironment();
    const dbService = new DatabaseService(dbUtil);
    
    const health = await dbService.getHealthCheck();
    const statistics = await dbService.getTableStatistics();
    
    const response = {
      service: 'M4ESTRO Database API',
      version: '1.0.0',
      requestId,
      health,
      statistics: statistics.success ? statistics.data : undefined,
      timestamp: new Date().toISOString(),
    };
    
    const statusCode = health.status === 'healthy' ? 200 : 503;
    return ResponseHelper.success(response, 'Health check completed', statusCode);
    
  } catch (error) {
    console.error(`❌ Health check failed - Request ID: ${requestId}:`, error);
    return ResponseHelper.serviceUnavailable('Health check failed');
  } finally {
    if (dbUtil) {
      await dbUtil.closeConnection();
    }
  }
}

/**
 * Handle migration endpoint
 * GET /db/migration
 */
async function handleMigration(requestId: string): Promise<APIGatewayProxyResult> {
  let dbUtil: DatabaseUtil | null = null;
  
  try {
    console.log(`🔄 Migration started - Request ID: ${requestId}`);
    
    dbUtil = DatabaseUtil.fromEnvironment();
    const knex = await dbUtil.getKnex();
    
    const result = await runMigrations(knex);
    console.log(`✅ Migration completed - Request ID: ${requestId}`);
    
    return ResponseHelper.success(result, 'Migration completed successfully');
    
  } catch (error) {
    console.error(`❌ Migration failed - Request ID: ${requestId}:`, error);
    return ResponseHelper.handleDatabaseError(error);
  } finally {
    if (dbUtil) {
      await dbUtil.closeConnection();
    }
  }
}

/**
 * Handle tables-related routes
 * GET /db/tables - List all tables
 * GET /db/tables/{tableName} - Get table info
 * GET /db/tables/{tableName}/data - Get table data
 * GET /db/tables/{tableName}/data/{id} - Get record by ID
 * POST /db/tables/{tableName} - Insert data
 * PUT /db/tables/{tableName}/{id} - Update record by ID
 * DELETE /db/tables/{tableName}/{id} - Delete record by ID
 * DELETE /db/tables/{tableName}/all-records - Delete ALL records from table
 */
async function handleTablesRoute(
  event: APIGatewayEvent,
  pathSegments: string[],
  requestId: string
): Promise<APIGatewayProxyResult> {
  let dbUtil: DatabaseUtil | null = null;
  
  try {
    dbUtil = DatabaseUtil.fromEnvironment();
    const dbService = new DatabaseService(dbUtil);
    
    // GET /db/tables - List all tables
    if (pathSegments.length === 0 && event.httpMethod === 'GET') {
      const result = await dbService.getAllTables();
      return ResponseHelper.success(result.data, result.message);
    }
    
    // Routes requiring table name
    if (pathSegments.length === 0) {
      return ResponseHelper.badRequest('Table name is required');
    }
    
    const tableName = pathSegments[0];
    
    // GET /db/tables/{tableName} - Get table info
    if (pathSegments.length === 1 && event.httpMethod === 'GET') {
      const result = await dbService.getTableInfo(tableName);
      if (result.success) {
        return ResponseHelper.success(result.data, result.message);
      } else {
        return ResponseHelper.error(result.message, 400);
      }
    }
    
    // POST /db/tables/{tableName} - Insert data
    if (pathSegments.length === 1 && event.httpMethod === 'POST') {
      const body = parseRequestBody(event.body);
      const validated = InsertDataRequestSchema.parse(sanitizeInput(body));
      
      const result = await dbService.insertData({
        tableName,
        data: validated.data,
        validateOnly: validated.validateOnly,
      });
      
      if (result.success) {
        const statusCode = validated.validateOnly ? 200 : 201;
        return ResponseHelper.success(result.data, result.message, statusCode, {
          recordsAffected: result.recordsAffected,
          executionTime: result.executionTime,
        });
      } else {
        return ResponseHelper.badRequest(result.message, {
          validationErrors: result.validationErrors,
        });
      }
    }
    
    // Handle data sub-routes
    if (pathSegments[1] === 'data') {
      return await handleTableDataRoute(event, tableName, pathSegments.slice(2), dbService);
    }
    
    // Handle delete all records route
    if (pathSegments[1] === 'all-records' && event.httpMethod === 'DELETE') {
      return await handleDeleteAllRecords(event, tableName, dbService, requestId);
    }
    
    // Handle direct record operations
    if (pathSegments.length === 2) {
      const recordId = parseInt(pathSegments[1]);
      if (isNaN(recordId)) {
        return ResponseHelper.badRequest('Invalid record ID. Must be a number');
      }
      
      return await handleRecordOperations(event, tableName, recordId, dbService);
    }
    
    return ResponseHelper.notFound('Route not found');
    
  } catch (error) {
    if (error instanceof z.ZodError) {
      return ResponseHelper.validationError(error);
    }
    throw error;
  } finally {
    if (dbUtil) {
      await dbUtil.closeConnection();
    }
  }
}

/**
 * Handle table data routes
 * GET /db/tables/{tableName}/data - Get table data with pagination
 * GET /db/tables/{tableName}/data/{id} - Get record by ID
 */
async function handleTableDataRoute(
  event: APIGatewayEvent,
  tableName: string,
  pathSegments: string[],
  dbService: DatabaseService
): Promise<APIGatewayProxyResult> {
  
  // GET /db/tables/{tableName}/data/{id} - Get record by ID
  if (pathSegments.length === 1 && event.httpMethod === 'GET') {
    const recordId = parseInt(pathSegments[0]);
    if (isNaN(recordId)) {
      return ResponseHelper.badRequest('Invalid record ID. Must be a number');
    }
    
    const result = await dbService.selectById(tableName, recordId);
    if (result.success) {
      return ResponseHelper.success(result.data, result.message);
    } else {
      return ResponseHelper.notFound(result.message);
    }
  }
  
  // GET /db/tables/{tableName}/data - Get table data with pagination
  if (pathSegments.length === 0 && event.httpMethod === 'GET') {
    const queryParams = event.queryStringParameters || {};
    
    // Check if pagination is requested
    if (queryParams.page || queryParams.pageSize) {
      const pagination = PaginationSchema.parse({
        page: queryParams.page ? parseInt(queryParams.page) : undefined,
        pageSize: queryParams.pageSize ? parseInt(queryParams.pageSize) : undefined,
        orderBy: queryParams.orderBy,
        direction: queryParams.direction as 'asc' | 'desc',
      });
      
      const whereClause = queryParams.where ? JSON.parse(queryParams.where) : undefined;
      
      const result = await dbService.selectWithPagination(
        tableName,
        pagination.page,
        pagination.pageSize,
        pagination.orderBy,
        pagination.direction,
        whereClause
      );
      
      if (result.success) {
        return ResponseHelper.paginated(result.data, result.pagination, result.message);
      } else {
        return ResponseHelper.error(result.message, 400);
      }
    } else {
      // Regular select with optional filters
      const requestData = {
        tableName,
        select: queryParams.select ? queryParams.select.split(',') : undefined,
        where: queryParams.where ? JSON.parse(queryParams.where) : undefined,
        orderBy: queryParams.orderBy ? {
          column: queryParams.orderBy,
          direction: (queryParams.direction as 'asc' | 'desc') || 'asc',
        } : undefined,
        limit: queryParams.limit ? parseInt(queryParams.limit) : undefined,
        offset: queryParams.offset ? parseInt(queryParams.offset) : undefined,
      };
      
      const validated = TableDataRequestSchema.parse(requestData);
      const result = await dbService.selectData(validated);
      
      if (result.success) {
        return ResponseHelper.success(result.data, result.message, 200, {
          recordsAffected: result.recordsAffected,
          executionTime: result.executionTime,
        });
      } else {
        return ResponseHelper.error(result.message, 400);
      }
    }
  }
  
  return ResponseHelper.methodNotAllowed(event.httpMethod || 'UNKNOWN');
}

/**
 * Handle individual record operations
 * PUT /db/tables/{tableName}/{id} - Update record by ID
 * DELETE /db/tables/{tableName}/{id} - Delete record by ID
 */
async function handleRecordOperations(
  event: APIGatewayEvent,
  tableName: string,
  recordId: number,
  dbService: DatabaseService
): Promise<APIGatewayProxyResult> {
  
  // PUT /db/tables/{tableName}/{id} - Update record by ID
  if (event.httpMethod === 'PUT') {
    const body = parseRequestBody(event.body);
    const validated = UpdateDataRequestSchema.parse(sanitizeInput(body));
    
    const result = await dbService.updateById(tableName, recordId, validated.data);
    
    if (result.success) {
      return ResponseHelper.success(result.data, result.message, 200, {
        recordsAffected: result.recordsAffected,
        executionTime: result.executionTime,
      });
    } else {
      return ResponseHelper.notFound(result.message);
    }
  }
  
  // DELETE /db/tables/{tableName}/{id} - Delete record by ID
  if (event.httpMethod === 'DELETE') {
    const body = event.body ? parseRequestBody(event.body) : {};
    const validated = DeleteDataRequestSchema.parse(body);
    
    const result = await dbService.deleteById(tableName, recordId, validated.confirmDelete);
    
    if (result.success) {
      return ResponseHelper.success(result.data, result.message, 200, {
        recordsAffected: result.recordsAffected,
        executionTime: result.executionTime,
      });
    } else {
      if (result.message.includes('confirmation')) {
        return ResponseHelper.badRequest(result.message);
      } else {
        return ResponseHelper.notFound(result.message);
      }
    }
  }
  
  return ResponseHelper.methodNotAllowed(event.httpMethod || 'UNKNOWN');
}

/**
 * Handle delete all records from table
 * DELETE /db/tables/{tableName}/all-records
 */
async function handleDeleteAllRecords(
  event: APIGatewayEvent,
  tableName: string,
  dbService: DatabaseService,
  requestId: string
): Promise<APIGatewayProxyResult> {
  
  try {
    console.log(`🗑️ Delete all records started for table ${tableName} - Request ID: ${requestId}`);
    
    const body = parseRequestBody(event.body);
    const validated = DeleteAllRecordsRequestSchema.parse(sanitizeInput(body));
    
    // Additional safety check - table name must match
    if (validated.tableNameConfirmation !== tableName) {
      return ResponseHelper.badRequest(
        `Table name confirmation does not match. Expected '${tableName}', got '${validated.tableNameConfirmation}'`
      );
    }
    
    const result = await dbService.deleteAllRecords(tableName, validated.method, validated.confirmDeleteAll);
    
    if (result.success) {
      console.log(`✅ Delete all records completed for table ${tableName} - Request ID: ${requestId}`);
      return ResponseHelper.success(result.data, result.message, 200, {
        recordsAffected: result.recordsAffected,
        executionTime: result.executionTime,
      });
    } else {
      if (result.message.includes('confirmation')) {
        return ResponseHelper.badRequest(result.message);
      } else {
        return ResponseHelper.error(result.message, 400);
      }
    }
    
  } catch (error) {
    if (error instanceof z.ZodError) {
      return ResponseHelper.validationError(error);
    }
    throw error;
  }
}

/**
 * Handle bulk delete operations
 * DELETE /db/bulk-delete/{tableName}
 */
async function handleBulkDelete(
  event: APIGatewayEvent,
  requestId: string
): Promise<APIGatewayProxyResult> {
  if (event.httpMethod !== 'DELETE') {
    return ResponseHelper.methodNotAllowed(event.httpMethod || 'UNKNOWN');
  }
  
  let dbUtil: DatabaseUtil | null = null;
  
  try {
    const pathSegments = event.path.split('/').filter(Boolean);
    
    if (pathSegments.length !== 3) {
      return ResponseHelper.badRequest('Invalid path. Expected: /db/bulk-delete/{tableName}');
    }
    
    const tableName = pathSegments[2];
    
    dbUtil = DatabaseUtil.fromEnvironment();
    const dbService = new DatabaseService(dbUtil);
    
    console.log(`🗑️ Bulk delete started for table ${tableName} - Request ID: ${requestId}`);
    
    const body = parseRequestBody(event.body);
    const validated = BulkDeleteRequestSchema.parse(sanitizeInput(body));
    
    let result;
    
    if (validated.method === 'ids') {
      result = await dbService.bulkDeleteByIds(tableName, validated.ids!, validated.confirmDelete);
    } else {
      result = await dbService.bulkDeleteByConditions(tableName, validated.conditions!, validated.confirmDelete);
    }
    
    if (result.success) {
      console.log(`✅ Bulk delete completed for table ${tableName} - Request ID: ${requestId}`);
      return ResponseHelper.success(result.data, result.message, 200, {
        recordsAffected: result.recordsAffected,
        executionTime: result.executionTime,
      });
    } else {
      if (result.message.includes('confirmation')) {
        return ResponseHelper.badRequest(result.message);
      } else {
        return ResponseHelper.error(result.message, 400);
      }
    }
    
  } catch (error) {
    if (error instanceof z.ZodError) {
      return ResponseHelper.validationError(error);
    }
    throw error;
  } finally {
    if (dbUtil) {
      await dbUtil.closeConnection();
    }
  }
}

/**
 * Handle bulk operations
 * POST /db/bulk
 */
async function handleBulkOperations(
  event: APIGatewayEvent,
  requestId: string
): Promise<APIGatewayProxyResult> {
  if (event.httpMethod !== 'POST') {
    return ResponseHelper.methodNotAllowed(event.httpMethod || 'UNKNOWN');
  }
  
  let dbUtil: DatabaseUtil | null = null;
  
  try {
    dbUtil = DatabaseUtil.fromEnvironment();
    const dbService = new DatabaseService(dbUtil);
    
    console.log(`🔄 Bulk operations started - Request ID: ${requestId}`);
    
    const body = parseRequestBody(event.body);
    const validated = BulkRequestSchema.parse(sanitizeInput(body));
    
    const result = await dbService.executeBulkOperations(validated);
    
    if (result.success) {
      console.log(`✅ Bulk operations completed - Request ID: ${requestId}`);
      return ResponseHelper.bulk(result.data, result.message);
    } else {
      return ResponseHelper.badRequest(result.message, {
        validationErrors: result.validationErrors,
      });
    }
    
  } catch (error) {
    if (error instanceof z.ZodError) {
      return ResponseHelper.validationError(error);
    }
    throw error;
  } finally {
    if (dbUtil) {
      await dbUtil.closeConnection();
    }
  }
}

/**
 * Handle raw SQL queries (SELECT only for security)
 * POST /db/query
 */
async function handleRawQuery(
  event: APIGatewayEvent,
  requestId: string
): Promise<APIGatewayProxyResult> {
  if (event.httpMethod !== 'POST') {
    return ResponseHelper.methodNotAllowed(event.httpMethod || 'UNKNOWN');
  }
  
  let dbUtil: DatabaseUtil | null = null;
  
  try {
    dbUtil = DatabaseUtil.fromEnvironment();
    const dbService = new DatabaseService(dbUtil);
    
    console.log(`🔍 Raw query started - Request ID: ${requestId}`);
    
    const body = parseRequestBody(event.body);
    const validated = RawQueryRequestSchema.parse(body);
    
    const result = await dbService.executeRawQuery(validated.sql, validated.bindings);
    
    if (result.success) {
      console.log(`✅ Raw query completed - Request ID: ${requestId}`);
      return ResponseHelper.success(result.data, result.message, 200, {
        recordsAffected: result.recordsAffected,
        executionTime: result.executionTime,
      });
    } else {
      return ResponseHelper.badRequest(result.message);
    }
    
  } catch (error) {
    if (error instanceof z.ZodError) {
      return ResponseHelper.validationError(error);
    }
    throw error;
  } finally {
    if (dbUtil) {
      await dbUtil.closeConnection();
    }
  }
}

// Export the main handler as default
export default databaseHandler;