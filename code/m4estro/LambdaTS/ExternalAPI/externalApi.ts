// src/functions/externalApi.ts
import { Context } from 'aws-lambda';
import { z } from 'zod';
import { DatabaseUtil } from '../utils/DatabaseUtils';
import { TrafficService, TrafficData } from './TrafficService';
import { WeatherService, BatchWeatherRequest, WeatherData, BatchWeatherResponse, WeatherServiceResult } from './WeatherService';
import { LocationService, LocationData } from './LocationService';

// ============================================================================
// EXTERNAL API HANDLER each service formats its request and response
/*
Traffic Service
Request
  service: 'traffic',
  action: 'get',
  data: {
    source_latitude: number,
    source_longitude: number,
    destination_latitude: number,
    destination_longitude: number,
    departure_time: string, // ISO datetime
    transportation_mode: 'ROAD' | 'AIR' | 'RAIL' | 'SEA'
  }

Response Format:

  success: boolean,
  data: {
    transportation_mode: string,
    distance_km: number,
    travel_time_hours: number,
    traffic_delay_hours: number,
    no_traffic_travel_time_hours: number,
  } | null,
  error?: string,
  source: 'api' | 'cache',
  timestamp: string


Weather Service
Request Format:

  service: 'weather',
  action: 'get',
  data: 
  {
    latitude: number,
    longitude: number,
    timestamp: string,  // ISO datetime
    location_name?: string
  } 
    | 
  [
    {
      latitude: number,
      longitude: number,
      timestamp: string,  // ISO datetime
      location_name?: string
    }, ...
  ]

Response Format:

  success: boolean,
  data: 
    {
      weather_codes: string,
      temperature_celsius: number,
      humidity: number,
      wind_speed: number,
      visibility: number,
      resolved_by: 'LOCATION' | 'COORDINATES';
      location?: string;
      coordinates: {
        latitude: number,
        longitude: number
      }
    } | null
  | 
    [
      {...} | null, 
      ...
    ],
  error?: string,
  source:  'api' | 'cache' | 'api, cache'
  timestamp: string


Location Service
Request Format:

  service: 'location',
  action: 'get',
  data: {
    latitude?: number,
    longitude?: number,
    city?: string,
    country?: string,
    address?: string
  }
  // Must provide either coordinates OR city OR address

Response Format:

  success: boolean,
  data: {
    name: string,
    city: string,
    state?: string,
    country: string,
    country_code: string,
    latitude: number,
    longitude: number
  } | null,
  error?: string,
  source:  'api' | 'cache'
  timestamp: string


Health Check (All Services)
Request Format:

  service: 'traffic' | 'weather' | 'location',
  action: 'health',
  data: {}

Response Format:

  success: boolean,
  data: {
    service: 'external-api',
    database: {
      status: 'healthy' | 'unhealthy',
      database: string,
      timestamp: string
    },
    apis: {
      tomtom: 'available',
      visualcrossing: 'available', 
      geonames: 'available'
    },
    caching: {
      traffic_ttl: '2 hours',
      weather_ttl: '24 hours',
      location_ttl: '7 days'
    }
  } | null,
  error?: string,
  source: 'api',
  timestamp: string
}*/




// ============================================================================
// LAMBDA INVOCATION TYPES
// ============================================================================

interface LambdaInvocationEvent {
  service: 'traffic' | 'weather' | 'location';
  action: 'get' | 'cache' | 'health';
  data: Record<string, any>;
}

export type ExternalApiLambdaEvent = LambdaInvocationEvent;

// ============================================================================
// VALIDATION SCHEMAS FOR SERVICE DATA
// ============================================================================

const TrafficRequestSchema = z.object({
  source_latitude: z.number().min(-90).max(90),
  source_longitude: z.number().min(-180).max(180),
  destination_latitude: z.number().min(-90).max(90),
  destination_longitude: z.number().min(-180).max(180),
  departure_time: z.string().datetime(),
  transportation_mode: z.enum(['ROAD', 'AIR', 'RAIL', 'SEA']).default('ROAD'),
});

const WeatherSingleRequestSchema = z.object({
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  timestamp: z.string().datetime(),
  location_name: z.string().optional(),
});

const WeatherRequestSchema = z.union([
  WeatherSingleRequestSchema,
  z.array(WeatherSingleRequestSchema),
]);

const LocationRequestSchema = z.object({
  latitude: z.number().min(-90).max(90).optional(),
  longitude: z.number().min(-180).max(180).optional(),
  city: z.string().optional(),
  country: z.string().optional(),
  address: z.string().optional(),
}).refine(
  (data) => 
    (data.latitude && data.longitude) || 
    data.city || 
    data.address,
  {
    message: "Either coordinates (lat/lng), city, or address must be provided",
  }
);

// type TrafficRequest = z.infer<typeof TrafficRequestSchema>;
// type WeatherRequest = z.infer<typeof WeatherRequestSchema>;
// type LocationRequest = z.infer<typeof LocationRequestSchema>;

// ============================================================================
// RESPONSE TYPES
// ============================================================================

interface ServiceResponse<T = any> {
  success: boolean;
  data: T | null;
  error?: string;
  source: string        // 'cache' | 'api' | 'api, cache';
  timestamp: string;
  executionTime?: number;
}

// ============================================================================
// MAIN HANDLER - LAMBDA INVOCATION ONLY
// ============================================================================

export const apiCallHandler = async (
  event: ExternalApiLambdaEvent,
  context: Context
): Promise<ServiceResponse> => {
  let dbUtil: DatabaseUtil | null = null;
  const startTime = Date.now();

  // Set Lambda context for proper cleanup
  context.callbackWaitsForEmptyEventLoop = false;

  try {
    console.log('🌐 External API Lambda invoked by:', context.invokedFunctionArn);
    console.log('📝 Request:', JSON.stringify(event, null, 2));
    console.log('⏱️ Remaining time:', context.getRemainingTimeInMillis() + 'ms');

    // Initialize database connection
    dbUtil = DatabaseUtil.fromEnvironment();
    const knex = await dbUtil.getKnex();

    // Handle health check
    if (event.action === 'health') {
      return await handleHealthCheck(dbUtil);
    }

    // Route to appropriate service
    switch (event.service) {
      case 'traffic':
        return await handleTrafficRequest(
          knex,
          event.action,
          event.data
        )

      case 'weather':
        return await handleWeatherRequest(
          knex,
          event.action,
          event.data,
        );

      case 'location':
        return await handleLocationRequest(
          knex,
          event.action,
          event.data,
        );

      default:
        throw new Error(`Unsupported service: ${event.service}`);
    }

  } catch (error) {
    console.error('❌ Error in external API handler:', error);

    return {
      success: false,
      data: null,
      error: error instanceof Error ? error.message : 'Unknown error',
      source: 'api',
      timestamp: new Date().toISOString(),
    };

  } finally {
    const executionTime = Date.now() - startTime;
    console.log(`⏱️ External API Lambda execution time: ${executionTime}ms`);
    
    if (dbUtil) {
      await dbUtil.closeConnection();
    }
  }
};

// ============================================================================
// SERVICE HANDLERS
// ============================================================================

async function handleTrafficRequest(
  knex: any,
  action: string,
  data: any,
  options?: any
): Promise<ServiceResponse<TrafficData>> {
  try {
    const requestData = TrafficRequestSchema.parse(data);

    if (action === 'get') {
      const trafficService = new TrafficService(knex);
      const result = await trafficService.getTrafficInfo(requestData);
      
      return {
        success: true,
        data: result.data,
        source: result.source,
        timestamp: new Date().toISOString(),
      };
    }

    throw new Error(`Unsupported traffic action: ${action}`);

  } catch (error) {
    console.error('❌ Traffic service error:', error);
    return {
      success: false,
      data: null,
      error: error instanceof Error ? error.message : 'Traffic service error',
      source: 'api',
      timestamp: new Date().toISOString(),
    };
  }
}

async function handleWeatherRequest(
  knex: any,
  action: string,
  data: any
): Promise<ServiceResponse<WeatherData | (WeatherData | null)[]>> {
  try {
    const requestData = WeatherRequestSchema.parse(data);

    if (action === 'get') {
      const weatherService = new WeatherService(knex);
      if (Array.isArray(requestData)) {
        console.log('🌤️ Processing batch weather requests:', requestData.length);
        if (requestData.length === 0) {
          return {
            success: true,
            data: [],
            source: 'api',
            timestamp: new Date().toISOString(),
          };
        }

        const batchRequest: BatchWeatherRequest = { requests: requestData };
        const batchResult: BatchWeatherResponse = await weatherService.handleBatchWeatherRequests(batchRequest);
        const batchData: (WeatherData | null)[] = batchResult.results.map((result: WeatherServiceResult) => (result.data));
        const batchSources: Set<string> = new Set(batchResult.results.map((result: WeatherServiceResult) => result.source));

        return {
          success: true,
          data: batchData,
          source: Array.from(batchSources).join(", "),
          timestamp: new Date().toISOString(),
        };
      }

      console.log('🌤️ Processing single weather request:', requestData);
      const result = await weatherService.getWeatherInfo(requestData);
      return {
        success: true,
        data: result.data,
        source: result.source,
        timestamp: new Date().toISOString(),
      };
    }

    throw new Error(`Unsupported weather action: ${action}`);
  } catch (error) {
    console.error('❌ Weather service error:', error);

    return {
      success: false,
      data: null,
      error: error instanceof Error ? error.message : 'Weather service error',
      source: 'api',
      timestamp: new Date().toISOString(),
    };
  }
}

async function handleLocationRequest(
  knex: any,
  action: string,
  data: any
): Promise<ServiceResponse<LocationData>> {
  try {
    const requestData = LocationRequestSchema.parse(data);

    if (action === 'get') {
      const locationService = new LocationService(knex);
      const result = await locationService.getLocationInfo(requestData);
      
      return {
        success: true,
        data: result.data,
        source: result.source,
        timestamp: new Date().toISOString(),
      };
    }

    throw new Error(`Unsupported location action: ${action}`);

  } catch (error) {
    console.error('❌ Location service error:', error);
    return {
      success: false,
      data: null,
      error: error instanceof Error ? error.message : 'Location service error',
      source: 'api',
      timestamp: new Date().toISOString(),
    };
  }
}

// ============================================================================
// HEALTH CHECK
// ============================================================================

async function handleHealthCheck(dbUtil: DatabaseUtil): Promise<ServiceResponse> {
  try {
    console.log('🏥 Performing external API health check');
    
    const dbHealth = await dbUtil.healthCheck();
    const isHealthy = dbHealth.status === 'healthy';

    return {
      success: isHealthy,
      data: {
        service: 'external-api',
        database: dbHealth,
        apis: {
          tomtom: 'available',
          visualcrossing: 'available',
          geonames: 'available',
        },
        caching: {
          traffic_ttl: '2 hours',
          weather_ttl: '24 hours',
          location_ttl: '7 days',
        },
      },
      source: 'api',
      timestamp: new Date().toISOString(),
    };

  } catch (error) {
    console.error('❌ Health check failed:', error);
    return {
      success: false,
      data: null,
      error: error instanceof Error ? error.message : 'Health check failed',
      source: 'api',
      timestamp: new Date().toISOString(),
    };
  }
}

export default apiCallHandler;