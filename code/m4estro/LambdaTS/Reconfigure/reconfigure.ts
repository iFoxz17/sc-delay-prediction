// const reconfigureHandler = async (event: any) => {
//     console.log('Reconfigure event:', JSON.stringify(event, null, 2));
//     const conditions = {
//         external: Math.random(),
//         SLS: Math.random() < 0.5,
//         delay: Math.round(Math.random() * 31)
//     };
//     const delay_threshold = 48;
//     const external=false
//     const { pathParameters } = event;
//     const { id } = pathParameters || {};
//     if (!id) {
//         return {
//             statusCode: 400,
//             body: JSON.stringify({ message: 'ID is required' }),
//         };
//     }

//     type Notification = {
//         external: boolean | null;
//         SLS: boolean | null;
//         delay: boolean | null;
//         message?: string;
//     };

//     let notification: Notification = {
//         external: null,
//         SLS: null,
//         delay: null,
//         message: '',
//     };

//     if (conditions.external > 0.7) {
//         notification.external = true;
//     }

//     if (conditions.SLS) {
//         notification.SLS = true;
//     }

//     if (conditions.delay > delay_threshold) {
//         notification.delay = true;
//     }

//     if (notification.external !== null && notification.SLS === null && notification.delay === null) {
//         notification.message = `Possible delay due to ${notification.external?'External Disruption':'Internal Disruption'}  with ${conditions.external}`;
//     } else if (notification.external === null && notification.SLS !== null && notification.delay === null) {
//         notification.message = 'Package lost at ${location} en route';
//     } else if (notification.external === null && notification.SLS === null && notification.delay !== null) {
//         notification.message = `Delay to Shipment greater than ${delay_threshold/24} days`;
//     } else if (notification.external !== null && notification.SLS !== null && notification.delay === null) {
//         notification.message = `Package lost at ${location} with disruption detected by ${notification.external?'External Disruption':'Internal Disruption'} with ${conditions.external}`;
//     } else if (notification.external !== null && notification.SLS === null && notification.delay !== null) {
//         notification.message = `Delay due to Shipment greater than ${delay_threshold/24} days due to ${notification.external?'External Disruption':'Internal Disruption'} with ${conditions.external}`;
//     }

//     console.log(`Reconfiguring service with ID: ${id}`);
//     console.log('Conditions:', conditions);
//     console.log('Notification:', notification);

//     return {
//         statusCode: 200,
//         body: JSON.stringify({
//             message: `Service with ID ${id} reconfigured successfully`,
//             conditions,
//             notification
//         }),
//     };
// };

// src/functions/reconfigure.ts
import { SQSEvent, SQSRecord, Context } from 'aws-lambda';
import { z } from 'zod';
import { DatabaseUtil } from '../utils/DatabaseUtils';
import { logger } from '../utils/logger';

// ============================================================================
// VALIDATION SCHEMAS
// ============================================================================

const ExternalDisruptionSchema = z.object({
  disruptionType: z.string().min(1, 'Disruption type is required'),
  severity: z.number().min(0).max(1, 'Severity must be between 0 and 1'),
});

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


const ReconfigurationMessageSchema = z.object({
  orderId: z.number().int().positive('Order ID must be a positive integer'),
  SLS: z.boolean().nullable(),
  external: ExternalDisruptionSchema.optional(),
  delay: DelayDataSchema.optional(),
});



type ReconfigurationMessage = z.infer<typeof ReconfigurationMessageSchema>;

type Notification = {
  external: boolean | null;
  SLS: boolean | null;
  delay: boolean | null;
  message: string | null;
};

interface ProcessingResult {
  orderId: number;
  disruptionCreated: boolean;
  message: string;
  error?: string;
}

// ============================================================================
// MAIN HANDLER
// ============================================================================

export const reconfigureHandler = async (
  event: SQSEvent,
  context: Context
): Promise<{
  processed: number;
  successful: number;
  failed: number;
  results: ProcessingResult[];
}> => {
  let dbUtil: DatabaseUtil | null = null;
  
  const results: ProcessingResult[] = [];
  let processed = 0;
  let successful = 0;
  let failed = 0;

  // Set Lambda context for proper cleanup
  context.callbackWaitsForEmptyEventLoop = false;

  try {
    logger.info('🔧 Starting reconfiguration handler', {
      recordCount: event.Records.length,
      functionName: context.functionName,
    });

    // Initialize database connection
    dbUtil = DatabaseUtil.fromEnvironment();
    const knex = await dbUtil.getKnex();

    // Process each SQS record
    for (const record of event.Records) {
      processed++;
      
      try {
        const result = await processSQSRecord(record, knex);
        results.push(result);
        
        if (result.error) {
          failed++;
          logger.error('❌ Failed to process record', {
            orderId: result.orderId,
            error: result.error,
          });
        } else {
          successful++;
          logger.info('✅ Successfully processed record', {
            orderId: result.orderId,
            disruptionCreated: result.disruptionCreated,
          });
        }

      } catch (error) {
        failed++;
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        
        results.push({
          orderId: 0,
          disruptionCreated: false,
          message: 'Failed to parse SQS record',
          error: errorMessage,
        });

        logger.error('❌ Error processing SQS record', {
          error: errorMessage,
          messageId: record.messageId,
        });
      }
    }

    logger.info('🏁 Reconfiguration processing completed', {
      processed,
      successful,
      failed,
    });

    return {
      processed,
      successful,
      failed,
      results,
    };

  } catch (error) {
    logger.error('❌ Critical error in reconfiguration handler', { error });
    throw error;

  } finally {
    if (dbUtil) {
      await dbUtil.closeConnection();
    }
  }
};

// ============================================================================
// SQS RECORD PROCESSING
// ============================================================================

async function processSQSRecord(
  record: SQSRecord,
  knex: any
): Promise<ProcessingResult> {
  
  try {
    // Parse and validate message
    const messageBody = JSON.parse(record.body);
    const validatedMessage = ReconfigurationMessageSchema.parse(messageBody);

    logger.debug('📩 Processing reconfiguration message', {
      orderId: validatedMessage.orderId,
      hasExternal: !!validatedMessage.external,
      hasDelay: !!validatedMessage.delay,
      hasSLS: validatedMessage.SLS !== undefined,
    });

    // // Verify order exists (uncomment if needed)
    // const orderExists = await verifyOrderExists(knex, validatedMessage.order_id);
    // if (!orderExists) {
    //   throw new Error(`Order ${validatedMessage.order_id} not found`);
    // }

    return await createDisruptionRecord(knex, validatedMessage);

  } catch (error) {
    if (error instanceof z.ZodError) {
      const validationErrors = error.errors.map(err => 
        `${err.path.join('.')}: ${err.message}`
      ).join(', ');
      
      throw new Error(`Validation failed: ${validationErrors}`);
    }

    throw error;
  }
}

// ============================================================================
// DATABASE OPERATIONS
// ============================================================================

// async function verifyOrderExists(knex: any, orderId: number): Promise<boolean> {
//   try {
//     const order = await knex('orders')
//       .where('id', orderId)
//       .select('id')
//       .first();

//     return !!order;

//   } catch (error) {
//     logger.error('❌ Error verifying order existence', {
//       orderId,
//       error: error instanceof Error ? error.message : 'Unknown error',
//     });
//     return false;
//   }
// }

async function createDisruptionRecord(
  knex: any,
  message: ReconfigurationMessage
): Promise<ProcessingResult> {
  
  const result: ProcessingResult = {
    orderId: message.orderId,
    disruptionCreated: false,
    message: '',
  };

  try {
    const now = new Date();
    
    // Prepare disruption data
    const disruptionData: any = {
      order_id: message.orderId,
      SLS: message.SLS || false,
      external: message.external ? true : null,
      external_data: message.external ? JSON.stringify(message.external) : null,
      delayed: message.delay ? true : null,
      delay_data: message.delay ? JSON.stringify(message.delay) : null,
      message: generateDisruptionMessage(message),
      created_at: now,
      updated_at: now,
    };

    // Insert disruption record
    const [disruptionRecord] = await knex('disruptions')
      .insert(disruptionData)
      .returning('*');

    result.disruptionCreated = true;
    result.message = `Disruption record ${disruptionRecord.id} created for order ${message.orderId}`;

    logger.info('🚨 Created disruption record', {
      orderId: message.orderId,
      disruptionId: disruptionRecord.id,
      external: !!message.external,
      delayed: !!message.delay,
      sls: message.SLS || false,
      message: result.message,
    });

  } catch (error) {
    result.error = error instanceof Error ? error.message : 'Database operation failed';
    logger.error('❌ Failed to create disruption record', {
      orderId: message.orderId,
      error: result.error,
    });
  }

  return result;
}

// ============================================================================
// MESSAGE GENERATION (Using existing logic from original file)
// ============================================================================

function generateDisruptionMessage(message: ReconfigurationMessage): string {
  const delay_threshold = 48; // hours
  const location = 'processing facility'; // default location
  
  // Map incoming data to notification structure
  let notification: Notification = {
    external: null,
    SLS: null,
    delay: null,
    message: '',
  };

  // Set external flag based on incoming data
  if (message.external) {
    notification.external = true;
  }

  // Set SLS flag based on incoming data
  if (message.SLS ) {
    notification.SLS = true;
  }

  // Set delay flag based on incoming data
  if (message.delay) {
    const avgDelay = ((message.delay?.total?.lower || 0) + (message.delay?.total?.upper || 0)) / 2;
    notification.delay = avgDelay > delay_threshold;
  }

  // Use existing message logic from original file
  if (notification.external !== null && notification.SLS === null && notification.delay === null) {
    const externalSeverity = message.external?.severity || 0;
    notification.message = `Possible delay due to ${notification.external ? 'External Disruption' : 'Internal Disruption'} with ${externalSeverity}`;
  } else if (notification.external === null && notification.SLS !== null && notification.delay === null) {
    notification.message = `Package lost at ${location} en route`;
  } else if (notification.external === null && notification.SLS === null && notification.delay !== null) {
    notification.message = `Delay to Shipment greater than ${delay_threshold/24} days`;
  } else if (notification.external !== null && notification.SLS !== null && notification.delay === null) {
    const externalSeverity = message.external?.severity || 0;
    notification.message = `Package lost at ${location} with disruption detected by ${notification.external ? 'External Disruption' : 'Internal Disruption'} with ${externalSeverity}`;
  } else if (notification.external !== null && notification.SLS === null && notification.delay !== null) {
    const externalSeverity = message.external?.severity || 0;
    notification.message = `Delay due to Shipment greater than ${delay_threshold/24} days due to ${notification.external ? 'External Disruption' : 'Internal Disruption'} with ${externalSeverity}`;
  } else {
    // Default message when no specific conditions match
    notification.message = 'Disruption detected for order monitoring';
  }

  return notification.message || 'Disruption detected for order monitoring';
}

export default reconfigureHandler;