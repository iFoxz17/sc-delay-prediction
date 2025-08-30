// src/functions/recentDisruptions.ts
import { APIGatewayProxyEvent, APIGatewayProxyResult, Context } from 'aws-lambda';
import { DatabaseUtil } from '../utils/DatabaseUtils';
import { ResponseHelper } from '../utils/responseHelper';
import { logger } from '../utils/logger';

// ============================================================================
// CONSTANTS - Fixed values, no query parameters from frontend
// ============================================================================


// ============================================================================
// TYPES
// ============================================================================

interface DisruptionRecord {
  id: number;
  order_id: number;
  SLS: boolean;
  external: boolean;
  external_data: any | null;
  delayed: boolean;
  delay_data: any | null;
  message: string | null;
  created_at: string;
  updated_at: string;
}


// ============================================================================
// MAIN HANDLER
// ============================================================================

export const recentDisruptionsHandler = async (
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> => {
  let dbUtil: DatabaseUtil | null = null;

  // Set Lambda context for proper cleanup
  context.callbackWaitsForEmptyEventLoop = false;

  try {
    logger.info('🚨 Starting recent disruptions handler', {
      functionName: context.functionName,
      requestId: context.awsRequestId,
    });

    // Validate HTTP method
    if (event.httpMethod !== 'GET') {
      return ResponseHelper.methodNotAllowed(event.httpMethod);
    }

    // Initialize database connection
    dbUtil = DatabaseUtil.fromEnvironment();
    const knex = await dbUtil.getKnex();

    // Get recent disruptions
    const result = await getRecentDisruptions(knex);

    logger.info('✅ Recent disruptions retrieved successfully', {
      disruptionCount: result.length
    });
    return ResponseHelper.success(
      result,
      `Retrieved ${result.length} recent disruptions`,
      200,
      {
        recordsAffected: result.length,
        executionTime: Date.now(),
      }
    );

  } catch (error) {
    logger.error('❌ Error in recent disruptions handler', { error });

    if (error instanceof Error && error.message.includes('database')) {
      return ResponseHelper.handleDatabaseError(error);
    }

    return ResponseHelper.error(
      'Failed to retrieve recent disruptions',
      500,
      process.env.NODE_ENV === 'development' ? {
        error: error instanceof Error ? error.message : 'Unknown error',
      } : undefined
    );

  } finally {
    if (dbUtil) {
      await dbUtil.closeConnection();
      logger.debug('🔐 Database connection closed');
    }
  }
};
     
// ============================================================================
// DATABASE OPERATIONS
// ============================================================================

async function getRecentDisruptions(
  knex: any
): Promise<DisruptionRecord[]> {
  
  try {
    logger.info('🔍 Querying recent disruptions from database');

    // Calculate the time threshold
    const timeThreshold = new Date(Date.now() - 10 * 60 * 1000);
    const queryTimestamp = new Date().toISOString();

    // Build the main query - only from disruptions table
    const disruptionsQuery = knex('disruptions')
      .select([
        'id',
        'order_id',
        'SLS',
        'external',
        'external_data',
        'delayed',
        'delay_data',
        'message',
        'created_at',
        'updated_at',
      ])
      .where('created_at', '>=', timeThreshold)
      .orderBy('created_at', 'desc');

    // Execute the query
    const results = await disruptionsQuery;

   

    // Process and format the results
    const formattedDisruptions: DisruptionRecord[] = results.map(disruption => ({
      id: disruption.id,
      order_id: disruption.order_id,
      SLS: disruption.SLS,
      external: disruption.external,
      external_data: disruption.external_data ? 
        safeParseJSON(disruption.external_data) : null,
      delayed: disruption.delayed,
      delay_data: disruption.delay_data ? 
        safeParseJSON(disruption.delay_data) : null,
      message: disruption.message,
      created_at: disruption.created_at.toISOString(),
      updated_at: disruption.updated_at.toISOString(),
    }));

    logger.info('📊 Query completed successfully', {
      resultsFound: formattedDisruptions.length,
      timeThreshold: timeThreshold.toISOString(),
    });

    return formattedDisruptions;

  } catch (error) {
    logger.error('❌ Error querying recent disruptions', { error });
    throw new Error(`Database query failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Safely parse JSON string, return null if invalid
 */
function safeParseJSON(jsonString: string): any {
  try {
    return JSON.parse(jsonString);
  } catch (error) {
    logger.warn('⚠️ Failed to parse JSON string', { 
      jsonString: jsonString.substring(0, 100),
      error: error instanceof Error ? error.message : 'Parse error'
    });
    return null;
  }
}



export default recentDisruptionsHandler;