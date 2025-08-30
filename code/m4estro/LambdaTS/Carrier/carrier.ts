// import { Context } from 'aws-lambda';
// import { z } from 'zod';
// import { TrackingApi } from '../utils/trackingApi';

// // ============================================================================
// // SCHEMAS
// // ============================================================================

// const TrackingProcessorInputSchema = z.object({
//   trackingId: z.string().min(1),
//   carrierCode: z.union([z.string(), z.number()]).optional(),
//   action: z.enum(['REGISTER_TRACKING', 'GET_TRACKING_INFO', 'DELETE_TRACKING']),
// });

// type TrackingProcessorInput = z.infer<typeof TrackingProcessorInputSchema>;

// interface TrackingProcessorResponse {
//   success: boolean;
//   message: string;
//   action: string;
//   trackingId: string;
//   trackingData?: any;
//   carrierInfo?: {
//     code?: number;
//     name?: string;
//   };
//   events?: Array<{
//     timestamp: string;
//     status: string;
//     subStatus?: string; // NEW: Add sub-status support
//     location: string;
//     description: string;
//     coordinates?: { latitude?: number; longitude?: number };
//   }>;
//   orderStatus?: {
//     current?: string;
//     subStatus?: string; // NEW: Add sub-status support
//     isDelivered?: boolean;
//     estimatedDelivery?: string;
//     confirmedDelivery?: string;
//   };
//   error?: string;
// }

// // ============================================================================
// // MAIN HANDLER
// // ============================================================================

// export const carrierHandler = async (
//   event: TrackingProcessorInput,
//   context: Context
// ): Promise<TrackingProcessorResponse> => {

//   try {
//     console.log('🎯 Carrier processor invoked:', JSON.stringify(event, null, 2));
    
//     const validatedInput = TrackingProcessorInputSchema.parse(event);
    
//     const trackingApi = new TrackingApi({
//       timeout: 25000,
//       retries: 2,
//     });

//     switch (validatedInput.action) {
//       case 'REGISTER_TRACKING':
//         return await handleRegistration(validatedInput, trackingApi);
      
//       case 'GET_TRACKING_INFO':
//         return await handleTrackingInfo(validatedInput, trackingApi);
      
//       case 'DELETE_TRACKING':
//         return await handleDeleteTracking(validatedInput, trackingApi);
      
//       default:
//         throw new Error(`Unsupported action: ${validatedInput.action}`);
//     }

//   } catch (error) {
//     console.error('❌ Tracking processor error:', error);
    
//     if (error instanceof z.ZodError) {
//       return {
//         success: false,
//         message: 'Invalid input data',
//         action: event.action || 'unknown',
//         trackingId: event.trackingId || 'unknown',
//         error: 'Validation failed',
//       };
//     }

//     return {
//       success: false,
//       message: 'Tracking API processing failed',
//       action: event.action || 'unknown',
//       trackingId: event.trackingId || 'unknown',
//       error: error instanceof Error ? error.message : 'Unknown error',
//     };
//   }
// }

// async function handleDeleteTracking(
//   input: TrackingProcessorInput,
//   trackingApi: TrackingApi
// ): Promise<TrackingProcessorResponse> {

//   try {
//     console.log(`🗑️ Deleting tracking for: ${input.trackingId}`);
    
//     const deleteResponse = await trackingApi.deleteTrackingNumber({
//       number: input.trackingId,
//       auto_detection: true,
//       ...(input.carrierCode && { carrier: input.carrierCode }),
//     });

//     if (typeof deleteResponse.data === 'string') {
//       return {
//         success: false,
//         message: 'Delete tracking failed',
//         action: 'DELETE_TRACKING',
//         trackingId: input.trackingId,
//         error: deleteResponse.data,
//       };
//     }

//     if (deleteResponse.data.accepted.length > 0) {
//       return {
//         success: true,
//         message: 'Tracking number deleted successfully',
//         action: 'DELETE_TRACKING',
//         trackingId: input.trackingId,
//         trackingData: deleteResponse,
//       };
//     }

//     if (deleteResponse.data.rejected.length > 0) {
//       const rejection = deleteResponse.data.rejected[0];
//       return {
//         success: false,
//         message: 'Delete tracking rejected',
//         action: 'DELETE_TRACKING',
//         trackingId: input.trackingId,
//         error: rejection.error.message,
//       };
//     }

//     return {
//       success: false,
//       message: 'No tracking numbers processed for deletion',
//       action: 'DELETE_TRACKING',
//       trackingId: input.trackingId,
//       error: 'Empty response',
//     };

//   } catch (error) {
//     console.error(`❌ Delete tracking failed for ${input.trackingId}:`, error);
//     return {
//       success: false,
//       message: 'Delete tracking failed',
//       action: 'DELETE_TRACKING',
//       trackingId: input.trackingId,
//       error: error instanceof Error ? error.message : 'Unknown error',
//     };
//   }
// };

// // ============================================================================
// // ACTION HANDLERS
// // ============================================================================

// async function handleRegistration(
//   input: TrackingProcessorInput,
//   trackingApi: TrackingApi
// ): Promise<TrackingProcessorResponse> {

//   try {
//     console.log(`📝 Registering tracking number: ${input.trackingId}`);
    
//     // Enhanced request with carrier code handling
//     const requestPayload: any = {
//       number: input.trackingId,
//       auto_detection: true,
//     };

//     // Add carrier code if provided and valid
//     if (input.carrierCode) {
//       const carrierCode = parseCarrierCode(input.carrierCode);
//       if (carrierCode) {
//         requestPayload.carrier = carrierCode;
//         console.log(`🚛 Using carrier code: ${carrierCode} for registration`);
//       }
//     }

//     const registrationResponse = await trackingApi.registerTrackingNumber(requestPayload);

//     if (typeof registrationResponse.data === 'string') {
//       return {
//         success: false,
//         message: 'Registration failed',
//         action: 'REGISTER_TRACKING',
//         trackingId: input.trackingId,
//         error: registrationResponse.data,
//       };
//     }

//     if (registrationResponse.data.accepted.length > 0) {
//       const accepted = registrationResponse.data.accepted[0];
      
//       return {
//         success: true,
//         message: 'Tracking number registered successfully',
//         action: 'REGISTER_TRACKING',
//         trackingId: input.trackingId,
//         trackingData: registrationResponse,
//         carrierInfo: {
//           code: accepted.carrier,
//           name: accepted.carrier_name,
//         },
//       };
//     }

//     if (registrationResponse.data.rejected.length > 0) {
//       const rejection = registrationResponse.data.rejected[0];
//       return {
//         success: false,
//         message: 'Registration rejected',
//         action: 'REGISTER_TRACKING',
//         trackingId: input.trackingId,
//         error: rejection.error.message,
//       };
//     }

//     return {
//       success: false,
//       message: 'No tracking numbers processed',
//       action: 'REGISTER_TRACKING',
//       trackingId: input.trackingId,
//       error: 'Empty response',
//     };

//   } catch (error) {
//     console.error(`❌ Registration failed for ${input.trackingId}:`, error);
//     return {
//       success: false,
//       message: 'Registration failed',
//       action: 'REGISTER_TRACKING',
//       trackingId: input.trackingId,
//       error: error instanceof Error ? error.message : 'Unknown error',
//     };
//   }
// }

// async function handleTrackingInfo(
//   input: TrackingProcessorInput,
//   trackingApi: TrackingApi
// ): Promise<TrackingProcessorResponse> {

//   try {
//     console.log(`🔍 Retrieving tracking info for: ${input.trackingId}`);

//     // Enhanced request with carrier code handling
//     const requestPayload: any = {
//       number: input.trackingId,
//       auto_detection: true,
//     };

//     // Add carrier code if provided and valid
//     if (input.carrierCode) {
//       const carrierCode = parseCarrierCode(input.carrierCode);
//       if (carrierCode) {
//         requestPayload.carrier = carrierCode;
//         console.log(`🚛 Using carrier code: ${carrierCode} for tracking info`);
//       }
//     }

//     const trackingInfo = await trackingApi.getTrackingInfo(requestPayload);

//     if (typeof trackingInfo.data === 'string') {
//       return {
//         success: false,
//         message: 'Tracking info failed',
//         action: 'GET_TRACKING_INFO',
//         trackingId: input.trackingId,
//         error: trackingInfo.data,
//       };
//     }

//     if (!trackingInfo.data?.accepted?.length) {
//       return {
//         success: false,
//         message: 'No tracking information found',
//         action: 'GET_TRACKING_INFO',
//         trackingId: input.trackingId,
//         error: 'No data available',
//       };
//     }

//     if (trackingInfo.data.rejected?.length > 0) {
//       const rejection = trackingInfo.data.rejected[0];
//       return {
//         success: false,
//         message: 'Tracking info rejected',
//         action: 'GET_TRACKING_INFO',
//         trackingId: input.trackingId,
//         error: rejection.error.message,
//       };
//     }

//     const trackingData = trackingInfo.data.accepted[0];
//     const events = await extractTrackingEvents(trackingData);
//     const orderStatus = extractOrderStatus(trackingData);

//     console.log(`✅ Retrieved ${events.length} events for ${input.trackingId}`);

//     return {
//       success: true,
//       message: 'Tracking information retrieved',
//       action: 'GET_TRACKING_INFO',
//       trackingId: input.trackingId,
//       trackingData: trackingInfo,
//       carrierInfo: {
//         code: trackingData.carrier,
//         name: trackingData.carrier_name,
//       },
//       events,
//       orderStatus,
//     };

//   } catch (error) {
//     console.error(`❌ Failed to retrieve tracking info for ${input.trackingId}:`, error);
//     return {
//       success: false,
//       message: 'Failed to retrieve tracking info',
//       action: 'GET_TRACKING_INFO',
//       trackingId: input.trackingId,
//       error: error instanceof Error ? error.message : 'Unknown error',
//     };
//   }
// }

// // ============================================================================
// // ENHANCED CARRIER CODE HANDLING
// // ============================================================================

// /**
//  * Parse and validate carrier code for 17track API
//  */
// function parseCarrierCode(carrierCode: string | number): number | null {
//   try {
//     // If it's already a number, return it
//     if (typeof carrierCode === 'number') {
//       return carrierCode > 0 ? carrierCode : null;
//     }

//     // If it's a string, try to parse as number
//     if (typeof carrierCode === 'string') {
//       // Check if it's a numeric string
//       const parsed = parseInt(carrierCode, 10);
//       if (!isNaN(parsed) && parsed > 0) {
//         return parsed;
//       }

//       // If it's a carrier name, we could map it to 17track carrier codes
//       // For now, let 17track auto-detect
//       console.log(`🤔 Carrier code "${carrierCode}" is not numeric, using auto-detection`);
//       return null;
//     }

//     return null;

//   } catch (error) {
//     console.error('Error parsing carrier code:', error);
//     return null;
//   }
// }

// // ============================================================================
// // EVENT EXTRACTION WITH SUB-STATUS SUPPORT
// // ============================================================================

// async function extractTrackingEvents(trackingData: any): Promise<Array<{
//   timestamp: string;
//   status: string;
//   subStatus?: string; // NEW: Add sub-status support
//   location: string;
//   description: string;
//   coordinates?: { latitude?: number; longitude?: number };
// }>> {
  
//   try {
//     const providers = trackingData?.track_info?.tracking?.providers;
//     if (!providers?.length || !providers[0]?.events?.length) {
//       console.log('⚠️ No tracking events found in response');
//       return [];
//     }

//     const events = providers[0].events
//       .filter((event: any) => event.time_utc)
//       .map((event: any) => {
//         const mappedEvent = {
//           timestamp: event.time_utc,
//           status: mapTrackingStage(event.stage || event.sub_status || 'UNKNOWN'),
//           subStatus: extractSubStatus(event), // NEW: Extract sub-status
//           location: formatLocation(event),
//           description: event.description || 'No description',
//           coordinates: getCoordinates(event),
//         };

//         console.log(`📍 Event: ${mappedEvent.status}${mappedEvent.subStatus ? ` [${mappedEvent.subStatus}]` : ''} at ${mappedEvent.location}`);
//         return mappedEvent;
//       })
//       .sort((a: any, b: any) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

//     return events;

//   } catch (error) {
//     console.error('Error extracting events:', error);
//     return [];
//   }
// }

// function extractOrderStatus(trackingData: any): {
//   current?: string;
//   subStatus?: string; // NEW: Add sub-status support
//   isDelivered?: boolean;
//   estimatedDelivery?: string;
//   confirmedDelivery?: string;
// } {
  
//   const status: any = {};

//   try {
//     if (trackingData?.track_info?.latest_status?.status) {
//       status.current = mapTrackingStage(trackingData.track_info.latest_status.status);
//       status.subStatus = extractSubStatusFromLatest(trackingData.track_info.latest_status); // NEW: Extract sub-status
//       status.isDelivered = status.current === 'DELIVERED';
//       //status.timeUTC= trackingData.track_info.latest_event.time_utc || new Date().toISOString();
//       console.log(`📊 Order status: ${status.current}${status.subStatus ? ` [${status.subStatus}]` : ''}, Delivered: ${status.isDelivered}`);
//     }

//     if (trackingData?.track_info?.time_metrics?.estimated_delivery_date?.to) {
//       status.estimatedDelivery = trackingData.track_info.time_metrics.estimated_delivery_date.to;
//     }

//     if (status.isDelivered && trackingData?.track_info?.latest_event?.time_utc) {
//       status.confirmedDelivery = trackingData.track_info.latest_event.time_utc;
//     }

//   } catch (error) {
//     console.error('Error extracting order status:', error);
//   }

//   return status;
// }

// // ============================================================================
// // SUB-STATUS EXTRACTION FUNCTIONS
// // ============================================================================

// /**
//  * Extract sub-status from tracking event
//  */
// function extractSubStatus(event: any): string | undefined {
//   try {
//     // Priority order for sub-status extraction:
//     // 1. sub_status field (most specific)
//     // 2. sub_status_description 
//     // 3. status_description if it contains exception info
//     // 4. stage if different from main status

//     if (event.sub_status) {
//       return event.sub_status;
//     }

//     if (event.sub_status_description) {
//       return event.sub_status_description;
//     }

//     // Check for exception keywords in description
//     if (event.description) {
//       const description = event.description.toLowerCase();
//       if (description.includes('lost')) return 'Exception_Lost';
//       if (description.includes('destroyed')) return 'Exception_Destroyed';
//       if (description.includes('cancel')) return 'Exception_Cancel';
//       if (description.includes('damaged')) return 'Exception_Damaged';
//       if (description.includes('refused')) return 'Exception_Refused';
//     }

//     // Check if stage provides additional info beyond main status
//     if (event.stage && event.stage !== event.status) {
//       return event.stage;
//     }

//     return undefined;

//   } catch (error) {
//     console.error('Error extracting sub-status:', error);
//     return undefined;
//   }
// }

// /**
//  * Extract sub-status from latest status object
//  */
// function extractSubStatusFromLatest(latestStatus: any): string | undefined {
//   try {
//     if (latestStatus.sub_status) {
//       return latestStatus.sub_status;
//     }

//     if (latestStatus.sub_status_description) {
//       return latestStatus.sub_status_description;
//     }

//     // Check status description for exception details
//     if (latestStatus.status_description) {
//       const description = latestStatus.status_description.toLowerCase();
//       if (description.includes('lost')) return 'Exception_Lost';
//       if (description.includes('destroyed')) return 'Exception_Destroyed';
//       if (description.includes('cancel')) return 'Exception_Cancel';
//       if (description.includes('damaged')) return 'Exception_Damaged';
//       if (description.includes('refused')) return 'Exception_Refused';
//     }

//     return undefined;

//   } catch (error) {
//     console.error('Error extracting sub-status from latest:', error);
//     return undefined;
//   }
// }

// // ============================================================================
// // UTILITY FUNCTIONS
// // ============================================================================

// function mapTrackingStage(stage: string): string {
//   const stageMap: Record<string, string> = {
//     'InfoReceived': 'PENDING',
//     'PickedUp': 'PICKED_UP',
//     'InTransit_PickedUp': 'PICKED_UP',
//     'InTransit_Other': 'IN_TRANSIT',
//     'InTransit_CustomsReleased': 'CUSTOMS_CLEARED',
//     'Departure': 'IN_TRANSIT',
//     'Arrival': 'ARRIVED',
//     'AvailableForPickup': 'AVAILABLE_FOR_PICKUP',
//     'OutForDelivery': 'OUT_FOR_DELIVERY',
//     'Delivered': 'DELIVERED',
//     'Returning': 'RETURNING',
//     'Returned': 'RETURNED',
//     'Exception': 'EXCEPTION',
    
//     // Handle specific exception sub-statuses
//     'Exception_Lost': 'EXCEPTION',
//     'Exception_Destroyed': 'EXCEPTION', 
//     'Exception_Cancel': 'EXCEPTION',
//     'Exception_Damaged': 'EXCEPTION',
//     'Exception_Refused': 'EXCEPTION',
//   };

//   return stageMap[stage] || stage || 'UNKNOWN';
// }

// function formatLocation(event: any): string {
//   if (!event.address) {
//     return event.location || 'Unknown Location';
//   }

//   const parts = [event.address.city, event.address.state, event.address.country]
//     .filter(Boolean);
  
//   return parts.length > 0 ? parts.join(', ') : 'Unknown Location';
// }

// function getCoordinates(event: any): { latitude?: number; longitude?: number } | undefined {
//   if (event.address?.coordinates?.latitude && event.address?.coordinates?.longitude) {
//     return {
//       latitude: event.address.coordinates.latitude,
//       longitude: event.address.coordinates.longitude,
//     };
//   }
  
//   return undefined;
// }

// export default carrierHandler;

import { Context } from 'aws-lambda';
import { LambdaClient, InvokeCommand } from '@aws-sdk/client-lambda';
import { z } from 'zod';
import { TrackingApi } from '../utils/trackingApi';

// ============================================================================
// ENVIRONMENT VARIABLES
// ============================================================================

const USE_SIMULATOR = process.env.USE_TRACKING_SIMULATOR === 'true';
const SIMULATOR_LAMBDA_ARN = process.env.TRACKING_SIMULATOR_LAMBDA_ARN;
const AWS_REGION = process.env.AWS_REGION || 'us-east-1';

// Initialize Lambda client for simulator
const lambdaClient = new LambdaClient({ region: AWS_REGION });

// ============================================================================
// SCHEMAS
// ============================================================================

const TrackingProcessorInputSchema = z.object({
  trackingId: z.string().min(1),
  carrierCode: z.union([z.string(), z.number()]).optional(),
  action: z.enum(['REGISTER_TRACKING', 'GET_TRACKING_INFO', 'DELETE_TRACKING']),
});

type TrackingProcessorInput = z.infer<typeof TrackingProcessorInputSchema>;

interface TrackingProcessorResponse {
  success: boolean;
  message: string;
  action: string;
  trackingId: string;
  trackingData?: any;
  carrierInfo?: {
    code?: number;
    name?: string;
  };
  events?: Array<{
    timestamp: string;
    status: string;
    subStatus?: string;
    location: string;
    description: string;
    coordinates?: { latitude?: number; longitude?: number };
  }>;
  orderStatus?: {
    current?: string;
    subStatus?: string;
    isDelivered?: boolean;
    estimatedDelivery?: string;
    confirmedDelivery?: string;
  };
  error?: string;
}

// ============================================================================
// MAIN HANDLER
// ============================================================================

export const carrierHandler = async (
  event: TrackingProcessorInput,
  context: Context
): Promise<TrackingProcessorResponse> => {

  try {
    console.log('🎯 Carrier processor invoked:', JSON.stringify(event, null, 2));
    console.log(`🔧 Using ${USE_SIMULATOR ? 'SIMULATOR' : 'REAL API'}`);
    
    const validatedInput = TrackingProcessorInputSchema.parse(event);
    
    // Choose implementation based on configuration
    if (USE_SIMULATOR) {
      return await handleWithSimulator(validatedInput);
    } else {
      return await handleWithRealAPI(validatedInput);
    }

  } catch (error) {
    console.error('❌ Tracking processor error:', error);
    
    if (error instanceof z.ZodError) {
      return {
        success: false,
        message: 'Invalid input data',
        action: event.action || 'unknown',
        trackingId: event.trackingId || 'unknown',
        error: 'Validation failed',
      };
    }

    return {
      success: false,
      message: 'Tracking API processing failed',
      action: event.action || 'unknown',
      trackingId: event.trackingId || 'unknown',
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

// ============================================================================
// SIMULATOR IMPLEMENTATION
// ============================================================================

async function handleWithSimulator(input: TrackingProcessorInput): Promise<TrackingProcessorResponse> {
  try {
    console.log(`🎭 Using simulator for ${input.action}: ${input.trackingId}`);

    if (!SIMULATOR_LAMBDA_ARN) {
      throw new Error('TRACKING_SIMULATOR_LAMBDA_ARN environment variable not set');
    }

    // Prepare request for simulator
    const simulatorRequest = {
      number: input.trackingId,
      auto_detection: true,
      ...(input.carrierCode && { carrier: input.carrierCode }),
    };

    console.log('📦 Simulator request:', JSON.stringify(simulatorRequest, null, 2));
    // Determine simulator action
    let simulatorAction = 'getTrackInfo';
    switch (input.action) {
      case 'REGISTER_TRACKING':
        simulatorAction = 'register';
        break;
      case 'DELETE_TRACKING':
        simulatorAction = 'deletetrack';
        break;
    }

    // Invoke simulator
    const simulatorPayload = {
      action: simulatorAction,
      data: [simulatorRequest],
    };

    const command = new InvokeCommand({
      FunctionName: SIMULATOR_LAMBDA_ARN,
      InvocationType: 'RequestResponse',
      Payload: JSON.stringify(simulatorPayload),
    });

    const response = await lambdaClient.send(command);
    
    if (response.StatusCode !== 200) {
      throw new Error(`Simulator invocation failed with status ${response.StatusCode}`);
    }
    if (!response.Payload) {
      throw new Error('Simulator response payload is empty');
    }
    
    const simulatorResponse = JSON.parse(new TextDecoder().decode(response.Payload));
    
    console.log('📬 Simulator response:', JSON.stringify(simulatorResponse, null, 2));
    // Convert simulator response to our format
    return await convertSimulatorResponse(input, simulatorResponse);

  } catch (error) {
    console.error(`❌ Simulator error for ${input.trackingId}:`, error);
    return {
      success: false,
      message: 'Simulator processing failed',
      action: input.action,
      trackingId: input.trackingId,
      error: error instanceof Error ? error.message : 'Simulator error',
    };
  }
}

// ============================================================================
// REAL API IMPLEMENTATION (EXISTING LOGIC)
// ============================================================================

async function handleWithRealAPI(input: TrackingProcessorInput): Promise<TrackingProcessorResponse> {
  const trackingApi = new TrackingApi({
    timeout: 25000,
    retries: 2,
  });

  switch (input.action) {
    case 'REGISTER_TRACKING':
      return await handleRegistration(input, trackingApi);
    
    case 'GET_TRACKING_INFO':
      return await handleTrackingInfo(input, trackingApi);
    
    case 'DELETE_TRACKING':
      return await handleDeleteTracking(input, trackingApi);
    
    default:
      throw new Error(`Unsupported action: ${input.action}`);
  }
}

async function handleDeleteTracking(
  input: TrackingProcessorInput,
  trackingApi: TrackingApi
): Promise<TrackingProcessorResponse> {

  try {
    console.log(`🗑️ Deleting tracking for: ${input.trackingId}`);
    
    const deleteResponse = await trackingApi.deleteTrackingNumber({
      number: input.trackingId,
      auto_detection: true,
      ...(input.carrierCode && { carrier: input.carrierCode }),
    });

    if (typeof deleteResponse.data === 'string') {
      return {
        success: false,
        message: 'Delete tracking failed',
        action: 'DELETE_TRACKING',
        trackingId: input.trackingId,
        error: deleteResponse.data,
      };
    }

    if (deleteResponse.data.accepted.length > 0) {
      return {
        success: true,
        message: 'Tracking number deleted successfully',
        action: 'DELETE_TRACKING',
        trackingId: input.trackingId,
        trackingData: deleteResponse,
      };
    }

    if (deleteResponse.data.rejected.length > 0) {
      const rejection = deleteResponse.data.rejected[0];
      return {
        success: false,
        message: 'Delete tracking rejected',
        action: 'DELETE_TRACKING',
        trackingId: input.trackingId,
        error: rejection.error.message,
      };
    }

    return {
      success: false,
      message: 'No tracking numbers processed for deletion',
      action: 'DELETE_TRACKING',
      trackingId: input.trackingId,
      error: 'Empty response',
    };

  } catch (error) {
    console.error(`❌ Delete tracking failed for ${input.trackingId}:`, error);
    return {
      success: false,
      message: 'Delete tracking failed',
      action: 'DELETE_TRACKING',
      trackingId: input.trackingId,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
};

async function handleRegistration(
  input: TrackingProcessorInput,
  trackingApi: TrackingApi
): Promise<TrackingProcessorResponse> {

  try {
    console.log(`📝 Registering tracking number: ${input.trackingId}`);
    
    const requestPayload: any = {
      number: input.trackingId,
      auto_detection: true,
    };

    if (input.carrierCode) {
      const carrierCode = parseCarrierCode(input.carrierCode);
      if (carrierCode) {
        requestPayload.carrier = carrierCode;
        console.log(`🚛 Using carrier code: ${carrierCode} for registration`);
      }
    }

    const registrationResponse = await trackingApi.registerTrackingNumber(requestPayload);

    if (typeof registrationResponse.data === 'string') {
      return {
        success: false,
        message: 'Registration failed',
        action: 'REGISTER_TRACKING',
        trackingId: input.trackingId,
        error: registrationResponse.data,
      };
    }

    if (registrationResponse.data.accepted.length > 0) {
      const accepted = registrationResponse.data.accepted[0];
      
      return {
        success: true,
        message: 'Tracking number registered successfully',
        action: 'REGISTER_TRACKING',
        trackingId: input.trackingId,
        trackingData: registrationResponse,
        carrierInfo: {
          code: accepted.carrier,
          name: accepted.carrier_name,
        },
      };
    }

    if (registrationResponse.data.rejected.length > 0) {
      const rejection = registrationResponse.data.rejected[0];
      return {
        success: false,
        message: 'Registration rejected',
        action: 'REGISTER_TRACKING',
        trackingId: input.trackingId,
        error: rejection.error.message,
      };
    }

    return {
      success: false,
      message: 'No tracking numbers processed',
      action: 'REGISTER_TRACKING',
      trackingId: input.trackingId,
      error: 'Empty response',
    };

  } catch (error) {
    console.error(`❌ Registration failed for ${input.trackingId}:`, error);
    return {
      success: false,
      message: 'Registration failed',
      action: 'REGISTER_TRACKING',
      trackingId: input.trackingId,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

async function handleTrackingInfo(
  input: TrackingProcessorInput,
  trackingApi: TrackingApi
): Promise<TrackingProcessorResponse> {

  try {
    console.log(`🔍 Retrieving tracking info for: ${input.trackingId}`);

    const requestPayload: any = {
      number: input.trackingId,
      auto_detection: true,
    };

    if (input.carrierCode) {
      const carrierCode = parseCarrierCode(input.carrierCode);
      if (carrierCode) {
        requestPayload.carrier = carrierCode;
        console.log(`🚛 Using carrier code: ${carrierCode} for tracking info`);
      }
    }

    const trackingInfo = await trackingApi.getTrackingInfo(requestPayload);

    if (typeof trackingInfo.data === 'string') {
      return {
        success: false,
        message: 'Tracking info failed',
        action: 'GET_TRACKING_INFO',
        trackingId: input.trackingId,
        error: trackingInfo.data,
      };
    }

    if (!trackingInfo.data?.accepted?.length) {
      return {
        success: false,
        message: 'No tracking information found',
        action: 'GET_TRACKING_INFO',
        trackingId: input.trackingId,
        error: 'No data available',
      };
    }

    if (trackingInfo.data.rejected?.length > 0) {
      const rejection = trackingInfo.data.rejected[0];
      return {
        success: false,
        message: 'Tracking info rejected',
        action: 'GET_TRACKING_INFO',
        trackingId: input.trackingId,
        error: rejection.error.message,
      };
    }

    const trackingData = trackingInfo.data.accepted[0];
    const events = await extractTrackingEvents(trackingData);
    const orderStatus = extractOrderStatus(trackingData);

    console.log(`✅ Retrieved ${events.length} events for ${input.trackingId}`);

    return {
      success: true,
      message: 'Tracking information retrieved',
      action: 'GET_TRACKING_INFO',
      trackingId: input.trackingId,
      trackingData: trackingInfo,
      carrierInfo: {
        code: trackingData.carrier,
        name: trackingData.carrier_name,
      },
      events,
      orderStatus,
    };

  } catch (error) {
    console.error(`❌ Failed to retrieve tracking info for ${input.trackingId}:`, error);
    return {
      success: false,
      message: 'Failed to retrieve tracking info',
      action: 'GET_TRACKING_INFO',
      trackingId: input.trackingId,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

// ============================================================================
// SIMULATOR RESPONSE CONVERSION
// ============================================================================

async function convertSimulatorResponse(
  input: TrackingProcessorInput, 
  simulatorResponse: any
): Promise<TrackingProcessorResponse> {
  
  try {
    if (simulatorResponse.code !== 0) {
      return {
        success: false,
        message: 'Simulator returned error',
        action: input.action,
        trackingId: input.trackingId,
        error: simulatorResponse.msg || 'Simulator error',
      };
    }

    // Handle different actions
    switch (input.action) {
      case 'REGISTER_TRACKING':
        return convertRegistrationResponse(input, simulatorResponse);
      
      case 'GET_TRACKING_INFO':
        return await convertTrackingInfoResponse(input, simulatorResponse);
      
      case 'DELETE_TRACKING':
        return convertDeleteResponse(input, simulatorResponse);
      
      default:
        throw new Error(`Unsupported action: ${input.action}`);
    }

  } catch (error) {
    console.error('❌ Error converting simulator response:', error);
    return {
      success: false,
      message: 'Failed to process simulator response',
      action: input.action,
      trackingId: input.trackingId,
      error: error instanceof Error ? error.message : 'Conversion error',
    };
  }
}

function convertRegistrationResponse(
  input: TrackingProcessorInput, 
  simulatorResponse: any
): TrackingProcessorResponse {
  
  const accepted = simulatorResponse.data?.accepted || [];
  const rejected = simulatorResponse.data?.rejected || [];

  // Find our tracking number in the response
  const acceptedItem = accepted.find((item: any) => item.number === input.trackingId);
  const rejectedItem = rejected.find((item: any) => item.number === input.trackingId);

  if (acceptedItem) {
    return {
      success: true,
      message: 'Tracking number registered successfully',
      action: 'REGISTER_TRACKING',
      trackingId: input.trackingId,
      trackingData: simulatorResponse,
      carrierInfo: {
        code: acceptedItem.carrier,
        name: acceptedItem.carrier_name,
      },
    };
  }

  if (rejectedItem) {
    return {
      success: false,
      message: 'Registration rejected',
      action: 'REGISTER_TRACKING',
      trackingId: input.trackingId,
      error: rejectedItem.error?.message || 'Registration rejected',
    };
  }

  return {
    success: false,
    message: 'Tracking number not found in response',
    action: 'REGISTER_TRACKING',
    trackingId: input.trackingId,
    error: 'No response for tracking number',
  };
}

async function convertTrackingInfoResponse(
  input: TrackingProcessorInput, 
  simulatorResponse: any
): Promise<TrackingProcessorResponse> {
  
  const accepted = simulatorResponse.data?.accepted || [];
  const rejected = simulatorResponse.data?.rejected || [];

  const acceptedItem = accepted.find((item: any) => item.number === input.trackingId);
  const rejectedItem = rejected.find((item: any) => item.number === input.trackingId);

  if (rejectedItem) {
    return {
      success: false,
      message: 'Tracking info rejected',
      action: 'GET_TRACKING_INFO',
      trackingId: input.trackingId,
      error: rejectedItem.error?.message || 'Tracking info rejected',
    };
  }

  if (!acceptedItem || !acceptedItem.track_info) {
    return {
      success: false,
      message: 'No tracking information found',
      action: 'GET_TRACKING_INFO',
      trackingId: input.trackingId,
      error: 'No tracking data available',
    };
  }

  // Extract events and status from simulator track_info
  const events = await extractTrackingEvents(acceptedItem);
  const orderStatus = extractOrderStatus(acceptedItem);

  return {
    success: true,
    message: 'Tracking information retrieved',
    action: 'GET_TRACKING_INFO',
    trackingId: input.trackingId,
    trackingData: simulatorResponse,
    carrierInfo: {
      code: acceptedItem.carrier,
      name: acceptedItem.carrier_name,
    },
    events,
    orderStatus,
  };
}

function convertDeleteResponse(
  input: TrackingProcessorInput, 
  simulatorResponse: any
): TrackingProcessorResponse {
  
  const accepted = simulatorResponse.data?.accepted || [];
  const rejected = simulatorResponse.data?.rejected || [];

  const acceptedItem = accepted.find((item: any) => item.number === input.trackingId);
  const rejectedItem = rejected.find((item: any) => item.number === input.trackingId);

  if (acceptedItem) {
    return {
      success: true,
      message: 'Tracking number deleted successfully',
      action: 'DELETE_TRACKING',
      trackingId: input.trackingId,
      trackingData: simulatorResponse,
    };
  }

  if (rejectedItem) {
    return {
      success: false,
      message: 'Delete tracking rejected',
      action: 'DELETE_TRACKING',
      trackingId: input.trackingId,
      error: rejectedItem.error?.message || 'Delete rejected',
    };
  }

  return {
    success: false,
    message: 'Tracking number not found in delete response',
    action: 'DELETE_TRACKING',
    trackingId: input.trackingId,
    error: 'No response for tracking number',
  };
}

// ============================================================================
// UTILITY FUNCTIONS (UNCHANGED)
// ============================================================================

function parseCarrierCode(carrierCode: string | number): number | null {
  try {
    if (typeof carrierCode === 'number') {
      return carrierCode > 0 ? carrierCode : null;
    }

    if (typeof carrierCode === 'string') {
      const parsed = parseInt(carrierCode, 10);
      if (!isNaN(parsed) && parsed > 0) {
        return parsed;
      }

      console.log(`🤔 Carrier code "${carrierCode}" is not numeric, using auto-detection`);
      return null;
    }

    return null;

  } catch (error) {
    console.error('Error parsing carrier code:', error);
    return null;
  }
}

async function extractTrackingEvents(trackingData: any): Promise<Array<{
  timestamp: string;
  status: string;
  subStatus?: string;
  location: string;
  description: string;
  coordinates?: { latitude?: number; longitude?: number };
}>> {
  
  try {
    const providers = trackingData?.track_info?.tracking?.providers;
    if (!providers?.length || !providers[0]?.events?.length) {
      console.log('⚠️ No tracking events found in response');
      return [];
    }

    const events = providers[0].events
      .filter((event: any) => event.time_utc)
      .map((event: any) => {
        const mappedEvent = {
          timestamp: event.time_utc,
          status: mapTrackingStage(event.stage || event.sub_status || 'UNKNOWN'),
          subStatus: extractSubStatus(event),
          location: formatLocation(event),
          description: event.description || 'No description',
          coordinates: getCoordinates(event),
        };

        console.log(`📍 Event: ${mappedEvent.status}${mappedEvent.subStatus ? ` [${mappedEvent.subStatus}]` : ''} at ${mappedEvent.location}`);
        return mappedEvent;
      })
      .sort((a: any, b: any) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

    return events;

  } catch (error) {
    console.error('Error extracting events:', error);
    return [];
  }
}

function extractOrderStatus(trackingData: any): {
  current?: string;
  subStatus?: string;
  isDelivered?: boolean;
  estimatedDelivery?: string;
  confirmedDelivery?: string;
} {
  
  const status: any = {};

  try {
    if (trackingData?.track_info?.latest_status?.status) {
      status.current = mapTrackingStage(trackingData.track_info.latest_status.status);
      status.subStatus = extractSubStatusFromLatest(trackingData.track_info.latest_status);
      status.isDelivered = status.current === 'DELIVERED';
      
      console.log(`📊 Order status: ${status.current}${status.subStatus ? ` [${status.subStatus}]` : ''}, Delivered: ${status.isDelivered}`);
    }

    if (trackingData?.track_info?.time_metrics?.estimated_delivery_date?.to) {
      status.estimatedDelivery = trackingData.track_info.time_metrics.estimated_delivery_date.to;
    }

    if (status.isDelivered && trackingData?.track_info?.latest_event?.time_utc) {
      status.confirmedDelivery = trackingData.track_info.latest_event.time_utc;
    }

  } catch (error) {
    console.error('Error extracting order status:', error);
  }

  return status;
}

function extractSubStatus(event: any): string | undefined {
  try {
    if (event.sub_status) {
      return event.sub_status;
    }

    if (event.sub_status_description) {
      return event.sub_status_description;
    }

    if (event.description) {
      const description = event.description.toLowerCase();
      if (description.includes('lost')) return 'Exception_Lost';
      if (description.includes('destroyed')) return 'Exception_Destroyed';
      if (description.includes('cancel')) return 'Exception_Cancel';
      if (description.includes('damaged')) return 'Exception_Damaged';
      if (description.includes('refused')) return 'Exception_Refused';
    }

    if (event.stage && event.stage !== event.status) {
      return event.stage;
    }

    return undefined;

  } catch (error) {
    console.error('Error extracting sub-status:', error);
    return undefined;
  }
}

function extractSubStatusFromLatest(latestStatus: any): string | undefined {
  try {
    if (latestStatus.sub_status) {
      return latestStatus.sub_status;
    }

    if (latestStatus.sub_status_description) {
      return latestStatus.sub_status_description;
    }

    if (latestStatus.status_description) {
      const description = latestStatus.status_description.toLowerCase();
      if (description.includes('lost')) return 'Exception_Lost';
      if (description.includes('destroyed')) return 'Exception_Destroyed';
      if (description.includes('cancel')) return 'Exception_Cancel';
      if (description.includes('damaged')) return 'Exception_Damaged';
      if (description.includes('refused')) return 'Exception_Refused';
    }

    return undefined;

  } catch (error) {
    console.error('Error extracting sub-status from latest:', error);
    return undefined;
  }
}

function mapTrackingStage(stage: string): string {
  const stageMap: Record<string, string> = {
    'InfoReceived': 'PENDING',
    'PickedUp': 'PICKED_UP',
    'InTransit_PickedUp': 'PICKED_UP',
    'InTransit_Other': 'IN_TRANSIT',
    'InTransit_CustomsReleased': 'CUSTOMS_CLEARED',
    'Departure': 'IN_TRANSIT',
    'Arrival': 'ARRIVED',
    'AvailableForPickup': 'AVAILABLE_FOR_PICKUP',
    'OutForDelivery': 'OUT_FOR_DELIVERY',
    'Delivered': 'DELIVERED',
    'Returning': 'RETURNING',
    'Returned': 'RETURNED',
    'Exception': 'EXCEPTION',
    
    'Exception_Lost': 'EXCEPTION',
    'Exception_Destroyed': 'EXCEPTION', 
    'Exception_Cancel': 'EXCEPTION',
    'Exception_Damaged': 'EXCEPTION',
    'Exception_Refused': 'EXCEPTION',
  };

  return stageMap[stage] || stage || 'UNKNOWN';
}

function formatLocation(event: any): string {
  if (!event.address) {
    return event.location || 'Unknown Location';
  }

  const parts = [event.address.city, event.address.state, event.address.country]
    .filter(Boolean);
  
  return parts.length > 0 ? parts.join(', ') : 'Unknown Location';
}

function getCoordinates(event: any): { latitude?: number; longitude?: number } | undefined {
  if (event.address?.coordinates?.latitude && event.address?.coordinates?.longitude) {
    return {
      latitude: event.address.coordinates.latitude,
      longitude: event.address.coordinates.longitude,
    };
  }
  
  return undefined;
}

export default carrierHandler;