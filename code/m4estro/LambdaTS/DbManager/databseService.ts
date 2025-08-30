// src/services/databaseService.ts
import { Knex } from 'knex';
import { z } from 'zod';
import { DatabaseUtil } from '../utils/DatabaseUtils';
import { DatabaseHealth, QueryOptions, ValidationError } from './databaseTypes';
import {tables as coreTables} from './coreBusinessTables';
import {tables as timeTables} from './timeBasedTables';
import {tables as trackingAndWeatherTables} from './trackingAndWeatherTables';

// Validation schemas for CRUD operations
const InsertRequestSchema = z.object({
  tableName: z.string().min(1),
  data: z.union([z.object({}).passthrough(), z.array(z.object({}).passthrough())]),
  validateOnly: z.boolean().optional().default(false),
});

const UpdateRequestSchema = z.object({
  tableName: z.string().min(1),
  data: z.object({}).passthrough(),
  whereClause: z.object({}).passthrough(),
  validateOnly: z.boolean().optional().default(false),
});

const DeleteRequestSchema = z.object({
  tableName: z.string().min(1),
  whereClause: z.object({}).passthrough(),
  confirmDelete: z.boolean().default(false),
});

const SelectRequestSchema = z.object({
  tableName: z.string().min(1),
  select: z.array(z.string()).optional(),
  where: z.object({}).passthrough().optional(),
  orderBy: z.object({
    column: z.string(),
    direction: z.enum(['asc', 'desc']).default('asc'),
  }).optional(),
  limit: z.number().int().positive().optional(),
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

const BulkOperationSchema = z.object({
  operations: z.array(z.object({
    type: z.enum(['insert', 'update', 'delete']),
    tableName: z.string(),
    data: z.object({}).passthrough().optional(),
    whereClause: z.object({}).passthrough().optional(),
  })),
  useTransaction: z.boolean().default(true),
});

export interface DatabaseResult {
  success: boolean;
  message: string;
  data?: any;
  recordsAffected?: number;
  validationErrors?: ValidationError[];
  executionTime?: number;
}

export interface BulkOperationResult {
  operation: string;
  tableName: string;
  recordsAffected: number;
  data: any;
}

export interface TableInfo {
  tableName: string;
  columnCount: number;
  rowCount: number;
  primaryKey: string[];
  foreignKeys: Array<{
    column: string;
    referencedTable: string;
    referencedColumn: string;
  }>;
}

export class DatabaseService {
  private dbUtil: DatabaseUtil;
  private knex: Knex | null = null;

  // Valid table names for security
  private readonly VALID_TABLES = [
    ...coreTables,
    ...timeTables,
    ...trackingAndWeatherTables
  ];

  constructor(dbUtil: DatabaseUtil) {
    this.dbUtil = dbUtil;
  }

  private async getKnex(): Promise<Knex> {
    if (!this.knex) {
      this.knex = await this.dbUtil.getKnex();
    }
    return this.knex;
  }

  private validateTableName(tableName: string): void {
    if (!this.VALID_TABLES.includes(tableName)) {
      throw new Error(`Invalid table name: ${tableName}. Must be one of: ${this.VALID_TABLES.join(', ')}`);
    }
  }

  private addTimestamps(data: any, isUpdate = false): any {
    const now = new Date();
    if (Array.isArray(data)) {
      return data.map(item => ({
        ...item,
        ...(isUpdate ? { updated_at: now } : { created_at: now, updated_at: now })
      }));
    }
    return {
      ...data,
      ...(isUpdate ? { updated_at: now } : { created_at: now, updated_at: now })
    };
  }

  // Helper function to format Zod validation errors
  private formatZodErrors(error: z.ZodError): ValidationError[] {
    return error.errors.map(issue => ({
      field: issue.path.join('.'),
      message: issue.message,
      // Handle the input property safely - it may not exist on all ZodIssue types
      value: 'received' in issue ? issue.received : undefined,
    }));
  }

  // ============================================================================
  // CREATE Operations
  // ============================================================================

  async insertData(request: z.infer<typeof InsertRequestSchema>): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      const validated = InsertRequestSchema.parse(request);
      this.validateTableName(validated.tableName);
      
      const knex = await this.getKnex();
      const dataWithTimestamps = this.addTimestamps(validated.data);
      
      if (validated.validateOnly) {
        return {
          success: true,
          message: 'Validation successful',
          data: dataWithTimestamps,
          executionTime: Date.now() - startTime,
        };
      }

      const result = await knex(validated.tableName)
        .insert(dataWithTimestamps)
        .returning('*');

      return {
        success: true,
        message: `Successfully inserted ${Array.isArray(result) ? result.length : 1} record(s)`,
        data: result,
        recordsAffected: Array.isArray(result) ? result.length : 1,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      if (error instanceof z.ZodError) {
        return {
          success: false,
          message: 'Validation failed',
          validationErrors: this.formatZodErrors(error),
          executionTime: Date.now() - startTime,
        };
      }
      
      throw error;
    }
  }

  async bulkInsert(tableName: string, data: any[], batchSize = 100): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      this.validateTableName(tableName);
      const knex = await this.getKnex();
      
      const dataWithTimestamps = this.addTimestamps(data);
      const results: any[] = [];
      
      // Process in batches to avoid memory issues
      for (let i = 0; i < dataWithTimestamps.length; i += batchSize) {
        const batch = dataWithTimestamps.slice(i, i + batchSize);
        const batchResult = await knex(tableName).insert(batch).returning('id');
        results.push(...batchResult);
      }

      return {
        success: true,
        message: `Successfully bulk inserted ${results.length} record(s)`,
        data: results,
        recordsAffected: results.length,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      throw error;
    }
  }

  // ============================================================================
  // READ Operations
  // ============================================================================

  async selectData(request: z.infer<typeof SelectRequestSchema>): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      const validated = SelectRequestSchema.parse(request);
      this.validateTableName(validated.tableName);
      
      const knex = await this.getKnex();
      let query = knex(validated.tableName);

      // Apply SELECT fields
      if (validated.select && validated.select.length > 0) {
        query = query.select(validated.select);
      } else {
        query = query.select('*');
      }

      // Apply JOINs
      if (validated.joins) {
        for (const join of validated.joins) {
          this.validateTableName(join.table);
          switch (join.type) {
            case 'inner':
              query = query.innerJoin(join.table, join.on.column1, join.on.column2);
              break;
            case 'left':
              query = query.leftJoin(join.table, join.on.column1, join.on.column2);
              break;
            case 'right':
              query = query.rightJoin(join.table, join.on.column1, join.on.column2);
              break;
            case 'full':
              query = query.fullOuterJoin(join.table, join.on.column1, join.on.column2);
              break;
          }
        }
      }

      // Apply WHERE conditions
      if (validated.where) {
        query = query.where(validated.where);
      }

      // Apply ORDER BY
      if (validated.orderBy) {
        query = query.orderBy(validated.orderBy.column, validated.orderBy.direction);
      }

      // Apply LIMIT and OFFSET
      if (validated.limit) {
        query = query.limit(validated.limit);
      }
      if (validated.offset) {
        query = query.offset(validated.offset);
      }

      const result = await query;
      
      return {
        success: true,
        message: `Retrieved ${result.length} record(s)`,
        data: result,
        recordsAffected: result.length,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      if (error instanceof z.ZodError) {
        return {
          success: false,
          message: 'Validation failed',
          validationErrors: this.formatZodErrors(error),
          executionTime: Date.now() - startTime,
        };
      }
      
      throw error;
    }
  }

  async selectById(tableName: string, id: number): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      this.validateTableName(tableName);
      const knex = await this.getKnex();
      
      const result = await knex(tableName).where('id', id).first();
      
      if (!result) {
        return {
          success: false,
          message: `Record with id ${id} not found in ${tableName}`,
          executionTime: Date.now() - startTime,
        };
      }

      return {
        success: true,
        message: 'Record retrieved successfully',
        data: result,
        recordsAffected: 1,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      throw error;
    }
  }

  async selectWithPagination(
    tableName: string,
    page = 1,
    pageSize = 50,
    orderBy = 'id',
    direction: 'asc' | 'desc' = 'asc',
    whereClause?: Record<string, any>
  ): Promise<DatabaseResult & { pagination: { page: number; pageSize: number; total: number; totalPages: number } }> {
    const startTime = Date.now();
    
    try {
      this.validateTableName(tableName);
      const knex = await this.getKnex();
      
      const offset = (page - 1) * pageSize;
      
      // Get total count
      let countQuery = knex(tableName).count('* as total');
      if (whereClause) {
        countQuery = countQuery.where(whereClause);
      }
      const [{ total }] = await countQuery;
      const totalCount = parseInt(total as string);
      
      // Get paginated data
      let dataQuery = knex(tableName).select('*').orderBy(orderBy, direction).limit(pageSize).offset(offset);
      if (whereClause) {
        dataQuery = dataQuery.where(whereClause);
      }
      const data = await dataQuery;
      
      return {
        success: true,
        message: `Retrieved page ${page} of ${tableName}`,
        data,
        recordsAffected: data.length,
        executionTime: Date.now() - startTime,
        pagination: {
          page,
          pageSize,
          total: totalCount,
          totalPages: Math.ceil(totalCount / pageSize),
        },
      };
    } catch (error) {
      throw error;
    }
  }

  // ============================================================================
  // UPDATE Operations
  // ============================================================================

  async updateData(request: z.infer<typeof UpdateRequestSchema>): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      const validated = UpdateRequestSchema.parse(request);
      this.validateTableName(validated.tableName);
      
      const knex = await this.getKnex();
      const dataWithTimestamps = this.addTimestamps(validated.data, true);
      
      if (validated.validateOnly) {
        return {
          success: true,
          message: 'Validation successful',
          data: dataWithTimestamps,
          executionTime: Date.now() - startTime,
        };
      }

      const result = await knex(validated.tableName)
        .where(validated.whereClause)
        .update(dataWithTimestamps)
        .returning('*');

      return {
        success: true,
        message: `Successfully updated ${result.length} record(s)`,
        data: result,
        recordsAffected: result.length,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      if (error instanceof z.ZodError) {
        return {
          success: false,
          message: 'Validation failed',
          validationErrors: this.formatZodErrors(error),
          executionTime: Date.now() - startTime,
        };
      }
      
      throw error;
    }
  }

  async updateById(tableName: string, id: number, data: Record<string, any>): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      this.validateTableName(tableName);
      const knex = await this.getKnex();
      
      const dataWithTimestamps = this.addTimestamps(data, true);
      
      const result = await knex(tableName)
        .where('id', id)
        .update(dataWithTimestamps)
        .returning('*');

      if (result.length === 0) {
        return {
          success: false,
          message: `Record with id ${id} not found in ${tableName}`,
          executionTime: Date.now() - startTime,
        };
      }

      return {
        success: true,
        message: 'Record updated successfully',
        data: result[0],
        recordsAffected: 1,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      throw error;
    }
  }

  // ============================================================================
  // DELETE Operations
  // ============================================================================

  async deleteData(request: z.infer<typeof DeleteRequestSchema>): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      const validated = DeleteRequestSchema.parse(request);
      this.validateTableName(validated.tableName);
      
      if (!validated.confirmDelete) {
        return {
          success: false,
          message: 'Delete operation requires confirmation. Set confirmDelete: true',
          executionTime: Date.now() - startTime,
        };
      }

      const knex = await this.getKnex();
      
      // First, get the records that will be deleted for logging
      const recordsToDelete = await knex(validated.tableName)
        .where(validated.whereClause)
        .select('id');

      const deletedCount = await knex(validated.tableName)
        .where(validated.whereClause)
        .del();

      return {
        success: true,
        message: `Successfully deleted ${deletedCount} record(s)`,
        data: { deletedIds: recordsToDelete.map(r => r.id) },
        recordsAffected: deletedCount,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      if (error instanceof z.ZodError) {
        return {
          success: false,
          message: 'Validation failed',
          validationErrors: this.formatZodErrors(error),
          executionTime: Date.now() - startTime,
        };
      }
      
      throw error;
    }
  }

 async deleteById(tableName: string, id: number, confirmDelete = false): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      this.validateTableName(tableName);
      
      if (!confirmDelete) {
        return {
          success: false,
          message: 'Delete operation requires confirmation. Set confirmDelete: true',
          executionTime: Date.now() - startTime,
        };
      }

      const knex = await this.getKnex();
      
      const deletedCount = await knex(tableName).where('id', id).del();

      if (deletedCount === 0) {
        return {
          success: false,
          message: `Record with id ${id} not found in ${tableName}`,
          executionTime: Date.now() - startTime,
        };
      }

      return {
        success: true,
        message: 'Record deleted successfully',
        data: { deletedId: id },
        recordsAffected: 1,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      throw error;
    }
  }

  async bulkDeleteByIds(tableName: string, ids: number[], confirmDelete = false): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      this.validateTableName(tableName);
      
      if (!confirmDelete) {
        return {
          success: false,
          message: 'Bulk delete operation requires confirmation. Set confirmDelete: true',
          executionTime: Date.now() - startTime,
        };
      }

      if (!ids || ids.length === 0) {
        return {
          success: false,
          message: 'No IDs provided for bulk delete',
          executionTime: Date.now() - startTime,
        };
      }

      const knex = await this.getKnex();
      
      // First, get the records that will be deleted for logging
      const recordsToDelete = await knex(tableName)
        .whereIn('id', ids)
        .select('id');

      const deletedCount = await knex(tableName)
        .whereIn('id', ids)
        .del();

      const notFoundIds = ids.filter(id => 
        !recordsToDelete.some(record => record.id === id)
      );

      return {
        success: true,
        message: `Successfully deleted ${deletedCount} record(s) from ${tableName}`,
        data: { 
          deletedIds: recordsToDelete.map(r => r.id),
          notFoundIds,
          requestedIds: ids,
        },
        recordsAffected: deletedCount,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      throw error;
    }
  }

  async bulkDeleteByConditions(tableName: string, conditions: Record<string, any>, confirmDelete = false): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      this.validateTableName(tableName);
      
      if (!confirmDelete) {
        return {
          success: false,
          message: 'Bulk delete operation requires confirmation. Set confirmDelete: true',
          executionTime: Date.now() - startTime,
        };
      }

      if (!conditions || Object.keys(conditions).length === 0) {
        return {
          success: false,
          message: 'No conditions provided for bulk delete. This would delete all records, which is not allowed.',
          executionTime: Date.now() - startTime,
        };
      }

      const knex = await this.getKnex();
      
      // First, get the records that will be deleted for logging
      const recordsToDelete = await knex(tableName)
        .where(conditions)
        .select('id');

      if (recordsToDelete.length === 0) {
        return {
          success: false,
          message: 'No records found matching the provided conditions',
          executionTime: Date.now() - startTime,
        };
      }

      const deletedCount = await knex(tableName)
        .where(conditions)
        .del();

      return {
        success: true,
        message: `Successfully deleted ${deletedCount} record(s) from ${tableName}`,
        data: { 
          deletedIds: recordsToDelete.map(r => r.id),
          conditions,
        },
        recordsAffected: deletedCount,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      throw error;
    }
  }

  async deleteAllRecords(tableName: string, method: 'truncate' | 'delete' = 'delete', confirmDeleteAll = false): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      this.validateTableName(tableName);
      
      if (!confirmDeleteAll) {
        return {
          success: false,
          message: 'Delete all records operation requires explicit confirmation. Set confirmDeleteAll: true and provide tableNameConfirmation',
          executionTime: Date.now() - startTime,
        };
      }

      const knex = await this.getKnex();
      
      // Get count of records before deletion for reporting
      const [{ count }] = await knex(tableName).count('* as count');
      const recordCount = parseInt(count as string);
      
      if (recordCount === 0) {
        return {
          success: true,
          message: `Table ${tableName} is already empty`,
          data: { 
            recordsBeforeDeletion: 0,
            method,
            tableName,
          },
          recordsAffected: 0,
          executionTime: Date.now() - startTime,
        };
      }

      let deletedCount: number;
      
      if (method === 'truncate') {
        // TRUNCATE is faster and resets auto-increment counters
        await knex(tableName).truncate();
        deletedCount = recordCount;
      } else {
        // DELETE preserves auto-increment counters but is slower
        deletedCount = await knex(tableName).del();
      }

      console.log(`⚠️ CRITICAL: All ${deletedCount} records deleted from table ${tableName} using ${method.toUpperCase()} method`);

      return {
        success: true,
        message: `Successfully deleted all ${deletedCount} record(s) from ${tableName} using ${method.toUpperCase()} method`,
        data: { 
          recordsBeforeDeletion: recordCount,
          method,
          tableName,
          autoIncrementReset: method === 'truncate',
        },
        recordsAffected: deletedCount,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      throw error;
    }
  }

  // ============================================================================
  // BULK Operations
  // ============================================================================

  async executeBulkOperations(request: z.infer<typeof BulkOperationSchema>): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      const validated = BulkOperationSchema.parse(request);
      const knex = await this.getKnex();
      
      if (validated.useTransaction) {
        return await knex.transaction(async (trx) => {
          const results: BulkOperationResult[] = [];
          
          for (const operation of validated.operations) {
            this.validateTableName(operation.tableName);
            
            let result: any;
            switch (operation.type) {
              case 'insert':
                if (!operation.data) throw new Error('Insert operation requires data');
                const dataWithTimestamps = this.addTimestamps(operation.data);
                result = await trx(operation.tableName).insert(dataWithTimestamps).returning('*');
                break;
                
              case 'update':
                if (!operation.data || !operation.whereClause) {
                  throw new Error('Update operation requires data and whereClause');
                }
                const updateDataWithTimestamps = this.addTimestamps(operation.data, true);
                result = await trx(operation.tableName)
                  .where(operation.whereClause)
                  .update(updateDataWithTimestamps)
                  .returning('*');
                break;
                
              case 'delete':
                if (!operation.whereClause) {
                  throw new Error('Delete operation requires whereClause');
                }
                result = await trx(operation.tableName).where(operation.whereClause).del();
                break;
                
              default:
                throw new Error(`Unknown operation type: ${operation.type}`);
            }
            
            results.push({
              operation: operation.type,
              tableName: operation.tableName,
              recordsAffected: Array.isArray(result) ? result.length : result,
              data: result,
            });
          }
          
          return {
            success: true,
            message: `Successfully executed ${validated.operations.length} bulk operations`,
            data: results,
            recordsAffected: results.reduce((total, r) => total + r.recordsAffected, 0),
            executionTime: Date.now() - startTime,
          };
        });
      } else {
        // Execute without transaction
        const results: BulkOperationResult[] = [];
        
        for (const operation of validated.operations) {
          this.validateTableName(operation.tableName);
          
          let result: any;
          switch (operation.type) {
            case 'insert':
              if (!operation.data) throw new Error('Insert operation requires data');
              const dataWithTimestamps = this.addTimestamps(operation.data);
              result = await knex(operation.tableName).insert(dataWithTimestamps).returning('*');
              break;
              
            case 'update':
              if (!operation.data || !operation.whereClause) {
                throw new Error('Update operation requires data and whereClause');
              }
              const updateDataWithTimestamps = this.addTimestamps(operation.data, true);
              result = await knex(operation.tableName)
                .where(operation.whereClause)
                .update(updateDataWithTimestamps)
                .returning('*');
              break;
              
            case 'delete':
              if (!operation.whereClause) {
                throw new Error('Delete operation requires whereClause');
              }
              result = await knex(operation.tableName).where(operation.whereClause).del();
              break;
              
            default:
              throw new Error(`Unknown operation type: ${operation.type}`);
          }
          
          results.push({
            operation: operation.type,
            tableName: operation.tableName,
            recordsAffected: Array.isArray(result) ? result.length : result,
            data: result,
          });
        }
        
        return {
          success: true,
          message: `Successfully executed ${validated.operations.length} bulk operations`,
          data: results,
          recordsAffected: results.reduce((total, r) => total + r.recordsAffected, 0),
          executionTime: Date.now() - startTime,
        };
      }
    } catch (error) {
      if (error instanceof z.ZodError) {
        return {
          success: false,
          message: 'Validation failed',
          validationErrors: this.formatZodErrors(error),
          executionTime: Date.now() - startTime,
        };
      }
      
      throw error;
    }
  }

  // ============================================================================
  // TABLE Management Operations
  // ============================================================================

  async truncateTable(tableName: string): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      this.validateTableName(tableName);
      const knex = await this.getKnex();
      
      await knex(tableName).truncate();
      
      return {
        success: true,
        message: `Table ${tableName} truncated successfully`,
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      throw error;
    }
  }

  async getTableInfo(tableName: string): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      this.validateTableName(tableName);
      const knex = await this.getKnex();
      
      // Get row count
      const [{ count }] = await knex(tableName).count('* as count');
      const rowCount = parseInt(count as string);
      
      // Get table schema
      const columns = await this.dbUtil.getTableSchema(tableName);
      
      // Get foreign keys
      const foreignKeys = await this.dbUtil.getForeignKeys(tableName);
      
      // Find primary key
      const primaryKey = columns
        .filter(col => col.column_default?.includes('nextval'))
        .map(col => col.column_name);
      
      const tableInfo: TableInfo = {
        tableName,
        columnCount: columns.length,
        rowCount,
        primaryKey,
        foreignKeys: foreignKeys.map(fk => ({
          column: fk.column_name,
          referencedTable: fk.foreign_table_name,
          referencedColumn: fk.foreign_column_name,
        })),
      };
      
      return {
        success: true,
        message: `Table info retrieved for ${tableName}`,
        data: {
          ...tableInfo,
          columns: columns.map(col => ({
            name: col.column_name,
            type: col.data_type,
            nullable: col.is_nullable === 'YES',
            default: col.column_default,
          })),
        },
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      throw error;
    }
  }

  async getAllTables(): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      const tableNames = await this.dbUtil.getTableNames();
      const validTables = tableNames.filter(name => this.VALID_TABLES.includes(name));
      
      const tablesInfo = await Promise.all(
        validTables.map(async (tableName) => {
          const knex = await this.getKnex();
          const [{ count }] = await knex(tableName).count('* as count');
          return {
            tableName,
            rowCount: parseInt(count as string),
          };
        })
      );
      
      return {
        success: true,
        message: `Retrieved info for ${validTables.length} tables`,
        data: {
          totalTables: validTables.length,
          tables: tablesInfo,
        },
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      throw error;
    }
  }

  // ============================================================================
  // HEALTH and ANALYTICS
  // ============================================================================

  async getHealthCheck(): Promise<DatabaseHealth> {
    try {
      const health = await this.dbUtil.healthCheck();
      const tableNames = await this.dbUtil.getTableNames();
      const knex = await this.getKnex();
      
      return {
        ...health,
        tableCount: tableNames.length,
        connectionPool: {
          min: 0,
          max: 1,
          used: knex.client.pool ? knex.client.pool.numUsed() : 0,
          waiting: knex.client.pool ? knex.client.pool.numPendingAcquires() : 0,
        },
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        timestamp: new Date().toISOString(),
        database: 'unknown',
        tableCount: 0,
        connectionPool: { min: 0, max: 0, used: 0, waiting: 0 },
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  async getTableStatistics(): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      const knex = await this.getKnex();
      const validTables = this.VALID_TABLES;
      
      const statistics = await Promise.all(
        validTables.map(async (tableName) => {
          try {
            const exists = await knex.schema.hasTable(tableName);
            if (!exists) {
              return {
                tableName,
                exists: false,
                rowCount: 0,
                sizeKB: 0,
              };
            }
            
            const [{ count }] = await knex(tableName).count('* as count');
            const rowCount = parseInt(count as string);
            
            // Get table size (PostgreSQL specific)
            const [sizeResult] = await knex.raw(`
              SELECT pg_size_pretty(pg_total_relation_size(?)) as size,
                     pg_total_relation_size(?) as size_bytes
            `, [tableName, tableName]);
            
            return {
              tableName,
              exists: true,
              rowCount,
              size: sizeResult.size,
              sizeBytes: parseInt(sizeResult.size_bytes),
              sizeKB: Math.round(parseInt(sizeResult.size_bytes) / 1024),
            };
          } catch (error) {
            return {
              tableName,
              exists: false,
              error: error instanceof Error ? error.message : 'Unknown error',
            };
          }
        })
      );
      
      const totalRows = statistics.reduce((sum, stat) => sum + (stat.rowCount || 0), 0);
      const totalSizeKB = statistics.reduce((sum, stat) => sum + (stat.sizeKB || 0), 0);
      
      return {
        success: true,
        message: 'Database statistics retrieved successfully',
        data: {
          summary: {
            totalTables: validTables.length,
            existingTables: statistics.filter(s => s.exists).length,
            totalRows,
            totalSizeKB,
            totalSizeMB: Math.round(totalSizeKB / 1024),
          },
          tables: statistics,
        },
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      throw error;
    }
  }

  // ============================================================================
  // Raw SQL Execution (Use with caution)
  // ============================================================================

  async executeRawQuery(sql: string, bindings?: any[]): Promise<DatabaseResult> {
    const startTime = Date.now();
    
    try {
      // Security check - only allow SELECT statements for raw queries
      const trimmedSql = sql.trim().toLowerCase();
      if (!trimmedSql.startsWith('select')) {
        throw new Error('Raw queries are restricted to SELECT statements only');
      }
      
      const result = await this.dbUtil.executeRaw(sql, bindings);
      
      return {
        success: true,
        message: 'Raw query executed successfully',
        data: result.rows || result,
        recordsAffected: result.rowCount || (result.rows ? result.rows.length : 0),
        executionTime: Date.now() - startTime,
      };
    } catch (error) {
      throw error;
    }
  }
}