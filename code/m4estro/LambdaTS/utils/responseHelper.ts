// src/utils/responseHelper.ts
import { APIGatewayProxyResult } from 'aws-lambda';
import { z } from 'zod';

export interface ErrorResponse {
  error: string;
  message: string;
  details?: any;
  timestamp: string;
  requestId?: string;
}

export interface SuccessResponse {
  success: boolean;
  message: string;
  data?: any;
  meta?: {
    recordsAffected?: number;
    executionTime?: number;
    pagination?: {
      page: number;
      pageSize: number;
      total: number;
      totalPages: number;
    };
  };
  timestamp: string;
}

export class ResponseHelper {
  private static createHeaders(additionalHeaders: Record<string, string> = {}): Record<string, string> {
    return {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
      'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS,PATCH',
      'Access-Control-Max-Age': '86400',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block',
      ...additionalHeaders,
    };
  }

  static success(
    data?: any,
    message = 'Operation completed successfully',
    statusCode = 200,
    meta?: SuccessResponse['meta']
  ): APIGatewayProxyResult {
    const response: SuccessResponse = {
      success: true,
      message,
      data,
      meta,
      timestamp: new Date().toISOString(),
    };

    return {
      statusCode,
      headers: this.createHeaders(),
      body: JSON.stringify(response, null, 2),
    };
  }

  static error(
    message: string,
    statusCode = 500,
    details?: any,
    requestId?: string
  ): APIGatewayProxyResult {
    const response: ErrorResponse = {
      error: this.getErrorName(statusCode),
      message,
      details,
      timestamp: new Date().toISOString(),
      requestId,
    };

    console.error(`Error ${statusCode}:`, response);

    return {
      statusCode,
      headers: this.createHeaders(),
      body: JSON.stringify(response, null, 2),
    };
  }

  static badRequest(message: string, details?: any): APIGatewayProxyResult {
    return this.error(message, 400, details);
  }

  static unauthorized(message = 'Unauthorized access'): APIGatewayProxyResult {
    return this.error(message, 401);
  }

  static forbidden(message = 'Access forbidden'): APIGatewayProxyResult {
    return this.error(message, 403);
  }

  static notFound(message = 'Resource not found'): APIGatewayProxyResult {
    return this.error(message, 404);
  }

  static methodNotAllowed(method: string): APIGatewayProxyResult {
    return this.error(`HTTP method ${method} not allowed`, 405);
  }

  static conflict(message: string, details?: any): APIGatewayProxyResult {
    return this.error(message, 409, details);
  }

  static validationError(errors: z.ZodError): APIGatewayProxyResult {
    const details = errors.errors.map(error => ({
      field: error.path.join('.'),
      message: error.message,
      // Handle the input property safely - it may not exist on all ZodIssue types
      value: 'received' in error ? error.received : undefined,
    }));

    return this.badRequest('Validation failed', { validationErrors: details });
  }

  static handleDatabaseError(error: any): APIGatewayProxyResult {
    console.error('Database error:', error);

    // Handle specific database errors
    if (error.code) {
      switch (error.code) {
        case '23505': // Unique violation
          return this.conflict('Record already exists', {
            constraint: error.constraint,
            detail: error.detail,
          });
        
        case '23503': // Foreign key violation
          return this.badRequest('Invalid reference - related record does not exist', {
            constraint: error.constraint,
            detail: error.detail,
          });
        
        case '23502': // Not null violation
          return this.badRequest('Required field is missing', {
            column: error.column,
            table: error.table,
          });
        
        case '42P01': // Undefined table
          return this.badRequest('Table does not exist', {
            table: error.table,
          });
        
        case '42703': // Undefined column
          return this.badRequest('Column does not exist', {
            column: error.column,
            table: error.table,
          });
        
        case '08006': // Connection failure
        case '08001': // Unable to connect
          return this.error('Database connection failed', 503);
        
        case '57014': // Query canceled
          return this.error('Query timed out', 408);
        
        default:
          return this.error(`Database error: ${error.message}`, 500, {
            code: error.code,
            detail: error.detail,
          });
      }
    }

    // Handle connection timeouts
    if (error.message?.includes('timeout') || error.message?.includes('TIMEOUT')) {
      return this.error('Database operation timed out', 408);
    }

    // Handle connection errors
    if (error.message?.includes('connection') || error.message?.includes('ECONNREFUSED')) {
      return this.error('Unable to connect to database', 503);
    }

    // Generic database error
    return this.error('Database operation failed', 500, {
      message: error.message,
      name: error.name,
    });
  }

  static created(data: any, message = 'Resource created successfully'): APIGatewayProxyResult {
    return this.success(data, message, 201);
  }

  static noContent(message = 'Operation completed successfully'): APIGatewayProxyResult {
    return {
      statusCode: 204,
      headers: this.createHeaders(),
      body: '',
    };
  }

  static serviceUnavailable(message = 'Service temporarily unavailable'): APIGatewayProxyResult {
    return this.error(message, 503);
  }

  private static getErrorName(statusCode: number): string {
    const errorNames: Record<number, string> = {
      400: 'Bad Request',
      401: 'Unauthorized',
      403: 'Forbidden',
      404: 'Not Found',
      405: 'Method Not Allowed',
      408: 'Request Timeout',
      409: 'Conflict',
      422: 'Unprocessable Entity',
      429: 'Too Many Requests',
      500: 'Internal Server Error',
      502: 'Bad Gateway',
      503: 'Service Unavailable',
      504: 'Gateway Timeout',
    };

    return errorNames[statusCode] || 'Unknown Error';
  }

  static paginated(
    data: any[],
    pagination: {
      page: number;
      pageSize: number;
      total: number;
      totalPages: number;
    },
    message = 'Data retrieved successfully'
  ): APIGatewayProxyResult {
    return this.success(data, message, 200, {
      recordsAffected: data.length,
      pagination,
    });
  }

  static bulk(
    results: any[],
    message = 'Bulk operation completed successfully'
  ): APIGatewayProxyResult {
    const totalRecords = results.reduce((sum, result) => {
      return sum + (result.recordsAffected || 0);
    }, 0);

    return this.success(results, message, 200, {
      recordsAffected: totalRecords,
    });
  }
}

// CORS preflight handler
export function handleCorsPreflightRequest(): APIGatewayProxyResult {
  return {
    statusCode: 200,
    headers: ResponseHelper['createHeaders'](),
    body: '',
  };
}

// Request body parser with validation
export function parseRequestBody(body: string | null): any {
  if (!body) {
    throw new Error('Request body is required');
  }

  try {
    return JSON.parse(body);
  } catch (error) {
    throw new Error('Invalid JSON in request body');
  }
}

// Request validation schemas
export const PaginationSchema = z.object({
  page: z.number().int().positive().default(1),
  pageSize: z.number().int().positive().max(1000).default(50),
  orderBy: z.string().default('id'),
  direction: z.enum(['asc', 'desc']).default('asc'),
});

export const BulkRequestSchema = z.object({
  operations: z.array(z.object({
    type: z.enum(['insert', 'update', 'delete']),
    tableName: z.string(),
    data: z.record(z.any()).optional(),
    whereClause: z.record(z.any()).optional(),
  })).min(1),
  useTransaction: z.boolean().default(true),
});

// Path parameter helpers
export function getPathParameter(event: any, paramName: string): string {
  const value = event.pathParameters?.[paramName];
  if (!value) {
    throw new Error(`Path parameter '${paramName}' is required`);
  }
  return value;
}

export function getQueryParameter(event: any, paramName: string, defaultValue?: string): string | undefined {
  return event.queryStringParameters?.[paramName] || defaultValue;
}

export function getRequiredQueryParameter(event: any, paramName: string): string {
  const value = event.queryStringParameters?.[paramName];
  if (!value) {
    throw new Error(`Query parameter '${paramName}' is required`);
  }
  return value;
}

// Request ID generator
export function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Security helpers
export function sanitizeInput(input: any): any {
  if (typeof input === 'string') {
    // Basic XSS prevention
    return input
      .replace(/[<>]/g, '')
      .replace(/javascript:/gi, '')
      .replace(/on\w+=/gi, '')
      .trim();
  }
  
  if (Array.isArray(input)) {
    return input.map(sanitizeInput);
  }
  
  if (typeof input === 'object' && input !== null) {
    const sanitized: any = {};
    for (const [key, value] of Object.entries(input)) {
      sanitized[sanitizeInput(key)] = sanitizeInput(value);
    }
    return sanitized;
  }
  
  return input;
}

// Rate limiting helpers (basic implementation)
const requestCounts = new Map<string, { count: number; lastReset: number }>();

export function checkRateLimit(
  identifier: string,
  maxRequests = 100,
  windowMs = 60000
): { allowed: boolean; remaining: number; resetTime: number } {
  const now = Date.now();
  const windowStart = now - windowMs;
  
  let requestData = requestCounts.get(identifier);
  
  if (!requestData || requestData.lastReset < windowStart) {
    requestData = { count: 0, lastReset: now };
    requestCounts.set(identifier, requestData);
  }
  
  requestData.count++;
  
  const remaining = Math.max(0, maxRequests - requestData.count);
  const allowed = requestData.count <= maxRequests;
  const resetTime = requestData.lastReset + windowMs;
  
  return { allowed, remaining, resetTime };
}