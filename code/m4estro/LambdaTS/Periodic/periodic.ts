// src/functions/tracking_updater.ts
import { ScheduledEvent, Context } from 'aws-lambda';
import { LambdaClient, InvokeCommand } from '@aws-sdk/client-lambda';
import { SQSClient, SendMessageCommand } from '@aws-sdk/client-sqs';
import { z } from 'zod';
import { DatabaseUtil } from '../utils/DatabaseUtils';
import { time } from 'console';

// ============================================================================
// 17TRACK STATUS REFERENCE
// ============================================================================
/*
17Track Main Status → Sub-Status → Our Internal Status Mapping:

NotFound:
  - NotFound_Other → NOT_FOUND
  - NotFound_InvalidCode → NOT_FOUND

InfoReceived:
  - InfoReceived → PENDING

InTransit:
  - InTransit_PickedUp → PICKED_UP
  - InTransit_Other → IN_TRANSIT
  - InTransit_Departure → DEPARTED
  - InTransit_Arrival → ARRIVED
  - InTransit_CustomsProcessing → CUSTOMS_PROCESSING
  - InTransit_CustomsReleased → CUSTOMS_CLEARED
  - InTransit_CustomsRequiringInformation → CUSTOMS_HOLD

Expired:
  - Expired_Other → EXPIRED (COMPLETION)

AvailableForPickup:
  - AvailableForPickup_Other → AVAILABLE_FOR_PICKUP

OutForDelivery:
  - OutForDelivery_Other → OUT_FOR_DELIVERY

DeliveryFailure:
  - DeliveryFailure_Other → DELIVERY_FAILED
  - DeliveryFailure_NoBody → DELIVERY_FAILED_NO_RECIPIENT
  - DeliveryFailure_Security → DELIVERY_FAILED_SECURITY
  - DeliveryFailure_Rejected → DELIVERY_REFUSED (SLS)
  - DeliveryFailure_InvalidAddress → DELIVERY_FAILED_ADDRESS

Delivered:
  - Delivered_Other → DELIVERED (COMPLETION)

Exception:
  - Exception_Other → EXCEPTION
  - Exception_Returning → RETURNING
  - Exception_Returned → RETURNED (COMPLETION)
  - Exception_NoBody → EXCEPTION_NO_RECIPIENT
  - Exception_Security → EXCEPTION_SECURITY
  - Exception_Damage → EXCEPTION_DAMAGED (SLS)
  - Exception_Rejected → EXCEPTION_REFUSED (SLS)
  - Exception_Delayed → DELAYED
  - Exception_Lost → EXCEPTION_LOST (SLS)
  - Exception_Destroyed → EXCEPTION_DESTROYED (SLS)
  - Exception_Cancel → EXCEPTION_CANCELLED (SLS)

SLS (Shipment Loss Status) Triggers:
  - Exception_Lost
  - Exception_Destroyed
  - Exception_Cancel
  - Exception_Damage
  - Exception_Rejected
  - DeliveryFailure_Rejected

Completion Types:
  - DELIVERED: Successful delivery
  - EXCEPTION: SLS scenarios
  - RETURNED: Return to sender
  - EXPIRED: Tracking expired
*/

// ============================================================================
// ENVIRONMENT VARIABLES & CONFIGURATION
// ============================================================================

const CARRIER_LAMBDA_ARN = process.env.CARRIER_LAMBDA_ARN!;
const TRACKING_UPDATES_SQS_URL = process.env.TRACKING_UPDATES_SQS_URL!;
const ORDER_STATUS_UPDATES_SQS_URL = process.env.ORDER_STATUS_UPDATES_SQS_URL!;
const AWS_REGION = process.env.AWS_REGION || 'us-east-1';
const BATCH_SIZE = parseInt(process.env.BATCH_SIZE || '50');

// Initialize AWS clients
const lambdaClient = new LambdaClient({ region: AWS_REGION });
const sqsClient = new SQSClient({ region: AWS_REGION });

// ============================================================================
// SCHEMAS AND TYPES
// ============================================================================

const TrackingProcessorResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  action: z.string(),
  trackingId: z.string(),
  trackingData: z.any().optional(),
  carrierInfo: z.object({
    code: z.number().optional(),
    name: z.string().optional(),
    detected: z.boolean().optional(),
  }).optional(),
  events: z.array(z.object({
    timestamp: z.string(),
    status: z.string(),
    subStatus: z.string().optional(),
    location: z.string(),
    description: z.string(),
    stage: z.string().optional(),
    coordinates: z.object({
      latitude: z.number().optional(),
      longitude: z.number().optional(),
    }).optional(),
  })).optional(),
  orderStatus: z.object({
    current: z.string().optional(),
    subStatus: z.string().optional(),
    isDelivered: z.boolean().optional(),
    estimatedDelivery: z.string().optional(),
    confirmedDelivery: z.string().optional(),
  }).optional(),
  error: z.string().optional(),
});

interface UpdaterResult {
  totalOrders: number;
  processedOrders: number;
  ordersWithUpdates: number;
  newStepsCreated: number;
  completedOrders: number;
  deliveredOrders: number;
  slsOrders: number;
  failedOrders: number;
  errors: string[];
}

interface OrderStepData {
  order_id: number;
  step: number;
  status: string;
  status_description: string;
  sub_status: string | null;
  latitude: number;
  longitude: number;
  timestamp: Date;
  location: string;
  created_at: Date;
  updated_at: Date;
}

interface ProcessingResult {
  hasNewEvents: boolean;
  newStepsCount: number;
  orderStatusChanged: boolean;
  newStatus: string;
  newSubStatus: string | null;
  slsUpdated: boolean;
  slsReason?: string;
  completionType?: 'DELIVERED' | 'EXCEPTION' | 'RETURNED' | 'EXPIRED' | null;
  exceptionDetails?: string;
  eventTimestamp?: string;
  newSteps?: Array<{
    stepId: number;
    location: string;
    eventTimestamp: string;
  }>;
}

// ============================================================================
// 17TRACK SPECIFIC STATUS HANDLING
// ============================================================================

/**
 * 17Track specific SLS detection based on actual API responses
 */
function isShipmentLossException(status: string, subStatus?: string): boolean {
  // Main status that always indicates completion/SLS
  if (status === 'Exception' && subStatus) {
    const slsSubStatuses = [
      'Exception_Lost',
      'Exception_Destroyed', 
      'Exception_Cancel',
      'Exception_Damage',
      'Exception_Rejected'
    ];
    return slsSubStatuses.includes(subStatus);
  }

  // DeliveryFailure can also be SLS in some cases
  if (status === 'DeliveryFailure' && subStatus === 'DeliveryFailure_Rejected') {
    return true;
  }

  return false;
}

/**
 * 17Track specific completion detection
 */
function getCompletionType(status: string, subStatus?: string): 'DELIVERED' | 'EXCEPTION' | 'RETURNED' | 'EXPIRED' | null {
  // Successful delivery
  if (status === 'Delivered') {
    return 'DELIVERED';
  }
  
  // Expired tracking
  if (status === 'Expired') {
    return 'EXPIRED';
  }
  
  // Return scenarios
  if (status === 'Exception') {
    if (subStatus === 'Exception_Returning' || subStatus === 'Exception_Returned') {
      return 'RETURNED';
    }
    
    // SLS Exception scenarios
    if (isShipmentLossException(status, subStatus)) {
      return 'EXCEPTION';
    }
  }
  
  // Delivery failure that results in SLS
  if (status === 'DeliveryFailure' && subStatus === 'DeliveryFailure_Rejected') {
    return 'EXCEPTION';
  }
  
  return null;
}

/**
 * 17Track specific SLS reason mapping
 */
function getSLSReason(status: string, subStatus?: string): string {
  if (subStatus) {
    const reasonMap: Record<string, string> = {
      'Exception_Lost': 'SHIPMENT_LOST',
      'Exception_Destroyed': 'SHIPMENT_DESTROYED',
      'Exception_Cancel': 'ORDER_CANCELLED',
      'Exception_Damage': 'SHIPMENT_DAMAGED',
      'Exception_Rejected': 'DELIVERY_REFUSED',
      'DeliveryFailure_Rejected': 'DELIVERY_REFUSED',
    };

    return reasonMap[subStatus] || 'SHIPMENT_EXCEPTION';
  }

  return 'SHIPMENT_EXCEPTION';
}

/**
 * 17Track specific status mapping
 */
function mapTrackingStage(stage: string, subStatus?: string): string {
  // Handle completion cases first
  const completionType = getCompletionType(stage, subStatus);
  if (completionType) {
    switch (completionType) {
      case 'DELIVERED': return 'DELIVERED';
      case 'RETURNED': return 'RETURNED';
      case 'EXCEPTION': return 'EXCEPTION';
      case 'EXPIRED': return 'EXPIRED';
    }
  }

  // 17Track main status mappings
  const stageMap: Record<string, string> = {
    // 17Track specific statuses
    'NotFound': 'NOT_FOUND',
    'InfoReceived': 'PENDING',
    'InTransit': 'IN_TRANSIT',
    'AvailableForPickup': 'AVAILABLE_FOR_PICKUP',
    'OutForDelivery': 'OUT_FOR_DELIVERY',
    'DeliveryFailure': 'DELIVERY_FAILED',
    'Delivered': 'DELIVERED',
    'Exception': 'EXCEPTION',
    'Expired': 'EXPIRED',
  };

  // Sub-status specific mappings for InTransit
  if (stage === 'InTransit' && subStatus) {
    const inTransitMap: Record<string, string> = {
      'InTransit_PickedUp': 'PICKED_UP',
      'InTransit_Other': 'IN_TRANSIT',
      'InTransit_Departure': 'DEPARTED',
      'InTransit_Arrival': 'ARRIVED',
      'InTransit_CustomsProcessing': 'CUSTOMS_PROCESSING',
      'InTransit_CustomsReleased': 'CUSTOMS_CLEARED',
      'InTransit_CustomsRequiringInformation': 'CUSTOMS_HOLD',
    };
    
    return inTransitMap[subStatus] || 'IN_TRANSIT';
  }

  // Sub-status specific mappings for DeliveryFailure
  if (stage === 'DeliveryFailure' && subStatus) {
    const deliveryFailureMap: Record<string, string> = {
      'DeliveryFailure_NoBody': 'DELIVERY_FAILED_NO_RECIPIENT',
      'DeliveryFailure_Security': 'DELIVERY_FAILED_SECURITY',
      'DeliveryFailure_Rejected': 'DELIVERY_REFUSED',
      'DeliveryFailure_InvalidAddress': 'DELIVERY_FAILED_ADDRESS',
      'DeliveryFailure_Other': 'DELIVERY_FAILED',
    };
    
    return deliveryFailureMap[subStatus] || 'DELIVERY_FAILED';
  }

  // Sub-status specific mappings for Exception
  if (stage === 'Exception' && subStatus) {
    const exceptionMap: Record<string, string> = {
      'Exception_Returning': 'RETURNING',
      'Exception_Returned': 'RETURNED',
      'Exception_NoBody': 'EXCEPTION_NO_RECIPIENT',
      'Exception_Security': 'EXCEPTION_SECURITY',
      'Exception_Damage': 'EXCEPTION_DAMAGED',
      'Exception_Rejected': 'EXCEPTION_REFUSED',
      'Exception_Delayed': 'DELAYED',
      'Exception_Lost': 'EXCEPTION_LOST',
      'Exception_Destroyed': 'EXCEPTION_DESTROYED',
      'Exception_Cancel': 'EXCEPTION_CANCELLED',
      'Exception_Other': 'EXCEPTION',
    };
    
    return exceptionMap[subStatus] || 'EXCEPTION';
  }

  return stageMap[stage] || stage || 'UNKNOWN';
}

// ============================================================================
// MAIN HANDLER
// ============================================================================

export const periodicHandler = async (
  event: ScheduledEvent,
  context: Context
): Promise<UpdaterResult> => {
  let dbUtil: DatabaseUtil | null = null;
  
  const result: UpdaterResult = {
    totalOrders: 0,
    processedOrders: 0,
    ordersWithUpdates: 0,
    newStepsCreated: 0,
    completedOrders: 0,
    deliveredOrders: 0,
    slsOrders: 0,
    failedOrders: 0,
    errors: [],
  };

  try {
    console.log('🔄 Starting periodic tracking update job');
    console.log('⏰ Triggered at:', new Date().toISOString());

    // Initialize database connection
    dbUtil = DatabaseUtil.fromEnvironment();
    const knex = await dbUtil.getKnex();

    // Get orders that need tracking updates
    const ordersToUpdate = await getOrdersNeedingUpdate(knex);
    result.totalOrders = ordersToUpdate.length;

    console.log(`📦 Found ${ordersToUpdate.length} orders to update`);

    if (ordersToUpdate.length === 0) {
      console.log('✅ No orders need updating');
      return result;
    }

    // Process orders in batches
    for (let i = 0; i < ordersToUpdate.length; i += BATCH_SIZE) {
      const batch = ordersToUpdate.slice(i, i + BATCH_SIZE);
      console.log(`🔄 Processing batch ${Math.floor(i / BATCH_SIZE) + 1} (${batch.length} orders)`);

      await processBatch(batch, result, knex);
      
      // Small delay between batches
      if (i + BATCH_SIZE < ordersToUpdate.length) {
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }

    console.log('✅ Tracking update job completed successfully');
    console.log(`📊 Results: ${result.processedOrders}/${result.totalOrders} processed, ${result.newStepsCreated} new steps, ${result.deliveredOrders} delivered, ${result.slsOrders} SLS`);

    return result;

  } catch (error) {
    console.error('❌ Error in tracking updater:', error);
    result.errors.push(error instanceof Error ? error.message : 'Unknown error');
    throw error;

  } finally {
    if (dbUtil) {
      await dbUtil.closeConnection();
    }
  }
};

// ============================================================================
// ORDER PROCESSING
// ============================================================================

/**
 * Get orders that need tracking updates (exclude completed orders)
 * FIXED: Updated to match new schema with carrier_id and proper joins
 */
async function getOrdersNeedingUpdate(knex: any): Promise<any[]> {
  const activeStatuses = [
    // 17Track active statuses that need continued monitoring
    'NOT_FOUND',
    'PENDING',
    'PICKED_UP', 
    'IN_TRANSIT',
    'DEPARTED',
    'ARRIVED',
    'CUSTOMS_PROCESSING',
    'CUSTOMS_CLEARED',
    'CUSTOMS_HOLD',
    'AVAILABLE_FOR_PICKUP',
    'OUT_FOR_DELIVERY',
    'DELIVERY_FAILED',
    'DELIVERY_FAILED_NO_RECIPIENT',
    'DELIVERY_FAILED_SECURITY',
    'DELIVERY_FAILED_ADDRESS',
    'DELAYED',
    'RETURNING',
  ];

  const orders = await knex('orders')
    .leftJoin('carriers', 'orders.carrier_id', 'carriers.id')
    .select([
      'orders.id', 
      'orders.status', 
      'orders.tracking_number', 
      'orders.tracking_link', 
      'orders.updated_at', 
      'orders.SLS',
      'carriers.name as carrier_name',
      'carriers.carrier_17track_id'
    ])
    .whereIn('orders.status', activeStatuses)
    .whereNotNull('orders.tracking_number')
    .where('orders.tracking_number', '!=', '')
    .where('orders.updated_at', '<', knex.raw("NOW() - INTERVAL '3 hours'"))
    .where('orders.SLS', false) // Only process non-SLS orders
    .orderBy('orders.updated_at', 'asc')
    .limit(500);

  return orders.map(order => ({
    ...order,
    trackingId: order.tracking_number, // Use tracking_number as trackingId
    carrierCode: order.carrier_17track_id, // Use 17track ID for API calls
  })).filter(order => order.trackingId);
}

/**
 * Process a batch of orders
 */
async function processBatch(orders: any[], result: UpdaterResult, knex: any): Promise<void> {
  const promises = orders.map(order => processOrder(order, result, knex));
  await Promise.allSettled(promises);
}

/**
 * Enhanced order processing with completion and SLS handling
 * FIXED: Updated to use correct carrier code
 */
async function processOrder(order: any, result: UpdaterResult, knex: any): Promise<void> {
  try {
    console.log(`🔍 Processing order ${order.id} (${order.trackingId})`);

    // Get current order state
    const currentOrder = await knex('orders')
      .where('id', order.id)
      .select('status', 'SLS')
      .first();

    if (!currentOrder) {
      throw new Error(`Order ${order.id} not found`);
    }

    const previousStatus = currentOrder.status;
    const previousSLS = currentOrder.SLS;

    // Invoke tracking processor with correct carrier code
    const processorResponse = await invokeTrackingProcessor({
      trackingId: order.trackingId,
      carrierCode: order.carrierCode, // Now using carrier_17track_id
      action: 'GET_TRACKING_INFO',
    });

    result.processedOrders++;

    if (!processorResponse.success) {
      console.error(`❌ Failed to get tracking info for order ${order.id}:`, processorResponse.error);
      result.failedOrders++;
      result.errors.push(`Order ${order.id}: ${processorResponse.error}`);
      return;
    }

    // Process tracking data with enhanced completion handling
    const updateResults = await processTrackingDataForOrder(
      knex, 
      order.id, 
      processorResponse,
      previousStatus,
      previousSLS
    );

    // Update result counters
    if (updateResults.hasNewEvents) {
      result.ordersWithUpdates++;
      result.newStepsCreated += updateResults.newStepsCount;
    }

    // Track completion types
    if (updateResults.completionType === 'DELIVERED') {
      result.deliveredOrders++;
      result.completedOrders++;
      console.log(`✅ Order ${order.id} delivered`);
    } else if (updateResults.completionType === 'EXCEPTION') {
      result.slsOrders++;
      result.completedOrders++;
      console.log(`🚨 Order ${order.id} completed with exception: ${updateResults.slsReason}`);
    } else if (updateResults.completionType === 'RETURNED') {
      result.completedOrders++;
      console.log(`📦 Order ${order.id} returned to sender`);
    } else if (updateResults.completionType === 'EXPIRED') {
      result.completedOrders++;
      console.log(`⏰ Order ${order.id} tracking expired`);
    }

    // // Send notifications
    // if (updateResults.orderStatusChanged || updateResults.completionType) {
    //   await sendOrderStatusUpdateNotification(order, updateResults);
    // }

    if (updateResults.hasNewEvents) {
      await sendTrackingUpdateNotification(order, updateResults);
    }

  } catch (error) {
    console.error(`❌ Error processing order ${order.id}:`, error);
    result.failedOrders++;
    result.errors.push(`Order ${order.id}: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

// ============================================================================
// ENHANCED DATABASE OPERATIONS
// ============================================================================

/**
 * Enhanced tracking data processing with completion and SLS handling
 * FIXED: Updated to match new schema fields
 */
async function processTrackingDataForOrder(
  knex: any, 
  orderId: number, 
  processorResponse: any,
  previousStatus: string,
  previousSLS: boolean
): Promise<ProcessingResult> {
  
  let hasNewEvents = false;
  let newStepsCount = 0;
  let orderStatusChanged = false;
  let newStatus = previousStatus;
  let newSubStatus: string | null = null;
  let slsUpdated = false;
  let slsReason: string | undefined;
  let completionType: 'DELIVERED' | 'EXCEPTION' | 'RETURNED' | 'EXPIRED' | null = null;
  let exceptionDetails: string | undefined;
  let newSteps: Array<{ stepId: number; location: string; eventTimestamp: string }> = [];

  try {
    // Analyze latest status for completion and SLS
    let shouldSetSLS = previousSLS;
    
    if (processorResponse.orderStatus?.current) {
      const latestStatus = processorResponse.orderStatus.current;
      const latestSubStatus = processorResponse.orderStatus.subStatus;
      
      // Map status with sub-status consideration
      newStatus = mapTrackingStage(latestStatus, latestSubStatus);
      newSubStatus = latestSubStatus || null;
      orderStatusChanged = previousStatus !== newStatus;
      
      // Determine completion type
      completionType = getCompletionType(latestStatus, latestSubStatus);
      
      // Check for SLS conditions
      if (isShipmentLossException(latestStatus, latestSubStatus)) {
        shouldSetSLS = true;
        slsReason = getSLSReason(latestStatus, latestSubStatus);
        slsUpdated = !previousSLS;
        exceptionDetails = `Status: ${latestStatus}, Sub-Status: ${latestSubStatus || 'N/A'}`;
        console.log(`🚨 SLS condition detected for order ${orderId}: ${exceptionDetails}`);
      }
    }

    // Check events for SLS conditions and completion
    if (processorResponse.events && Array.isArray(processorResponse.events)) {
      for (const event of processorResponse.events) {
        if (isShipmentLossException(event.status, event.subStatus)) {
          shouldSetSLS = true;
          slsReason = getSLSReason(event.status, event.subStatus);
          slsUpdated = !previousSLS;
          exceptionDetails = `Event Status: ${event.status}, Sub-Status: ${event.subStatus || 'N/A'}, Location: ${event.location}`;
          console.log(`🚨 SLS condition found in events for order ${orderId}: ${exceptionDetails}`);
          
          // If we found SLS in events but not in latest status, update completion type
          if (!completionType) {
            completionType = 'EXCEPTION';
            const carrierId = (await knex('orders').where('id', orderId).select('carrier_id')).pop()?.carrier_id;
            await knex('carriers').where('id', carrierId).update({
              n_losses: knex.raw('n_losses + 1'),
              updated_at: new Date(),
            });
          }
          break;
        }
      }
    }

    // Prepare comprehensive order update with new schema fields
    const updateData: any = {
      status: newStatus,
      SLS: shouldSetSLS,
      updated_at: new Date(),
    };

    // Add sub-status to order
    if (newSubStatus) {
      updateData.sub_status = newSubStatus;
    }

    // Set completion type
    if (completionType) {
      updateData.completion_type = completionType;
    }

    // Handle completion timestamps
    if (completionType === 'DELIVERED') {
      if (processorResponse.orderStatus?.confirmedDelivery) {
        updateData.carrier_confirmed_delivery_timestamp = new Date(processorResponse.orderStatus.confirmedDelivery);
      } else {
        updateData.carrier_confirmed_delivery_timestamp = new Date(); // Use current time as fallback
      }
    }

    // Set estimated delivery if available
    if (processorResponse.orderStatus?.estimatedDelivery) {
      updateData.carrier_estimated_delivery_timestamp = new Date(processorResponse.orderStatus.estimatedDelivery);
    }

    // Add exception details for SLS cases
    if (shouldSetSLS && exceptionDetails) {
      updateData.exception_details = exceptionDetails;
    }

    // Update order
    await knex('orders')
      .where('id', orderId)
      .update(updateData);

    if (orderStatusChanged) {
      console.log(`🔄 Updated order ${orderId} status: ${previousStatus} → ${newStatus}`);
    }

    if (slsUpdated) {
      console.log(`🚨 Updated order ${orderId} SLS: false → true (Reason: ${slsReason})`);
    }

    if (completionType) {
      console.log(`🏁 Order ${orderId} completed as: ${completionType}`);
    }

    // Process tracking events
    if (processorResponse.events && Array.isArray(processorResponse.events)) {
      const incomingEvents = processorResponse.events;
      
      const existingSteps = await knex('order_steps')
        .where('order_id', orderId)
        .select('*')
        .orderBy('timestamp', 'asc');

      const newEvents = await findNewTrackingEvents(existingSteps, incomingEvents);
      
      if (newEvents.length > 0) {
        console.log(`🆕 Found ${newEvents.length} new tracking events for order ${orderId}`);
        
        const stepsToCreate = await calculateStepNumbers(knex, orderId, existingSteps, newEvents);
        
        for (const stepData of stepsToCreate) {
          const createdStep = await createOrderStepWithData(knex, stepData);
          if (createdStep) {
            newSteps.push({
              stepId: createdStep.id,
              location: createdStep.location,
              eventTimestamp: createdStep.eventTimestamp,
            });
          }
          newStepsCount++;
        }

        hasNewEvents = true;
        
        // Update order with new step count
        await knex('orders')
          .where('id', orderId)
          .update({ 
            n_steps: existingSteps.length + newStepsCount,
            updated_at: new Date()
          });

        console.log(`✅ Added ${newStepsCount} new tracking events for order ${orderId}`);
      }
    }

  } catch (error) {
    console.error(`❌ Error processing tracking data for order ${orderId}:`, error);
  }

  return { 
    hasNewEvents, 
    newStepsCount, 
    orderStatusChanged, 
    newStatus,
    newSubStatus,
    slsUpdated,
    slsReason,
    completionType,
    exceptionDetails,
    newSteps,
    eventTimestamp: processorResponse.orderStatus.timeUTC 
  };  
}

/**
 * Enhanced step creation with sub-status support
 */
async function createOrderStepWithData(knex: any, stepData: OrderStepData): Promise<any> {
  try {
    const [createdStep] = await knex('order_steps').insert(stepData).returning('*');
    
    const subStatusInfo = stepData.sub_status ? ` [Sub: ${stepData.sub_status}]` : '';
    console.log(`📍 Created order step ${stepData.step}: ${stepData.status}${subStatusInfo} at ${stepData.location}`);
    
    return createdStep;

  } catch (error) {
    console.error(`❌ Error creating order step ${stepData.step}:`, error);
    return null;
  }
}

/**
 * Enhanced step calculation with sub-status preservation
 */
async function calculateStepNumbers(
  knex: any, 
  orderId: number, 
  existingSteps: any[], 
  newEvents: any[]
): Promise<OrderStepData[]> {
  
  // Combine and sort all events chronologically
  const allEvents = [
    ...existingSteps.map(step => ({
      timestamp: step.timestamp,
      location: step.location,
      status: step.status,
      subStatus: step.sub_status,
      description: step.status_description,
      coordinates: { latitude: step.latitude, longitude: step.longitude },
      isExisting: true,
      stepId: step.id
    })),
    ...newEvents.map(event => ({
      timestamp: event.timestamp,
      location: event.location,
      status: mapTrackingStage(event.stage || event.status, event.subStatus),
      subStatus: event.subStatus,
      description: event.description,
      coordinates: event.coordinates,
      stage: event.stage,
      isExisting: false
    }))
  ].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  // Create steps for new events only
  const stepsToCreate: OrderStepData[] = [];
  
  allEvents.forEach((event, index) => {
    if (!event.isExisting) {
      const stepNumber = index + 1;
      const now = new Date();
      
      // Enhanced description with SLS information
      let description = event.description || `${event.status} - ${event.location}`;
      
      if (event.subStatus) {
        description += ` [${event.subStatus}]`;
      }
      
      if (isShipmentLossException(event.status, event.subStatus)) {
        const slsReason = getSLSReason(event.status, event.subStatus);
        description += ` [SLS: ${slsReason}]`;
      }
      
      stepsToCreate.push({
        order_id: orderId,
        step: stepNumber,
        status: event.status,
        status_description: description,
        sub_status: event.subStatus || null,
        latitude: event.coordinates?.latitude || 0,
        longitude: event.coordinates?.longitude || 0,
        timestamp: new Date(event.timestamp),
        location: event.location || 'Unknown Location',
        created_at: now,
        updated_at: now,
      });
    }
  });

  return stepsToCreate;
}

async function findNewTrackingEvents(existingSteps: any[], incomingEvents: any[]): Promise<any[]> {
  const existingEventSet = new Set(
    existingSteps.map(step => 
      `${new Date(step.timestamp).getTime()}-${step.location}-${step.status}-${step.sub_status || ''}`
    )
  );

  const newEvents = incomingEvents.filter(event => {
    const mappedStatus = mapTrackingStage(event.stage || event.status, event.subStatus);
    const eventKey = `${new Date(event.timestamp).getTime()}-${event.location}-${mappedStatus}-${event.subStatus || ''}`;
    return !existingEventSet.has(eventKey);
  });

  return newEvents;
}

// ============================================================================
// INTEGRATION FUNCTIONS
// ============================================================================

async function invokeTrackingProcessor(payload: any): Promise<any> {
  try {
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
    return TrackingProcessorResponseSchema.parse(responseData);

  } catch (error) {
    console.error('Error invoking tracking processor:', error);
    throw error;
  }
}

/**
 * Enhanced SQS notifications with completion and SLS information
 */
async function sendTrackingUpdateNotification(order: any, updateResults: ProcessingResult): Promise<void> {
  try {
    const message = {
      eventType: 'ORDER_EVENT',
      data:{
        type:'CARRIER_UPDATE',
        orderId: order.id,
        trackingNumber: order.trackingId,
        eventTimestamps: updateResults.newSteps?.map(step => step.eventTimestamp) || [],
        orderNewStepsIds: updateResults.newSteps?.map(step => step.stepId) || [],
        orderNewLocations: updateResults.newSteps?.map(step => step.location) || [],
      },
      timestamp: new Date().toISOString(),
      
    };

    await sqsClient.send(new SendMessageCommand({
      QueueUrl: TRACKING_UPDATES_SQS_URL,
      MessageBody: JSON.stringify(message),
      MessageAttributes: {
        eventType: { DataType: 'String', StringValue: 'TRACKING_UPDATE' },
        orderId: { DataType: 'Number', StringValue: order.id.toString() },
        newStepsCount: { DataType: 'Number', StringValue: (updateResults.newStepsCount || 0).toString() },
      },
    }));

    console.log(`📨 Sent tracking update notification for order ${order.id}`);

  } catch (error) {
    console.error(`Error sending tracking update notification for order ${order.id}:`, error);
  }
}

// async function sendOrderStatusUpdateNotification(order: any, updateResults: ProcessingResult): Promise<void> {
//   try {
//     const message = {
//       eventType: 'ORDER_STATUS_UPDATE',
//       orderId: order.id,
//       trackingId: order.trackingId,
//       carrierName: order.carrier_name,
//       newStatus: updateResults.newStatus,
//       newSubStatus: updateResults.newSubStatus,
//       completionType: updateResults.completionType,
//       slsUpdated: updateResults.slsUpdated,
//       slsReason: updateResults.slsReason,
//       exceptionDetails: updateResults.exceptionDetails,
//       orderSteps: updateResults.newSteps?.map(step => ({
//         stepId: step.stepId,
//         location: step.location,
//       })) || [],
//       timestamp: new Date().toISOString(),
//     };

//     await sqsClient.send(new SendMessageCommand({
//       QueueUrl: ORDER_STATUS_UPDATES_SQS_URL,
//       MessageBody: JSON.stringify(message),
//       MessageAttributes: {
//         eventType: { DataType: 'String', StringValue: 'ORDER_STATUS_UPDATE' },
//         orderId: { DataType: 'Number', StringValue: order.id.toString() },
//         completionType: { DataType: 'String', StringValue: updateResults.completionType || 'ACTIVE' },
//         newStatus: { DataType: 'String', StringValue: updateResults.newStatus },
//         slsUpdated: { DataType: 'String', StringValue: updateResults.slsUpdated.toString() },
//       },
//     }));

//     console.log(`📨 Sent order status update notification for order ${order.id}: ${updateResults.newStatus}`);

//   } catch (error) {
//     console.error(`Error sending order status update notification for order ${order.id}:`, error);
//   }
// }

export default periodicHandler;