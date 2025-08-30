// src/services/TrafficService.ts
import { Knex } from 'knex';
import axios, { AxiosInstance } from 'axios';


// ============================================================================
// TYPES AND INTERFACES
// ============================================================================

interface TrafficRequest {
  source_latitude: number;
  source_longitude: number;
  destination_latitude: number;
  destination_longitude: number;
  departure_time: string;
  transportation_mode: string;
}

interface TrafficServiceResult {
  data: TrafficData | null;
  source: 'cache' | 'api';
}

export interface TrafficData {
  transportation_mode: string;
  distance_km: number;
  travel_time_hours: number;
  traffic_delay_hours: number;
  no_traffic_travel_time_hours: number;
}


// ============================================================================
// TRAFFIC SERVICE CLASS
// ============================================================================

export class TrafficService {
  private readonly tomtomApiUrl = 'https://api.tomtom.com/routing/1/calculateRoute';
  private readonly tomtomApiKey = process.env.TOMTOM_API_KEY || 'ZQjQkIjUNMhGapMW1GmG64WYBAzxhYbZ';
  private readonly apiClient: AxiosInstance;
  private readonly cacheExpiry = 6 * 60 * 60 * 1000;          // 6 hours in milliseconds
  private readonly cacheCleanup = 30 * 24 * 60 * 60 * 1000;   // 30 days in milliseconds

  constructor(private knex: Knex) {
    this.apiClient = axios.create({
      timeout: 15000,
      headers: {
        'User-Agent': 'TrackingSystem/1.0',
      },
    });
  }

  /**
   * Get traffic information with database-first caching
   */
  async getTrafficInfo(
    request: TrafficRequest
  ): Promise<TrafficServiceResult> {
    try {
      console.log('🚗 Processing traffic request:', {
        source: `lat=${request.source_latitude}, lon=${request.source_longitude}`,
        destination: `lat=${request.destination_latitude}, lon=${request.destination_longitude}`,
        transportation_mode: request.transportation_mode,
      });

      // Validate coordinates
      if (!this.isValidCoordinates(request)) {
        console.error('❌ Invalid coordinates provided:', request);
        throw new Error('Invalid coordinates provided');
      }

      // Check cache first
      const cachedData = await this.getCachedTrafficData(request);
      if (cachedData) {
        console.log('✅ Traffic data retrieved from cache');
          return {
            data: cachedData,
            source: 'cache',
          };
        }
      

      // Fetch from API
      console.log('🌐 Fetching traffic data from TomTom API');
      const apiData = await this.fetchFromTomTomApi(request);
      
      // Handle case where no route exists
      if (apiData === null) {
        console.log('ℹ️ No road route available - returning null data');
        return {
          data: null,
          source: 'api',
        };
      }

      // Cache the result
      await this.cacheTrafficData(request, apiData);

      return {
        data: apiData,
        source: 'api',
      };

    } catch (error) {
      console.error('❌ Error in traffic service:', error);
      return {
        data: null,
        source: 'api',
      };
    }
  }

 /**
 * Get cached traffic data from database
 */
  private async getCachedTrafficData(request: TrafficRequest): Promise<TrafficData | null> {
    try {
      const COORD_TOLERANCE = 0.001; // ~100m tolerance
      const TIME_TOLERANCE_MS = 30 * 60 * 1000; // 30 minutes
      const now = new Date();

      console.log('🔍 Checking cache for traffic data:', {
        source: `lat=${request.source_latitude}, lon=${request.source_longitude}`,
        destination: `lat=${request.destination_latitude}, lon=${request.destination_longitude}`,
        transportation_mode: request.transportation_mode,
        departure_time: request.departure_time,
      });

      let query = this.knex('traffic_data')
        .whereRaw(
          'ABS(source_latitude - ?) < ? AND ABS(source_longitude - ?) < ?',
          [request.source_latitude, COORD_TOLERANCE, request.source_longitude, COORD_TOLERANCE]
        )
        .whereRaw(
          'ABS(destination_latitude - ?) < ? AND ABS(destination_longitude - ?) < ?',
          [request.destination_latitude, COORD_TOLERANCE, request.destination_longitude, COORD_TOLERANCE]
        )
        .where('transportation_mode', request.transportation_mode);

      if (request.departure_time) {
        const departure = new Date(request.departure_time);
        const timeWindowStart = new Date(departure.getTime() - TIME_TOLERANCE_MS);
        const timeWindowEnd = new Date(departure.getTime() + TIME_TOLERANCE_MS);

        query = query.whereBetween('departure_time', [timeWindowStart, timeWindowEnd]);

        if (departure > now) {
          const cacheThreshold = new Date(now.getTime() - this.cacheExpiry);
          query = query.where('updated_at', '>=', cacheThreshold);
        }
      }

      const cached = await query.orderBy('updated_at', 'desc').first();

      if (!cached) {
        console.log('ℹ️ No cached traffic data found for the given request');
        return null;
      } 

      console.log('✅ Cached traffic data found:', {
        source: `lat=${cached.source_latitude}, lon=${cached.source_longitude}`,
        destination: `lat=${cached.destination_latitude}, lon=${cached.destination_longitude}`,
        transportation_mode: cached.transportation_mode,
      });

      return {
        transportation_mode: cached.transportation_mode,
        distance_km: parseFloat(cached.distance_km),
        travel_time_hours: parseFloat(cached.travel_time_hours),
        no_traffic_travel_time_hours: parseFloat(cached.no_traffic_travel_time_hours),
        traffic_delay_hours: parseFloat(cached.traffic_delay_hours),
      };

    } catch (error) {
      console.error('❌ Error retrieving cached traffic data:', error);
      return null;
    }
  }


  /**
   * Fetch traffic data from TomTom API
   */
  private async fetchFromTomTomApi(request: TrafficRequest): Promise<TrafficData | null> {
    try {
      const url = `${this.tomtomApiUrl}/${request.source_latitude},${request.source_longitude}:${request.destination_latitude},${request.destination_longitude}/json`;
      
      const params: any = {
        key: this.tomtomApiKey,
        traffic: 'true',
        routeType: 'fastest',
        computeTravelTimeFor: 'all',
      };

      // Add departure time if provided
      if (request.departure_time) {
        params.departAt = request.departure_time;
      }

      // Adjust parameters based on transportation mode
      switch (request.transportation_mode) {
        case 'ROAD':
          params.travelMode = 'truck';
          params.vehicleCommercial = 'true';
          break;
        case 'SEA':
          // For sea routes, we might not get good results from road API
          return null;
        default:
          break;
      }

      const response = await this.apiClient.get(url, { params });

      if (!response.data?.routes?.length) {
        console.log(`ℹ️ No route found between coordinates`);
        return null;
      }

      const route = response.data.routes[0];
      const summary = route.summary;

      const trafficData: TrafficData = {
        distance_km: (summary.lengthInMeters || 0) / 1000,
        travel_time_hours: (summary.travelTimeInSeconds || 0) / 3600,
        traffic_delay_hours: (summary.trafficDelayInSeconds || 0) / 3600,
        no_traffic_travel_time_hours: (summary.noTrafficTravelTimeInSeconds || 0) / 3600,
        transportation_mode: request.transportation_mode,
      };

      return trafficData;

    } catch (error) {
      if (this.isNoRouteFoundError(error)) {
        console.log(`ℹ️ No route available between specified locations`);
        return null;
      }

      console.error('❌ Error fetching from TomTom API:', error);
      throw error;
    }
  }

  /**
   * Cache traffic data in database
   */
  private async cacheTrafficData(request: TrafficRequest, data: TrafficData): Promise<void> {
    try {
      const now = new Date();
      
      const cacheRecord = {
        source_latitude: request.source_latitude,
        source_longitude: request.source_longitude,
        destination_latitude: request.destination_latitude,
        destination_longitude: request.destination_longitude,
        departure_time: request.departure_time,
        transportation_mode: request.transportation_mode,
        distance_km: data.distance_km,
        travel_time_hours: data.travel_time_hours,
        no_traffic_travel_time_hours: data.no_traffic_travel_time_hours,
        traffic_delay_hours: data.traffic_delay_hours,
        created_at: now,
        updated_at: now,
      };

      await this.knex('traffic_data').insert(cacheRecord);
      console.log('✅ Traffic data cached successfully');

    } catch (error) {
      console.error('❌ Error caching traffic data:', error);
      // Don't throw - we can still return the data even if caching fails
    }
  }

  /**
   * Validate coordinates
   */
  private isValidCoordinates(request: TrafficRequest): boolean {
    return !!(
      request.source_latitude >= -90 && request.source_latitude <= 90 &&
      request.source_longitude >= -180 && request.source_longitude <= 180 &&
      request.destination_latitude >= -90 && request.destination_latitude <= 90 &&
      request.destination_longitude >= -180 && request.destination_longitude <= 180
    );
  }

  /**
   * Check if error indicates no route was found
   */
  private isNoRouteFoundError(error: any): boolean {
    const noRouteCode = 'NO_ROUTE_FOUND';
    const noRouteMessageIndicators = ['NO_ROUTE_FOUND'];

    const errorMessage = (error.response?.data?.detailedError?.message || 
                         error.response?.data?.message || 
                         error.message || 
                         String(error)).toUpperCase();

    const errorCode = (error.response?.data?.detailedError?.code || 
                        error.response?.data?.code || 
                        error.code || 
                        String(error)).toUpperCase();

    console.log('🔍 Error code:', errorCode, '- Error message:', errorMessage);

    return error.response?.status === 400 && 
           (errorCode === noRouteCode || 
            noRouteMessageIndicators.some(indicator => errorMessage.includes(indicator)));
  }

  /**
   * Clean up old cache entries (utility method)
   */
  async cleanupOldCache(): Promise<number> {
    try {
      const threshold = new Date(Date.now() - this.cacheCleanup);
      const deletedCount = await this.knex('traffic_data')
        .where('updated_at', '<', threshold)
        .del();

      console.log(`🧹 Cleaned up ${deletedCount} old traffic cache entries`);
      return deletedCount;

    } catch (error) {
      console.error('❌ Error cleaning up traffic cache:', error);
      return 0;
    }
  }
}