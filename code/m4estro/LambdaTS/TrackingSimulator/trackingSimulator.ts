// src/functions/trackingSimulator.ts
import { Context } from 'aws-lambda';
import { z } from 'zod';
import { DatabaseUtil } from '../utils/DatabaseUtils';

// ============================================================================
// SCHEMAS (Matching 17track API exactly)
// ============================================================================

const TrackingRequestSchema = z.object({
  number: z.string().min(1),
  carrier: z.union([z.string(), z.number()]).optional(),
  auto_detection: z.boolean().default(true),
});

const SimulatorRequestSchema = z.object({
  action: z.enum(['register', 'getTrackInfo', 'deletetrack']),
  data: z.array(TrackingRequestSchema),
});

// Response schemas matching 17track exactly
const AcceptedItemSchema = z.object({
  number: z.string(),
  carrier: z.number().optional(),
  carrier_name: z.string().optional(),
  track_info: z.any().optional(),
});

const RejectedItemSchema = z.object({
  number: z.string(),
  error: z.object({
    code: z.number(),
    message: z.string(),
  }),
});

const APIResponseSchema = z.object({
  code: z.number(),
  msg: z.string().optional(),
  data: z.object({
    accepted: z.array(AcceptedItemSchema),
    rejected: z.array(RejectedItemSchema),
  }),
});

// ============================================================================
// SIMULATION DATA STRUCTURES
// ============================================================================

interface TrackingScenario {
  name: string;
  carrier: number;
  carrier_name: string;
  events: TrackingEvent[];
  completion_type: 'DELIVERED' | 'EXCEPTION' | 'RETURNED' | 'EXPIRED' | null;
  estimated_delivery_minutes: number;
}

interface TrackingEvent {
  stage: string;
  sub_status?: string;
  description: string;
  location: string;
  address?: {
    city?: string;
    state?: string;
    country?: string;
    coordinates?: {
      latitude: number;
      longitude: number;
    };
  };
  delay_minutes: number; // Minutes after registration
}

interface SimulatedTracking {
  id: number;
  tracking_number: string;
  carrier_code: number;
  carrier_name: string;
  scenario: string;
  registered_at: Date;
  current_event_index: number;
  status: 'active' | 'completed' | 'expired';
  completion_type?: string;
  created_at: Date;
  updated_at: Date;
}

// ============================================================================
// PREDEFINED TRACKING SCENARIOS (MINUTE-BASED FOR FAST TESTING)
// ============================================================================

const TRACKING_SCENARIOS: TrackingScenario[] = [
  {
    name: 'standard_delivery',
    carrier: 100001, // DHL
    carrier_name: 'DHL Express',
    completion_type: 'DELIVERED',
    estimated_delivery_minutes: 25,
    events: [
      {
        stage: 'InfoReceived',
        description: 'Shipment information received',
        location: 'Shipper\'s Warehouse, Shanghai, China',
        address: { city: 'Shanghai', country: 'China', coordinates: { latitude: 31.2304, longitude: 121.4737 } },
        delay_minutes: 0
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_PickedUp',
        description: 'Package picked up by courier',
        location: 'Shanghai, China',
        address: { city: 'Shanghai', country: 'China', coordinates: { latitude: 31.2304, longitude: 121.4737 } },
        delay_minutes: 2
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Departure',
        description: 'Package departed from origin facility',
        location: 'Shanghai Pudong Airport, China',
        address: { city: 'Shanghai', country: 'China', coordinates: { latitude: 31.1434, longitude: 121.8052 } },
        delay_minutes: 5
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Arrival',
        description: 'Package arrived at destination country',
        location: 'Frankfurt Airport, Germany',
        address: { city: 'Frankfurt', country: 'Germany', coordinates: { latitude: 50.0379, longitude: 8.5622 } },
        delay_minutes: 8
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_CustomsProcessing',
        description: 'Package processing through customs',
        location: 'Frankfurt Customs, Germany',
        address: { city: 'Frankfurt', country: 'Germany', coordinates: { latitude: 50.0379, longitude: 8.5622 } },
        delay_minutes: 12
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_CustomsReleased',
        description: 'Package cleared customs',
        location: 'Frankfurt, Germany',
        address: { city: 'Frankfurt', country: 'Germany', coordinates: { latitude: 50.0379, longitude: 8.5622 } },
        delay_minutes: 15
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Other',
        description: 'Package in transit to delivery facility',
        location: 'Berlin Sorting Center, Germany',
        address: { city: 'Berlin', country: 'Germany', coordinates: { latitude: 52.5200, longitude: 13.4050 } },
        delay_minutes: 18
      },
      {
        stage: 'OutForDelivery',
        description: 'Package out for delivery',
        location: 'Berlin, Germany',
        address: { city: 'Berlin', country: 'Germany', coordinates: { latitude: 52.5200, longitude: 13.4050 } },
        delay_minutes: 22
      },
      {
        stage: 'Delivered',
        description: 'Package delivered successfully',
        location: 'Berlin, Germany',
        address: { city: 'Berlin', country: 'Germany', coordinates: { latitude: 52.5200, longitude: 13.4050 } },
        delay_minutes: 25
      }
    ]
  },
  {
    name: 'us_to_germany_route',
    carrier: 100002, // UPS
    carrier_name: 'UPS',
    completion_type: 'DELIVERED',
    estimated_delivery_minutes: 120, // 2 hours for testing (represents ~5 days)
    events: [
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Arrival',
        description: 'Arrived at Facility',
        location: 'Thief River Falls, MN, US',
        address: { city: 'Thief River Falls', state: 'MN', country: 'US', coordinates: { latitude: 48.1169, longitude: -96.1795 } },
        delay_minutes: 0
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Departure',
        description: 'Departed from Facility',
        location: 'Thief River Falls, MN, US',
        address: { city: 'Thief River Falls', state: 'MN', country: 'US', coordinates: { latitude: 48.1169, longitude: -96.1795 } },
        delay_minutes: 15
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Departure',
        description: 'Departed from Facility',
        location: 'Fargo, ND, US',
        address: { city: 'Fargo', state: 'ND', country: 'US', coordinates: { latitude: 46.8772, longitude: -96.7898 } },
        delay_minutes: 35
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Arrival',
        description: 'Arrived at Facility',
        location: 'Louisville, KY, US',
        address: { city: 'Louisville', state: 'KY', country: 'US', coordinates: { latitude: 38.2527, longitude: -85.7585 } },
        delay_minutes: 50
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Departure',
        description: 'Departed from Facility',
        location: 'Louisville, KY, US',
        address: { city: 'Louisville', state: 'KY', country: 'US', coordinates: { latitude: 38.2527, longitude: -85.7585 } },
        delay_minutes: 75
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Arrival',
        description: 'Arrived at Facility',
        location: 'Koeln, DE',
        address: { city: 'Köln', country: 'Germany', coordinates: { latitude: 50.9375, longitude: 6.9603 } },
        delay_minutes: 100
      },
      {
        stage: 'Delivered',
        description: 'Package delivered successfully',
        location: 'Koeln, DE',
        address: { city: 'Köln', country: 'Germany', coordinates: { latitude: 50.9375, longitude: 6.9603 } },
        delay_minutes: 120
      }
    ]
  },
  {
    name: 'china_to_germany_dhl',
    carrier: 100001, // DHL
    carrier_name: 'DHL Express',
    completion_type: 'DELIVERED',
    estimated_delivery_minutes: 150, // 2.5 hours for testing (represents ~6 days)
    events: [
      {
        stage: 'InTransit',
        sub_status: 'InTransit_PickedUp',
        description: 'Spedizione ritirata',
        location: 'SHENZHEN, CHINA',
        address: { city: 'Shenzhen', country: 'China', coordinates: { latitude: 22.5431, longitude: 114.0579 } },
        delay_minutes: 0
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Other',
        description: 'Elaborata presso il centro DHL',
        location: 'SHENZHEN, CHINA',
        address: { city: 'Shenzhen', country: 'China', coordinates: { latitude: 22.5431, longitude: 114.0579 } },
        delay_minutes: 20
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Departure',
        description: 'Partita da una sede DHL',
        location: 'SHENZHEN, CHINA',
        address: { city: 'Shenzhen', country: 'China', coordinates: { latitude: 22.5431, longitude: 114.0579 } },
        delay_minutes: 35
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Arrival',
        description: 'Arrivata presso il centro di smistamento DHL',
        location: 'HONG KONG, HK',
        address: { city: 'Hong Kong', country: 'Hong Kong', coordinates: { latitude: 22.3193, longitude: 114.1694 } },
        delay_minutes: 40
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Other',
        description: 'Elaborata presso DHL HONG KONG',
        location: 'HONG KONG, HK',
        address: { city: 'Hong Kong', country: 'Hong Kong', coordinates: { latitude: 22.3193, longitude: 114.1694 } },
        delay_minutes: 60
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Arrival',
        description: 'Arrivata presso il centro di smistamento DHL FRANKFURT - GERMANY',
        location: 'FRANKFURT, GERMANY',
        address: { city: 'Frankfurt', country: 'Germany', coordinates: { latitude: 50.1109, longitude: 8.6821 } },
        delay_minutes: 85
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Departure',
        description: 'Partita da una sede DHL FRANKFURT - GERMANY',
        location: 'FRANKFURT, GERMANY',
        address: { city: 'Frankfurt', country: 'Germany', coordinates: { latitude: 50.1109, longitude: 8.6821 } },
        delay_minutes: 95
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Arrival',
        description: 'Arrivata presso il centro di smistamento DHL LEIPZIG - GERMANY',
        location: 'LEIPZIG, GERMANY',
        address: { city: 'Leipzig', country: 'Germany', coordinates: { latitude: 51.3397, longitude: 12.3731 } },
        delay_minutes: 110
      },
      {
        stage: 'InTransit',
        sub_status: 'InTransit_Other',
        description: 'Elaborata presso DHL LEIPZIG - GERMANY',
        location: 'LEIPZIG, GERMANY',
        address: { city: 'Leipzig', country: 'Germany', coordinates: { latitude: 51.3397, longitude: 12.3731 } },
        delay_minutes: 130
      },
      {
        stage: 'OutForDelivery',
        description: 'Out for delivery',
        location: 'LEIPZIG, GERMANY',
        address: { city: 'Leipzig', country: 'Germany', coordinates: { latitude: 51.3397, longitude: 12.3731 } },
        delay_minutes: 145
      },
      {
        stage: 'Delivered',
        description: 'Package delivered successfully',
        location: 'LEIPZIG, GERMANY',
        address: { city: 'Leipzig', country: 'Germany', coordinates: { latitude: 51.3397, longitude: 12.3731 } },
        delay_minutes: 150
      }
    ]
  },
];

// ============================================================================
// MAIN HANDLER
// ============================================================================

export const trackingSimulatorHandler = async (
  event: any,
  context: Context
): Promise<any> => {
  let dbUtil: DatabaseUtil | null = null;

  try {
    console.log('🎭 17track Simulator invoked:', JSON.stringify(event, null, 2));

    // Handle different invocation methods
    let requestData: any;
    let action = 'getTrackInfo'; // default

    // Check if this is a structured event with action and data
    if (event.action && event.data) {
      action = event.action;
      requestData = event.data;
      console.log(`🎯 Structured event - Action: ${action}, Data count: ${requestData.length}`);
    }
    // Handle API Gateway format
    else if (event.body) {
      const parsedBody = JSON.parse(event.body);
      if (parsedBody.action && parsedBody.data) {
        action = parsedBody.action;
        requestData = parsedBody.data;
      } else {
        requestData = Array.isArray(parsedBody) ? parsedBody : [parsedBody];
      }
      console.log(`🌐 API Gateway format - Action: ${action}, Data count: ${requestData.length}`);
    }
    // Handle direct Lambda invocation
    else if (Array.isArray(event)) {
      requestData = event;
      console.log(`⚡ Direct array format - Action: ${action}, Data count: ${requestData.length}`);
    }
    // Handle single object invocation
    else {
      requestData = [event];
      console.log(`⚡ Direct single format - Action: ${action}, Data count: ${requestData.length}`);
    }

    // Determine action from path if not already set
    if (event.path) {
      if (event.path.includes('register')) action = 'register';
      else if (event.path.includes('deletetrack')) action = 'deletetrack';
    }

    console.log(`🎯 Final Action: ${action}, Data count: ${requestData.length}`);

    // Initialize database
    dbUtil = DatabaseUtil.fromEnvironment();
    const knex = await dbUtil.getKnex();

    // Process based on action
    let response: any;
    switch (action) {
      case 'register':
        response = await handleRegistration(knex, requestData);
        break;
      case 'getTrackInfo':
        response = await handleGetTrackingInfo(knex, requestData);
        break;
      case 'deletetrack':
        response = await handleDeleteTracking(knex, requestData);
        break;
      default:
        throw new Error(`Unsupported action: ${action}`);
    }

    console.log(`✅ Simulator response: ${response.data.accepted.length} accepted, ${response.data.rejected.length} rejected`);

    // Return in correct format based on invocation type
    if (event.body) {
      // API Gateway response
      return {
        statusCode: 200,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
        body: JSON.stringify(response),
      };
    } else {
      // Direct Lambda response
      return response;
    }

  } catch (error) {
    console.error('❌ Simulator error:', error);
    
    const errorResponse = {
      code: -1,
      msg: error instanceof Error ? error.message : 'Simulator error',
      data: {
        accepted: [],
        rejected: [],
      },
    };

    if (event.body) {
      return {
        statusCode: 500,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(errorResponse),
      };
    } else {
      return errorResponse;
    }

  } finally {
    if (dbUtil) {
      await dbUtil.closeConnection();
    }
  }
};

// ============================================================================
// ACTION HANDLERS
// ============================================================================

async function handleRegistration(knex: any, requestData: any[]): Promise<any> {
  const accepted: any[] = [];
  const rejected: any[] = [];

  for (const request of requestData) {
    try {
      console.log(`📦 Processing registration request:`, request);
      
      const validatedRequest = TrackingRequestSchema.parse(request);
      
      console.log(`📝 Registering tracking number: ${validatedRequest.number}, Carrier: ${validatedRequest.carrier || 'auto-detect'}`);
      
      // Check if already registered
      const existing = await knex('tracking_simulator')
        .where('tracking_number', validatedRequest.number)
        .first();

      if (existing) {
        accepted.push({
          number: validatedRequest.number,
          carrier: existing.carrier_code,
          carrier_name: existing.carrier_name,
          param: null,
          tag: "",
        });
        continue;
      }

      // Assign random scenario and carrier
      const scenario = getRandomScenario(validatedRequest.carrier);
      const now = new Date();

      // Create simulated tracking entry
      await knex('tracking_simulator').insert({
        tracking_number: validatedRequest.number,
        carrier_code: scenario.carrier,
        carrier_name: scenario.carrier_name,
        scenario: scenario.name,
        registered_at: now,
        current_event_index: 0,
        status: 'active',
        created_at: now,
        updated_at: now,
      });

      accepted.push({
        number: validatedRequest.number,
        carrier: scenario.carrier,
        carrier_name: scenario.carrier_name,
        param: null,
        tag: "",
      });

      console.log(`📝 Registered ${validatedRequest.number} with scenario: ${scenario.name} (completes in ~${scenario.estimated_delivery_minutes} minutes)`);

    } catch (error) {
      console.error(`❌ Registration error for ${request?.number || 'unknown'}:`, error);
      rejected.push({
        number: request?.number || 'unknown',
        error: {
          code: 4003,
          message: error instanceof z.ZodError ? `Validation failed: ${error.errors.map(e => e.message).join(', ')}` : 'Invalid tracking number format',
        },
      });
    }
  }

  return {
    code: 0,
    msg: 'Success',
    data: { accepted, rejected },
  };
}

async function handleGetTrackingInfo(knex: any, requestData: any[]): Promise<any> {
  const accepted: any[] = [];
  const rejected: any[] = [];

  for (const request of requestData) {
    try {
      const validatedRequest = TrackingRequestSchema.parse(request);
      
      // Get simulated tracking data
      const simulatedTracking = await knex('tracking_simulator')
        .where('tracking_number', validatedRequest.number)
        .first();

      if (!simulatedTracking) {
        rejected.push({
          number: validatedRequest.number,
          error: {
            code: 4004,
            message: 'Tracking number not found',
          },
        });
        continue;
      }

      // Generate track_info based on current state
      const trackInfo = await generateTrackingInfo(knex, simulatedTracking);

      accepted.push({
        number: validatedRequest.number,
        carrier: simulatedTracking.carrier_code,
        carrier_name: simulatedTracking.carrier_name,
        param: null,
        tag: "",
        track_info: trackInfo,
      });

      console.log(`📊 Generated tracking info for ${validatedRequest.number}: ${trackInfo.tracking?.providers?.[0]?.events?.length || 0} events`);

    } catch (error) {
      console.error(`❌ Tracking info error for ${request?.number || 'unknown'}:`, error);
      rejected.push({
        number: request?.number || 'unknown',
        error: {
          code: 4005,
          message: 'Failed to retrieve tracking information',
        },
      });
    }
  }

  return {
    code: 0,
    msg: 'Success',
    data: { accepted, rejected },
  };
}

async function handleDeleteTracking(knex: any, requestData: any[]): Promise<any> {
  const accepted: any[] = [];
  const rejected: any[] = [];

  for (const request of requestData) {
    try {
      const trackingNumber = request.number;
      
      // Delete simulated tracking
      const deletedCount = await knex('tracking_simulator')
        .where('tracking_number', trackingNumber)
        .del();

      if (deletedCount > 0) {
        accepted.push({
          number: trackingNumber,
        });
        console.log(`🗑️ Deleted tracking simulation for ${trackingNumber}`);
      } else {
        rejected.push({
          number: trackingNumber,
          error: {
            code: 4004,
            message: 'Tracking number not found',
          },
        });
      }

    } catch (error) {
      console.error(`❌ Delete error for ${request?.number || 'unknown'}:`, error);
      rejected.push({
        number: request?.number || 'unknown',
        error: {
          code: 4006,
          message: 'Failed to delete tracking number',
        },
      });
    }
  }

  return {
    code: 0,
    msg: 'Success',
    data: { accepted, rejected },
  };
}

// ============================================================================
// SIMULATION LOGIC
// ============================================================================

async function generateTrackingInfo(knex: any, simulatedTracking: SimulatedTracking): Promise<any> {
  const scenario = TRACKING_SCENARIOS.find(s => s.name === simulatedTracking.scenario);
  if (!scenario) {
    throw new Error(`Scenario ${simulatedTracking.scenario} not found`);
  }

  const now = new Date();
  const minutesSinceRegistration = (now.getTime() - simulatedTracking.registered_at.getTime()) / (1000 * 60);

  console.log(`⏰ Minutes since registration: ${minutesSinceRegistration.toFixed(1)} for ${simulatedTracking.tracking_number}`);

  // Determine which events should be visible now
  const visibleEvents = scenario.events.filter(event => 
    event.delay_minutes <= minutesSinceRegistration
  );

  console.log(`👁️ Visible events: ${visibleEvents.length}/${scenario.events.length} for ${simulatedTracking.tracking_number}`);

  // Update current event index if needed
  const newEventIndex = visibleEvents.length - 1;
  if (newEventIndex > simulatedTracking.current_event_index) {
    await knex('tracking_simulator')
      .where('id', simulatedTracking.id)
      .update({
        current_event_index: Math.max(newEventIndex, 0),
        updated_at: now,
      });
    console.log(`📈 Updated event index to ${Math.max(newEventIndex, 0)} for ${simulatedTracking.tracking_number}`);
  }

  // Generate events in 17track format
  const events = visibleEvents.map((event, index) => {
    const eventTime = new Date(simulatedTracking.registered_at.getTime() + (event.delay_minutes * 60 * 1000));
    
    return {
      time_utc: eventTime.toISOString(),
      description: event.description,
      location: event.location,
      stage: event.stage,
      sub_status: event.sub_status,
      address: event.address || {
        country: event.location.includes('China') ? 'CN' : event.location.includes('Germany') ? 'DE' : 'IT',
        state: null,
        city: event.location.split(',')[0]?.trim(),
        street: null,
        postal_code: null,
        coordinates: {
          longitude: null,
          latitude: null
        }
      },
    };
  });

  // Determine current status
  const latestEvent = visibleEvents[visibleEvents.length - 1];
  const isCompleted = scenario.completion_type && 
    (latestEvent?.stage === 'Delivered' || 
     latestEvent?.stage === 'Exception' || 
     latestEvent?.stage === 'Expired');

  // Update completion status if needed
  if (isCompleted && simulatedTracking.status === 'active') {
    await knex('tracking_simulator')
      .where('id', simulatedTracking.id)
      .update({
        status: 'completed',
        completion_type: scenario.completion_type,
        updated_at: now,
      });
    console.log(`🏁 Marked ${simulatedTracking.tracking_number} as completed (${scenario.completion_type})`);
  }

  // Generate estimated delivery date
  const estimatedDelivery = new Date(
    simulatedTracking.registered_at.getTime() + 
    (scenario.estimated_delivery_minutes * 60 * 1000)
  );

  // Build 17track compatible response
  const trackInfo = {
    shipping_info: {
      shipper_address: {
        country: "CN",
        state: null,
        city: null,
        street: null,
        postal_code: null,
        coordinates: {
          longitude: null,
          latitude: null
        }
      },
      recipient_address: {
        country: "IT", 
        state: null,
        city: null,
        street: null,
        postal_code: null,
        coordinates: {
          longitude: null,
          latitude: null
        }
      }
    },
    latest_status: {
      status: latestEvent?.stage || 'InfoReceived',
      sub_status: latestEvent?.sub_status || null,
      sub_status_descr: null,
    },
    latest_event: events.length > 0 ? {
      time_iso: events[events.length - 1].time_utc,
      time_utc: events[events.length - 1].time_utc,
      time_raw: {
        date: events[events.length - 1].time_utc.split('T')[0],
        time: events[events.length - 1].time_utc.split('T')[1].replace('Z', ''),
        timezone: null
      },
      description: events[events.length - 1].description,
      location: events[events.length - 1].location,
      stage: events[events.length - 1].stage,
      sub_status: events[events.length - 1].sub_status,
      address: events[events.length - 1].address
    } : null,
    time_metrics: {
      days_after_order: Math.floor(minutesSinceRegistration / (24 * 60)),
      days_of_transit: Math.floor(minutesSinceRegistration / (24 * 60)),
      days_of_transit_done: Math.floor(minutesSinceRegistration / (24 * 60)),
      days_after_last_update: 0,
      estimated_delivery_date: {
        source: null,
        from: estimatedDelivery.toISOString(),
        to: estimatedDelivery.toISOString(),
      },
    },
    milestone: [
      {
        key_stage: "InfoReceived",
        time_iso: events.find(e => e.stage === 'InfoReceived')?.time_utc || null,
        time_utc: events.find(e => e.stage === 'InfoReceived')?.time_utc || null,
        time_raw: {
          date: events.find(e => e.stage === 'InfoReceived')?.time_utc?.split('T')[0] || null,
          time: events.find(e => e.stage === 'InfoReceived')?.time_utc?.split('T')[1]?.replace('Z', '') || null,
          timezone: null
        }
      },
      {
        key_stage: "PickedUp",
        time_iso: events.find(e => e.stage === 'InTransit' && e.sub_status === 'InTransit_PickedUp')?.time_utc || null,
        time_utc: events.find(e => e.stage === 'InTransit' && e.sub_status === 'InTransit_PickedUp')?.time_utc || null,
        time_raw: {
          date: events.find(e => e.stage === 'InTransit' && e.sub_status === 'InTransit_PickedUp')?.time_utc?.split('T')[0] || null,
          time: events.find(e => e.stage === 'InTransit' && e.sub_status === 'InTransit_PickedUp')?.time_utc?.split('T')[1]?.replace('Z', '') || null,
          timezone: null
        }
      },
      {
        key_stage: "Departure",
        time_iso: events.find(e => e.stage === 'InTransit' && e.sub_status === 'InTransit_Departure')?.time_utc || null,
        time_utc: events.find(e => e.stage === 'InTransit' && e.sub_status === 'InTransit_Departure')?.time_utc || null,
        time_raw: {
          date: events.find(e => e.stage === 'InTransit' && e.sub_status === 'InTransit_Departure')?.time_utc?.split('T')[0] || null,
          time: events.find(e => e.stage === 'InTransit' && e.sub_status === 'InTransit_Departure')?.time_utc?.split('T')[1]?.replace('Z', '') || null,
          timezone: null
        }
      },
      {
        key_stage: "Arrival",
        time_iso: events.find(e => e.stage === 'InTransit' && e.sub_status === 'InTransit_Arrival')?.time_utc || null,
        time_utc: events.find(e => e.stage === 'InTransit' && e.sub_status === 'InTransit_Arrival')?.time_utc || null,
        time_raw: {
          date: events.find(e => e.stage === 'InTransit' && e.sub_status === 'InTransit_Arrival')?.time_utc?.split('T')[0] || null,
          time: events.find(e => e.stage === 'InTransit' && e.sub_status === 'InTransit_Arrival')?.time_utc?.split('T')[1]?.replace('Z', '') || null,
          timezone: null
        }
      },
      {
        key_stage: "AvailableForPickup",
        time_iso: events.find(e => e.stage === 'AvailableForPickup')?.time_utc || null,
        time_utc: events.find(e => e.stage === 'AvailableForPickup')?.time_utc || null,
        time_raw: {
          date: events.find(e => e.stage === 'AvailableForPickup')?.time_utc?.split('T')[0] || null,
          time: events.find(e => e.stage === 'AvailableForPickup')?.time_utc?.split('T')[1]?.replace('Z', '') || null,
          timezone: null
        }
      },
      {
        key_stage: "OutForDelivery",
        time_iso: events.find(e => e.stage === 'OutForDelivery')?.time_utc || null,
        time_utc: events.find(e => e.stage === 'OutForDelivery')?.time_utc || null,
        time_raw: {
          date: events.find(e => e.stage === 'OutForDelivery')?.time_utc?.split('T')[0] || null,
          time: events.find(e => e.stage === 'OutForDelivery')?.time_utc?.split('T')[1]?.replace('Z', '') || null,
          timezone: null
        }
      },
      {
        key_stage: "Delivered",
        time_iso: events.find(e => e.stage === 'Delivered')?.time_utc || null,
        time_utc: events.find(e => e.stage === 'Delivered')?.time_utc || null,
        time_raw: {
          date: events.find(e => e.stage === 'Delivered')?.time_utc?.split('T')[0] || null,
          time: events.find(e => e.stage === 'Delivered')?.time_utc?.split('T')[1]?.replace('Z', '') || null,
          timezone: null
        }
      },
      {
        key_stage: "Returning",
        time_iso: events.find(e => e.stage === 'Exception' && e.sub_status === 'Exception_Returning')?.time_utc || null,
        time_utc: events.find(e => e.stage === 'Exception' && e.sub_status === 'Exception_Returning')?.time_utc || null,
        time_raw: {
          date: events.find(e => e.stage === 'Exception' && e.sub_status === 'Exception_Returning')?.time_utc?.split('T')[0] || null,
          time: events.find(e => e.stage === 'Exception' && e.sub_status === 'Exception_Returning')?.time_utc?.split('T')[1]?.replace('Z', '') || null,
          timezone: null
        }
      },
      {
        key_stage: "Returned",
        time_iso: events.find(e => e.stage === 'Exception' && e.sub_status === 'Exception_Returned')?.time_utc || null,
        time_utc: events.find(e => e.stage === 'Exception' && e.sub_status === 'Exception_Returned')?.time_utc || null,
        time_raw: {
          date: events.find(e => e.stage === 'Exception' && e.sub_status === 'Exception_Returned')?.time_utc?.split('T')[0] || null,
          time: events.find(e => e.stage === 'Exception' && e.sub_status === 'Exception_Returned')?.time_utc?.split('T')[1]?.replace('Z', '') || null,
          timezone: null
        }
      }
    ],
    misc_info: {
      risk_factor: 0,
      service_type: null,
      weight_raw: null,
      weight_kg: null,
      pieces: "1",
      dimensions: null,
      customer_number: null,
      reference_number: null,
      local_number: null,
      local_provider: null,
      local_key: 0
    },
    tracking: {
      providers_hash: Math.floor(Math.random() * 2147483647),
      providers: [
        {
          provider: {
            key: simulatedTracking.carrier_code,
            name: simulatedTracking.carrier_name,
            alias: simulatedTracking.carrier_name,
            tel: "+1 (800) 225-5345",
            homepage: "https://www.dhl.com/",
            country: "US"
          },
          provider_lang: null,
          service_type: null,
          latest_sync_status: "Success",
          latest_sync_time: new Date().toISOString(),
          events_hash: Math.floor(Math.random() * 2147483647),
          events: events.map(event => ({
            time_iso: event.time_utc,
            time_utc: event.time_utc,
            time_raw: {
              date: event.time_utc.split('T')[0],
              time: event.time_utc.split('T')[1].replace('Z', ''),
              timezone: null
            },
            description: event.description,
            location: event.location,
            stage: event.stage,
            sub_status: event.sub_status,
            address: event.address || {
              country: event.location.includes('China') ? 'CN' : 'IT',
              state: null,
              city: event.location.split(',')[0]?.trim(),
              street: null,
              postal_code: null,
              coordinates: {
                longitude: null,
                latitude: null
              }
            }
          }))
        }
      ]
    }
  };

  return trackInfo;
}

function getRandomScenario(requestedCarrier?: string | number): TrackingScenario {
  // If carrier is specified, try to match it
  if (requestedCarrier) {
    const carrierCode = typeof requestedCarrier === 'string' 
      ? parseInt(requestedCarrier, 10) 
      : requestedCarrier;
    
    const matchingScenarios = TRACKING_SCENARIOS.filter(s => s.carrier === carrierCode);
    if (matchingScenarios.length > 0) {
      return matchingScenarios[Math.floor(Math.random() * matchingScenarios.length)];
    }
  }

  // Random scenario selection with weights
  const weights = [
    { scenario: 'standard_delivery', weight: 0.7 },  // 70% normal delivery
    { scenario: 'us_to_germany_route', weight: 0.15 }, // 15% US route
    { scenario: 'china_to_germany_dhl', weight: 0.15 }, // 15% China route
  ];

  const random = Math.random();
  let cumulativeWeight = 0;

  for (const weight of weights) {
    cumulativeWeight += weight.weight;
    if (random <= cumulativeWeight) {
      return TRACKING_SCENARIOS.find(s => s.name === weight.scenario) || TRACKING_SCENARIOS[0];
    }
  }

  return TRACKING_SCENARIOS[0]; // fallback
}

export default trackingSimulatorHandler;