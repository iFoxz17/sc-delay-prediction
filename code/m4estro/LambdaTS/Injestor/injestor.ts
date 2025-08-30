// src/functions/order_injestor.ts
import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { LambdaClient, InvokeCommand } from '@aws-sdk/client-lambda';
import { SQSClient, SendMessageCommand } from '@aws-sdk/client-sqs';
import { z } from 'zod';
import { DatabaseUtil } from '../utils/DatabaseUtils';

// ============================================================================
// VALIDATION SCHEMAS
// ============================================================================

const RequestBodySchema = z.object({
  type: z.string(),
  content: z.object({}).passthrough(),
});

const CreateOrderSchema = z.object({
  tracking_link: z.string().optional(),
  tracking_number: z.string().min(1, 'Tracking number is required'),
  supplier_name: z.string().min(1, 'Supplier name is required'),
  site_location: z.string().nullable().optional(),
  manufacturer_id: z.number().int().positive().optional(),
  manufacturer_order_id: z.number().int().positive(),
  carrier_name: z.string().nullable().optional(),
  status: z.string().default('PENDING'),
  manufacturer_creation_timestamp: z.string().datetime().default(() => new Date().toISOString()),
  manufacturer_estimated_delivery_timestamp: z.string().datetime().optional().nullable(),
  manufacturer_confirmed_delivery_timestamp: z.string().datetime().optional().nullable(),
  carrier_creation_timestamp: z.string().datetime().optional().nullable(),
  carrier_estimated_delivery_timestamp: z.string().datetime().optional().nullable(),
  carrier_confirmed_delivery_timestamp: z.string().datetime().optional().nullable(),
});

type CreateOrderInput = z.infer<typeof CreateOrderSchema>;

// ============================================================================
// ENVIRONMENT VARIABLES
// ============================================================================

const CARRIER_LAMBDA_ARN = process.env.CARRIER_LAMBDA_ARN!;
const AWS_REGION = process.env.AWS_REGION || 'us-east-1';
//const TRACKING_UPDATES_SQS_URL = process.env.TRACKING_UPDATES_SQS_URL!;

// Initialize AWS clients
const lambdaClient = new LambdaClient({ region: AWS_REGION });
//const sqsClient = new SQSClient({ region: AWS_REGION });

// ============================================================================
// MAIN HANDLER
// ============================================================================

export const injestorHandler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
  let dbUtil: DatabaseUtil | null = null;

  try {
    console.log('🚀 Starting order injestor handler');
    
    // Validate HTTP method
    if (event.httpMethod !== 'POST') {
      return createResponse(405, {
        error: 'Method Not Allowed',
        message: 'Only POST method is supported',
      });
    }

    // Validate and parse request body
    const requestBody = RequestBodySchema.parse(JSON.parse(event.body || '{}'));
    console.log('📥 Received request body:', requestBody);
    const orderData: CreateOrderInput = CreateOrderSchema.parse(requestBody.content);

    console.log(`📦 Processing order for tracking number: ${orderData.tracking_number}`);

    // Initialize database connection
    dbUtil = DatabaseUtil.fromEnvironment();
    const knex = await dbUtil.getKnex();

    // Check if tracking number already exists
    const existingOrder = await knex('orders')
      .where('tracking_number', orderData.tracking_number)
      .first();

    if (existingOrder) {
      console.warn(`⚠️ Order with tracking number ${orderData.tracking_number} already exists`);
      return createResponse(409, {
        error: 'Duplicate tracking number',
        message: `Order with tracking number ${orderData.tracking_number} already exists`,
        existing_order_id: existingOrder.id,
      });
    }

    // Find existing entities (do not create anything)
    const entityIds = await findExistingOrderEntities(knex, orderData);

    // Register tracking number with tracking service via carrier processor
    console.log(`🔍 Registering tracking number: ${orderData.tracking_number}`);
    
    // Prepare carrier processor payload - FIXED: Use undefined instead of null
    const carrierPayload: any = {
      trackingId: orderData.tracking_number,
      action: 'REGISTER_TRACKING',
    };

    // Only add carrierCode if it's a valid value
    if (entityIds.carrierCode) {
      carrierPayload.carrierCode = entityIds.carrierCode;
    }

    const registerResponse = await invokeCarrierProcessor(carrierPayload);

    if (!registerResponse.success) {
      console.error('❌ Tracking number registration failed:', registerResponse.error);
      return createResponse(400, {
        error: 'Tracking number registration failed',
        message: 'The tracking number could not be registered with the tracking service',
        details: registerResponse,
      });
    }
  const carrierResult = await knex('carriers')
  .where('carrier_17track_id', '=', registerResponse.carrierInfo?.code)
  .select('id')
  .first(); 
if (!carrierResult) {
  console.error('❌ Carrier not found for code:', registerResponse.carrierInfo?.code);
  return createResponse(400, {
    error: 'Carrier not found',
    message: 'The carrier could not be found in the database',
    carrierCode: registerResponse.carrierInfo?.code,
  });
}

const carrierId = carrierResult.id;
    // Prepare order data for insertion - ONLY INSERT INTO ORDERS TABLE
    const now = new Date();
    const orderInsertData = {
      manufacturer_id: entityIds.manufacturerId,
      manufacturer_order_id: orderData.manufacturer_order_id ,
      site_id: entityIds.siteId,
      carrier_id: carrierId,
      status: orderData.status || 'IN_TRANSIT',
      sub_status: null,
      exception_details: null,
      completion_type: null,
      n_steps: 0,
      tracking_link: orderData.tracking_link || null,
      tracking_number: orderData.tracking_number,
      manufacturer_creation_timestamp: orderData.manufacturer_creation_timestamp ? new Date(orderData.manufacturer_creation_timestamp) : now,
      manufacturer_estimated_delivery_timestamp: orderData.manufacturer_estimated_delivery_timestamp ? new Date(orderData.manufacturer_estimated_delivery_timestamp) : null,
      manufacturer_confirmed_delivery_timestamp: orderData.manufacturer_confirmed_delivery_timestamp ? new Date(orderData.manufacturer_confirmed_delivery_timestamp) : null,
      carrier_creation_timestamp: orderData.carrier_creation_timestamp ? new Date(orderData.carrier_creation_timestamp) : null,
      carrier_estimated_delivery_timestamp: orderData.carrier_estimated_delivery_timestamp ? new Date(orderData.carrier_estimated_delivery_timestamp) : null,
      carrier_confirmed_delivery_timestamp: orderData.carrier_confirmed_delivery_timestamp ? new Date(orderData.carrier_confirmed_delivery_timestamp) : null,
      SLS: false,
      created_at: now,
      updated_at: now,
    };

    // Insert ONLY into orders table
    console.log('💾 Inserting order into database');
    const [insertedOrder] = await knex('orders')
      .insert(orderInsertData)
      .returning('*');

    console.log(`✅ Order inserted successfully with ID: ${insertedOrder.id}`);

    // // Send notification
    // await sqsClient.send(new SendMessageCommand({
    //   QueueUrl: TRACKING_UPDATES_SQS_URL,
    //   MessageBody: JSON.stringify({
    //     eventType: 'ORDER_CREATED',
    //     orderId: insertedOrder.id,
    //     trackingNumber: orderData.tracking_number,
    //     carrierInfo: registerResponse.carrierInfo,
    //     timestamp: new Date().toISOString(),
    //   }),
    //   MessageAttributes: {
    //     eventType: {
    //       DataType: 'String',
    //       StringValue: 'ORDER_CREATED',
    //     },
    //     orderId: {
    //       DataType: 'Number',
    //       StringValue: insertedOrder.id.toString(),
    //     },
    //   },
    // }));

    // console.log(`📨 Sent order creation notification for order ${insertedOrder.id}`);

    // Return success response
    return createResponse(201, {
      success: true,
      message: 'Order created successfully',
      data: {
        order_id: insertedOrder.id,
        tracking_number: orderData.tracking_number,
        tracking_link: insertedOrder.tracking_link,
        status: insertedOrder.status,
        carrier_info: registerResponse.carrierInfo,
        created_at: insertedOrder.created_at,
      },
    });

  } catch (error) {
    console.error('❌ Error processing order:', error);

    // Handle specific error types
    if (error instanceof z.ZodError) {
      return createResponse(400, {
        error: 'Validation failed',
        message: 'The request data is invalid',
        details: error.errors.map(err => ({
          field: err.path.join('.'),
          message: err.message,
        })),
      });
    }

    if (error instanceof SyntaxError) {
      return createResponse(400, {
        error: 'Invalid JSON',
        message: 'The request body contains invalid JSON',
      });
    }

    // Database constraint errors
    if (error instanceof Error && error.message.includes('foreign key')) {
      return createResponse(400, {
        error: 'Invalid reference',
        message: 'One or more referenced entities do not exist',
      });
    }

    // Entity not found errors
    if (error instanceof Error && error.message.includes('not found')) {
      return createResponse(404, {
        error: 'Entity not found',
        message: error.message,
      });
    }

    // Generic error response
    return createResponse(500, {
      error: 'Internal Server Error',
      message: 'An unexpected error occurred while processing the order',
      ...(process.env.NODE_ENV === 'development' && {
        details: error instanceof Error ? error.message : 'Unknown error',
      }),
    });

  } finally {
    // Always close database connection
    if (dbUtil) {
      await dbUtil.closeConnection();
      console.log('🔐 Database connection closed');
    }
  }
};

// ============================================================================
// DATABASE OPERATIONS - FIND ONLY, NO CREATION
// ============================================================================

/**
 * Find existing entities - do NOT create anything
 * FIXED: Better error handling and ensure we find a site
 */
async function findExistingOrderEntities(knex: any, orderData: CreateOrderInput): Promise<{
  siteId: number;
  carrierId: number;
  carrierCode: string | null;
  manufacturerId: number;
}> {
  
  let manufacturerId: number;
  
  // 1. Get manufacturer (default to first one if not specified)
  if (!orderData.manufacturer_id) {
    const manufacturer = await knex('manufacturers')
      .select('id')
      .first();
    
    if (!manufacturer) {
      throw new Error('No manufacturers found in the system');
    }
    manufacturerId = manufacturer.id;
  } else {
    // Verify the specified manufacturer exists
    const manufacturer = await knex('manufacturers')
      .where('id', orderData.manufacturer_id)
      .first();
    
    if (!manufacturer) {
      throw new Error(`Manufacturer with ID ${orderData.manufacturer_id} not found`);
    }
    manufacturerId = orderData.manufacturer_id;
  }

  // 2. Find existing supplier
  const supplier = await knex('suppliers')
    .whereRaw('LOWER(name) = ?', [orderData.supplier_name.toLowerCase()])
    .first();

  if (!supplier) {
    throw new Error(`Supplier '${orderData.supplier_name}' not found. Please ensure the supplier exists in the system.`);
  }

  // 3. Find existing site for this supplier
  const site = await knex('sites')
    .where('supplier_id', supplier.id)
    .orderBy('n_orders', 'desc')
    .first();

  if (!site) {
    throw new Error(`No site found for supplier '${orderData.supplier_name}'. Please ensure the supplier has at least one site configured.`);
  }

  // 4. Find existing carrier (optional)
  let carrierId = 0;
  let carrierCode: string | null = null;
  
  if (orderData.carrier_name) {
    const carrier = await knex('carriers')
      .whereRaw('LOWER(name) = ?', [orderData.carrier_name.toLowerCase()])
      .first();
    
    if (carrier) {
      carrierId = carrier.id;
      carrierCode = carrier.carrier_17track_id || null;
    } else {
      console.warn(`⚠️ Carrier '${orderData.carrier_name}' not found, will use auto-detection`);
    }
  }

  console.log(`✅ Found entities - Supplier: ${supplier.name}, Site: ${site.id}, Manufacturer: ${manufacturerId}, Carrier: ${carrierId || 'auto-detect'}`);

  return {
    siteId: site.id,
    carrierId,
    carrierCode,
    manufacturerId,
  };
}

// ============================================================================
// INTEGRATION FUNCTIONS
// ============================================================================

/**
 * Invoke carrier processor Lambda function
 */
async function invokeCarrierProcessor(payload: any): Promise<any> {
  try {
    console.log('🔗 Invoking carrier processor with payload:', JSON.stringify(payload, null, 2));
    
    const command = new InvokeCommand({
      FunctionName: CARRIER_LAMBDA_ARN,
      InvocationType: 'RequestResponse',
      Payload: JSON.stringify(payload),
    });

    const response = await lambdaClient.send(command);
    
    if (response.StatusCode !== 200) {
      throw new Error(`Lambda invocation failed with status ${response.StatusCode}`);
    }

    const responseData = JSON.parse(new TextDecoder().decode(response.Payload));
    console.log('📨 Carrier processor response:', JSON.stringify(responseData, null, 2));
    
    return responseData;

  } catch (error) {
    console.error('Error invoking carrier processor:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Create API response helper
 */
function createResponse(statusCode: number, body: any): APIGatewayProxyResult {
  return {
    statusCode,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
      'Access-Control-Allow-Methods': 'POST',
    },
    body: JSON.stringify(body),
  };
}

export default injestorHandler;