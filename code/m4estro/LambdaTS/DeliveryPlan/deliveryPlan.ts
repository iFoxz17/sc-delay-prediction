// src/functions/disruptionRetriever.ts
import { APIGatewayProxyEvent, APIGatewayProxyResult, Context } from 'aws-lambda';
import { z } from 'zod';
import { DatabaseUtil } from '../utils/DatabaseUtils';
import { ResponseHelper } from '../utils/responseHelper';
import { logger } from '../utils/logger';

// ============================================================================
// VALIDATION SCHEMAS
// ============================================================================


const DelayDataSchema = z.object({
  dispatch: z.object({
    lower: z.number(),
    upper: z.number(),
  }).optional(),
  shipment: z.object({
    lower: z.number(),
    upper: z.number(),
  }).optional(),
  total: z.object({
    lower: z.number(),
    upper: z.number(),
  }).optional(),
  expected_order_delivery_time: z.string().optional(),
  estimated_order_delivery_time: z.string().optional(),
});

const ExternalDisruptionSchema = z.object({
  disruptionType: z.string().min(1, 'Disruption type is required'),
  severity: z.number().min(0).max(1, 'Severity must be between 0 and 1'),
});

const PathParametersSchema = z.object({
  id: z.string().transform((val) => parseInt(val, 10)).refine((val) => !isNaN(val) && val > 0, {
    message: "Order ID must be a positive integer"
  }),
});

const QueryParametersSchema = z.object({
  order_id: z.string().transform((val) => parseInt(val, 10)).refine((val) => !isNaN(val) && val > 0, {
    message: "order_id must be a positive integer"
  }),
});

// ============================================================================
// RESPONSE TYPES
// ============================================================================

type DelayData = z.infer<typeof DelayDataSchema>;
type ExternalDisruptionData = z.infer<typeof ExternalDisruptionSchema>;

interface DisruptionRecord {
  id: number;
  order_id: number;
  SLS: boolean;
  external: boolean;
  external_data: ExternalDisruptionData | null;
  delayed: boolean;
  delay_data: DelayData | null;
  message: string | null;
  created_at: Date;
  updated_at: Date;
}

interface DisruptionResponse {
  order_id: number;
  total_disruptions: number;
  latest_disruption: DisruptionRecord | null;
  all_disruptions: DisruptionRecord[];
  summary: {
    has_sls: boolean;
    has_external_disruption: boolean;
    has_delays: boolean;
    latest_message: string | null;
    first_disruption_date: Date | null;
    latest_disruption_date: Date | null;
    delay_summary?: {
      dispatch_delay_hours?: { lower: number; upper: number };
      shipment_delay_hours?: { lower: number; upper: number };
      total_delay_hours?: { lower: number; upper: number };
      expected_delivery?: string;
      estimated_delivery?: string;
    };
    external_summary?: {
      disruption_type?: string;
      severity?: number;
    };
  };
}

// ============================================================================
// MAIN HANDLER
// ============================================================================

export const deliveryPlanHandler = async (
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> => {
  let dbUtil: DatabaseUtil | null = null;

  // Set Lambda context for proper cleanup
  context.callbackWaitsForEmptyEventLoop = false;

  try {
    logger.info('🔍 Starting disruption retrieval handler', {
      httpMethod: event.httpMethod,
      pathParameters: event.pathParameters,
      queryStringParameters: event.queryStringParameters,
    });

    // Handle CORS preflight
    if (event.httpMethod === 'OPTIONS') {
      return ResponseHelper.success({}, 'CORS preflight successful', 200);
    }

    // Validate HTTP method
    if (event.httpMethod !== 'GET') {
      return ResponseHelper.methodNotAllowed(event.httpMethod);
    }

    // Extract and validate order_id from path or query parameters
    let orderId: number;

    if (event.pathParameters?.id) {
      // Path parameter format: /disruptions/{id}
      const pathValidation = PathParametersSchema.safeParse(event.pathParameters);
      if (!pathValidation.success) {
        return ResponseHelper.validationError(pathValidation.error);
      }
      orderId = pathValidation.data.id;
    } else if (event.queryStringParameters?.order_id) {
      // Query parameter format: /disruptions?order_id=123
      const queryValidation = QueryParametersSchema.safeParse(event.queryStringParameters);
      if (!queryValidation.success) {
        return ResponseHelper.validationError(queryValidation.error);
      }
      orderId = queryValidation.data.order_id;
    } else {
      return ResponseHelper.badRequest('Order ID is required. Use path parameter /disruptions/{id} or query parameter ?order_id={id}');
    }

    logger.info('📝 Processing disruption retrieval', {
      orderId,
    });

    // Initialize database connection
    dbUtil = DatabaseUtil.fromEnvironment();
    const knex = await dbUtil.getKnex();

    // Verify order exists
    const orderExists = await verifyOrderExists(knex, orderId);
    if (!orderExists) {
      return ResponseHelper.notFound(`Order with ID ${orderId} not found`);
    }

    // Get disruption data (always include all records, sorted newest first)
    const disruptionResponse = await getDisruptionData(knex, orderId);

    logger.info('✅ Successfully retrieved disruption data', {
      orderId,
      totalDisruptions: disruptionResponse.total_disruptions,
      hasLatest: !!disruptionResponse.latest_disruption,
    });

    return ResponseHelper.success(
      disruptionResponse,
      disruptionResponse.total_disruptions > 0 
        ? `Retrieved ${disruptionResponse.total_disruptions} disruption record(s) for order ${orderId}`
        : `No disruptions found for order ${orderId}`,
      200,
      {
        recordsAffected: disruptionResponse.total_disruptions,
      }
    );

  } catch (error) {
    logger.error('❌ Error in disruption retrieval handler', { error });

    if (error instanceof z.ZodError) {
      return ResponseHelper.validationError(error);
    }

    // Handle database errors
    if (error instanceof Error && error.message.includes('database')) {
      return ResponseHelper.handleDatabaseError(error);
    }

    return ResponseHelper.error(
      'Failed to retrieve disruption data',
      500,
      process.env.NODE_ENV === 'development' ? {
        error: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined,
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

/**
 * Verify that the order exists in the database
 */
async function verifyOrderExists(knex: any, orderId: number): Promise<boolean> {
  try {
    const order = await knex('orders')
      .where('id', orderId)
      .select('id')
      .first();

    return !!order;

  } catch (error) {
    logger.error('❌ Error verifying order existence', {
      orderId,
      error: error instanceof Error ? error.message : 'Unknown error',
    });
    throw new Error(`Database error while verifying order: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Get disruption data for the specified order
 */
async function getDisruptionData(
  knex: any, 
  orderId: number
): Promise<DisruptionResponse> {
  
  try {
    // Get all disruptions for the order, ordered by creation date (newest first)
    const allDisruptions = await knex('disruptions')
      .where('order_id', orderId)
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
        'updated_at'
      ])
      .orderBy('created_at', 'desc');

    logger.debug('📊 Found disruptions', {
      orderId,
      count: allDisruptions.length,
    });

    // Process external_data and delay_data JSON fields with proper validation
    const processedDisruptions = allDisruptions.map(disruption => ({
      ...disruption,
      external_data: disruption.external_data ? safeParseAndValidateJSON(disruption.external_data, ExternalDisruptionSchema) : null,
      delay_data: disruption.delay_data ? safeParseAndValidateJSON(disruption.delay_data, DelayDataSchema) : null,
    }));

    // Get the latest disruption (first in the newest-first ordered list)
    const latestDisruption = processedDisruptions.length > 0 ? processedDisruptions[0] : null;

    // Calculate summary statistics
    const summary = calculateDisruptionSummary(processedDisruptions);

    const response: DisruptionResponse = {
      order_id: orderId,
      total_disruptions: processedDisruptions.length,
      latest_disruption: latestDisruption,
      all_disruptions: processedDisruptions, // Always include all disruptions
      summary,
    };

    return response;

  } catch (error) {
    logger.error('❌ Error getting disruption data', {
      orderId,
      error: error instanceof Error ? error.message : 'Unknown error',
    });
    throw new Error(`Database error while getting disruption data: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Calculate summary statistics from disruption records
 */
function calculateDisruptionSummary(disruptions: DisruptionRecord[]): DisruptionResponse['summary'] {
  if (disruptions.length === 0) {
    return {
      has_sls: false,
      has_external_disruption: false,
      has_delays: false,
      latest_message: null,
      first_disruption_date: null,
      latest_disruption_date: null,
    };
  }

  // Get latest disruption data for summary (first item since sorted newest first)
  const latestChronologically = disruptions[0];
  const oldestChronologically = disruptions[disruptions.length - 1];
  
  const summary: DisruptionResponse['summary'] = {
    has_sls: disruptions.some(d => d.SLS),
    has_external_disruption: disruptions.some(d => d.external),
    has_delays: disruptions.some(d => d.delayed),
    latest_message: latestChronologically.message,
    first_disruption_date: oldestChronologically.created_at,
    latest_disruption_date: latestChronologically.created_at,
  };

  // Add delay summary from latest disruption with delay data (first item since sorted newest first)
  const latestDelayDisruption = disruptions.find(d => d.delayed && d.delay_data);
  if (latestDelayDisruption?.delay_data) {
    const delayData = latestDelayDisruption.delay_data;
    summary.delay_summary = {
      ...(delayData.dispatch && { dispatch_delay_hours: delayData.dispatch }),
      ...(delayData.shipment && { shipment_delay_hours: delayData.shipment }),
      ...(delayData.total && { total_delay_hours: delayData.total }),
      ...(delayData.expected_order_delivery_time && { expected_delivery: delayData.expected_order_delivery_time }),
      ...(delayData.estimated_order_delivery_time && { estimated_delivery: delayData.estimated_order_delivery_time }),
    };
  }

  // Add external summary from latest external disruption (first item since sorted newest first)
  const latestExternalDisruption = disruptions.find(d => d.external && d.external_data);
  if (latestExternalDisruption?.external_data) {
    const externalData = latestExternalDisruption.external_data;
    summary.external_summary = {
      ...(externalData.disruptionType && { disruption_type: externalData.disruptionType }),
      ...(externalData.severity !== undefined && { severity: externalData.severity }),
    };
  }

  logger.debug('📈 Calculated disruption summary', {
    totalDisruptions: disruptions.length,
    hasSLS: summary.has_sls,
    hasExternal: summary.has_external_disruption,
    hasDelays: summary.has_delays,
    hasDelaySummary: !!summary.delay_summary,
    hasExternalSummary: !!summary.external_summary,
  });

  return summary;
}

/**
 * Safely parse JSON string and validate against schema, return null if invalid
 */
function safeParseAndValidateJSON<T>(jsonString: string, schema: z.ZodSchema<T>): T | null {
  try {
    const parsed = JSON.parse(jsonString);
    const validated = schema.safeParse(parsed);
    
    if (validated.success) {
      return validated.data;
    } else {
      logger.warn('⚠️ JSON data failed schema validation', { 
        jsonString,
        errors: validated.error.errors 
      });
      return null;
    }
  } catch (error) {
    logger.warn('⚠️ Failed to parse JSON data', { jsonString });
    return null;
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get disruption statistics for monitoring/analytics (optional endpoint)
 */
export async function getDisruptionStatistics(knex: any, timeframe: 'day' | 'week' | 'month' = 'week'): Promise<any> {
  try {
    const timeMap = {
      day: '1 day',
      week: '7 days',
      month: '30 days'
    };

    const since = knex.raw(`NOW() - INTERVAL '${timeMap[timeframe]}'`);

    const stats = await knex('disruptions')
      .where('created_at', '>=', since)
      .select([
        knex.raw('COUNT(*) as total_disruptions'),
        knex.raw('COUNT(DISTINCT order_id) as affected_orders'),
        knex.raw('SUM(CASE WHEN SLS = true THEN 1 ELSE 0 END) as sls_disruptions'),
        knex.raw('SUM(CASE WHEN external = true THEN 1 ELSE 0 END) as external_disruptions'),
        knex.raw('SUM(CASE WHEN delayed = true THEN 1 ELSE 0 END) as delay_disruptions'),
        knex.raw('AVG(CASE WHEN SLS = true THEN 1.0 ELSE 0.0 END) as sls_rate'),
      ])
      .first();

    return {
      timeframe,
      period: timeMap[timeframe],
      statistics: {
        total_disruptions: parseInt(stats.total_disruptions) || 0,
        affected_orders: parseInt(stats.affected_orders) || 0,
        sls_disruptions: parseInt(stats.sls_disruptions) || 0,
        external_disruptions: parseInt(stats.external_disruptions) || 0,
        delay_disruptions: parseInt(stats.delay_disruptions) || 0,
        sls_rate: parseFloat(stats.sls_rate) || 0,
      },
    };

  } catch (error) {
    logger.error('❌ Error getting disruption statistics', { error });
    return null;
  }
}


export default deliveryPlanHandler;