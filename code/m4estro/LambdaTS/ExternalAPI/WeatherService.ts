// src/services/WeatherService.ts
import { Knex } from 'knex';
import axios, { AxiosInstance } from 'axios';

import tzLookup from 'tz-lookup';
import { toZonedTime, format } from 'date-fns-tz';

// ============================================================================
// TYPES AND INTERFACES
// ============================================================================

export interface WeatherRequest {
  latitude: number;
  longitude: number;
  timestamp: string;
  location_name?: string;
}

export interface WeatherServiceResult {
  data: WeatherData | null;
  source: 'cache' | 'api';
}

export interface WeatherData {
  weather_codes: string;
  temperature_celsius: number;
  humidity: number;
  wind_speed: number;
  visibility: number;
  resolved_by: 'LOCATION' | 'COORDINATES';
  location?: string;
  resolved_location?: string;
  coordinates: {
    latitude: number;
    longitude: number;
    resolved_latitude: number;
    resolved_longitude: number;
  };
}

export interface BatchWeatherRequest {
  requests: WeatherRequest[];
}

export interface BatchWeatherResponse {
  results: WeatherServiceResult[];
}

interface CacheOptions {
  skipCache?: boolean;
  forceRefresh?: boolean;
}

// ============================================================================
// WEATHER SERVICE CLASS
// ============================================================================

export class WeatherService {
  private readonly visualCrossingApiUrl = 'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline';
  private readonly visualCrossingApiKey = process.env.VISUAL_CROSSING_API_KEY || 'ZV9Q8HXG5474KFZPTNKF3G6RT' || 'D6F73KKLTYGVSMHQDV9ATY2TG';
  private readonly apiClient: AxiosInstance;
  private readonly cacheExpiry = 6 * 60 * 60 * 1000;          // 6 hours in milliseconds
  private readonly cacheCleanup = 30 * 24 * 60 * 60 * 1000;   // 30 days in milliseconds

  constructor(private knex: Knex) {
    this.apiClient = axios.create({
      timeout: 10000,
      headers: {
        'User-Agent': 'TrackingSystem/1.0',
      },
    });
  }

  /**
  * Handle batch weather requests 
  */
  async handleBatchWeatherRequests(
    batchRequest: BatchWeatherRequest,
  ): Promise<BatchWeatherResponse> {
    console.log('🌤️ Processing', batchRequest.requests.length, 'weather requests in parallel');
    
    const results: WeatherServiceResult[] = await Promise.all(
      batchRequest.requests.map(req => this.getWeatherInfo(req))
    );

    return { results };
  }

  /**
  * Get weather information with database-first caching
  */
  async getWeatherInfo(
    request: WeatherRequest
  ): Promise<WeatherServiceResult> {
    try {
      console.log('🌤️ Processing weather request:', {
        coordinates: `${request.latitude},${request.longitude}`,
        location_name: request.location_name,
        timestamp: request.timestamp,
      });

      // Validate coordinates
      if (!this.isValidCoordinates(request)) {
        throw new Error('Invalid coordinates provided');
      }

      // Check cache first
      const cachedData = await this.getCachedWeatherData(request);
      if (cachedData) {
        console.log('✅ Weather data retrieved from cache');
        return {
            data: cachedData,
            source: 'cache',
          };
      }
      console.log('ℹ️ No cached weather data found, fetching from API');

      // Fetch from API
      console.log('🌐 Fetching weather data from Visual Crossing API');
      const apiData = await this.fetchFromVisualCrossingApi(request);
      
      if (apiData === null) {
        return {
          data: null,
          source: 'api',
        };
      }

      // Cache the result
      await this.cacheWeatherData(request, apiData);

      return {
        data: apiData,
        source: 'api',
      };

    } catch (error) {
      console.error('❌ Error in weather service:', error);
      return {
        data: null,
        source: 'api',
      };
    }
  }

  /**
  * Get cached weather data from database
  */
  private async getCachedWeatherData(request: WeatherRequest): Promise<WeatherData | null> {
    try {
      const COORD_TOLERANCE = 0.01; // ~1km tolerance
      const now = new Date();

      // Determine the day range based on request timestamp
      const requestTimestamp = request.timestamp;
      const requestDay = new Date(requestTimestamp);
      const requestDayStart = new Date(requestDay);
      requestDayStart.setHours(0, 0, 0, 0);
      const requestDayEnd = new Date(requestDay);
      requestDayEnd.setHours(23, 59, 59, 999);

      console.log('🔍 Checking cache for weather data:', {
        coordinates: `${request.latitude},${request.longitude}`,
        location_name: request.location_name,
        request_day: requestDay.toISOString(),
      });

      let query = this.knex('weather_data')

      if (request.location_name) { 
        // Try to retrieve cache by location name
       query = query
        .whereRaw(
          '(LOWER(location_name) = LOWER(?) OR LOWER(resolved_location_name) = LOWER(?))',
          [request.location_name, request.location_name]
        )
        .whereBetween('timestamp', [requestDayStart, requestDayEnd]);
          
        // If request is in the future, apply freshness filter
        if (requestDay > now) {
          const cacheThreshold = new Date(now.getTime() - this.cacheExpiry);
          query = query.where('updated_at', '>=', cacheThreshold);
        }

        const cachedRecord = await query.orderBy('updated_at', 'desc').first();
        if (cachedRecord) {
          console.log('✅ Cache hit by location name = ${cachedRecord.location_name} and timestamp = ${cachedRecord.timestamp}');
          return {
            temperature_celsius: parseFloat(cachedRecord.temperature_celsius),
            weather_codes: cachedRecord.weather_codes,
            humidity: parseFloat(cachedRecord.humidity),
            wind_speed: parseFloat(cachedRecord.wind_speed),
            visibility: parseFloat(cachedRecord.visibility),
            resolved_by: cachedRecord.resolved_by,
            location: cachedRecord.location_name,
            resolved_location: cachedRecord.resolved_location_name,
            coordinates: {
              latitude: parseFloat(cachedRecord.latitude),
              longitude: parseFloat(cachedRecord.longitude),
              resolved_latitude: parseFloat(cachedRecord.resolved_latitude),
              resolved_longitude: parseFloat(cachedRecord.resolved_longitude),
            },
          };
        }
      }

      // Try to retrieve cache by coordinates
      query = this.knex('weather_data')
        .whereRaw(
          `(
            (ABS(latitude - ?) < ? AND ABS(longitude - ?) < ?) 
            OR 
            (ABS(resolved_latitude - ?) < ? AND ABS(resolved_longitude - ?) < ?)
          )`,
          [
            request.latitude, COORD_TOLERANCE,
            request.longitude, COORD_TOLERANCE,
            request.latitude, COORD_TOLERANCE,
            request.longitude, COORD_TOLERANCE
          ]
        )
        .whereBetween('timestamp', [requestDayStart, requestDayEnd]);


      // If request is in the future, apply freshness filter
      if (requestDay > now) {
        const cacheThreshold = new Date(now.getTime() - this.cacheExpiry);
        query = query.where('updated_at', '>=', cacheThreshold);
      }

      const cachedRecord = await query.orderBy('updated_at', 'desc').first();

      if (!cachedRecord) {
        console.log('ℹ️ No cached weather data found');
        return null;
      } 

      console.log(`✅ Cache hit by coordinates = (lat=${cachedRecord.latitude}, long=${cachedRecord.longitude}) and timestamp = ${cachedRecord.timestamp}`);

      return {
        temperature_celsius: parseFloat(cachedRecord.temperature_celsius),
        weather_codes: cachedRecord.weather_codes,
        humidity: parseFloat(cachedRecord.humidity),
        wind_speed: parseFloat(cachedRecord.wind_speed),
        visibility: parseFloat(cachedRecord.visibility),
        resolved_by: cachedRecord.resolved_by,
        location: cachedRecord.location_name,
        resolved_location: cachedRecord.resolved_location_name,
        coordinates: {
          latitude: parseFloat(cachedRecord.latitude),
          longitude: parseFloat(cachedRecord.longitude),
          resolved_latitude: parseFloat(cachedRecord.resolved_latitude),
          resolved_longitude: parseFloat(cachedRecord.resolved_longitude),
        },
      };
    } catch (error) {
      console.error('❌ Error retrieving cached weather data:', error);
      return null;
    }
  }


  /**
  * Fetch weather data from Visual Crossing API
  */
  private async fetchFromVisualCrossingApi(request: WeatherRequest, retry: boolean = true): Promise<WeatherData | null> {
    try {
      const requestTime = request.timestamp

      const requestDate: Date = new Date(requestTime);
      const tz = tzLookup(request.latitude, request.longitude);
      if (tz) {
        console.log('🌍 Resolved timezone from coordinates: ', tz)
      } else {
        console.log('🌍 No timezone found for coordinates, defaulting to UTC')
      };
      
      const localRequestDate = tz
        ? toZonedTime(requestDate, tz)
        : requestDate;
      
      const formattedDate = format(localRequestDate, "yyyy-M-d'T'H:m:sX", { timeZone: tz || 'UTC' });
      console.log(`🌍 Formatted request date in local timezone (${tz}): ${formattedDate}`);

      const locationName = request.location_name
      let resolvedBy: 'LOCATION' | 'COORDINATES';

      let location: string;
      if (locationName) {
        console.log(`📍 Location name provided: ${locationName}`);
        location = locationName;
        resolvedBy = 'LOCATION';
      } else {
        console.log(`📍 No location name provided, using coordinates: lat=${request.latitude}, lon=${request.longitude}`);
        location = `${request.latitude},${request.longitude}`;
        resolvedBy = 'COORDINATES';
      }

      const url = `${this.visualCrossingApiUrl}/${location}/${formattedDate}`;
      console.log(`🌐 Fetching weather data from URL: ${url}`);

      const params = {
        unitGroup: 'metric',
        key: this.visualCrossingApiKey,
        include: 'current',
        elements: 'temp,conditions,humidity,windspeed,visibility',
        lang: "id",
        contentType: 'json'
      };

      const response = await this.apiClient.get(url, { params });

      if (!response) {
        console.log('❌ No response from Visual Crossing API');
        return null;
      }

      if (!response.data) {
        console.log('ℹ️ No weather data received from API');
        if (retry) {
          console.log(`📍 Fallback: fetching weather by lat=${request.latitude}, lon=${request.longitude}`);
          const fallback_request: WeatherRequest = {
            latitude: request.latitude,
            longitude: request.longitude,
            timestamp: request.timestamp,
          };
          return this.fetchFromVisualCrossingApi(fallback_request, false);
        }
        return null;
      }

      // Try to get current conditions first, fallback to daily data
      const resolvedLatitude = parseFloat(response.data.latitude);
      const resolvedLongitude = parseFloat(response.data.longitude);
      const resolvedLocation = response.data.resolvedAddress;

      if (!response.data.currentConditions) {
        console.log('ℹ️ No current conditions found in response');
        return null;
      }
      
      let weatherInfo = response.data.currentConditions;
      if (!weatherInfo) {
        console.log('ℹ️ No suitable weather data found in response');
        return null;
      }

      console.info(`🌤️ Weather data retrieved with query cost ${response.data.queryCost}: ${JSON.stringify(weatherInfo)}`);

      const weatherData: WeatherData = {
        temperature_celsius: weatherInfo.temp || 0,
        weather_codes: weatherInfo.conditions || 'Unknown',
        humidity: weatherInfo.humidity || 0,
        wind_speed: weatherInfo.windspeed || 0,
        visibility: weatherInfo.visibility || 0,
        resolved_by: resolvedBy,
        location: locationName,
        resolved_location: resolvedLocation,
        coordinates: {
          latitude: request.latitude,
          longitude: request.longitude,
          resolved_latitude: resolvedLatitude,
          resolved_longitude: resolvedLongitude,
        },
      };

      return weatherData;

    } catch (error) {
      console.error('❌ Error fetching from Visual Crossing API:', error);
      throw error;
    }
  }

  /**
  * Cache weather data in database
  */
  private async cacheWeatherData(request: WeatherRequest, data: WeatherData): Promise<void> {
    try {

      const now = new Date();
      const timestamp = new Date(request.timestamp);

      if (request.location_name) {
        // Check if we already have a record with similar location and timestamp (case-insensitive)
        const existingByLocation = await this.knex('weather_data')
          .whereRaw(
            'LOWER(location_name) = LOWER(?)',
            [request.location_name]
          )
          .whereBetween('timestamp', [
            new Date(timestamp.getTime() - 60 * 60 * 1000), // 1 hour before
            new Date(timestamp.getTime() + 60 * 60 * 1000), // 1 hour after
          ])
          .first();

        if (existingByLocation) {
          console.log('ℹ️ Record with same location (case-insensitive) and similar timestamp already exists');
          return;
        }
      }
       
      // Check if we already have a record with similar coordinates and timestamp
      const existingByCoordinates = await this.knex('weather_data')
        .whereRaw(
          'ABS(latitude - ?) < 0.01 AND ABS(longitude - ?) < 0.01',
          [data.coordinates.latitude, data.coordinates.longitude]
        )
        .whereBetween('timestamp', [
          new Date(timestamp.getTime() - 60 * 60 * 1000),       // 1 hour before
          new Date(timestamp.getTime() + 60 * 60 * 1000),       // 1 hour after
        ])
        .first();

      if (existingByCoordinates) {
        console.log('ℹ️ Record with similar coordinates and timestamp already exists');
        return;
      }

      const cacheRecord = {
          latitude: data.coordinates.latitude,
          longitude: data.coordinates.longitude,
          resolved_latitude: data.coordinates.resolved_latitude,
          resolved_longitude: data.coordinates.resolved_longitude,
          location_name: data.location,
          resolved_location_name: data.resolved_location,
          resolved_by: data.resolved_by,
          timestamp: timestamp,
          weather_codes: data.weather_codes,
          temperature_celsius: data.temperature_celsius,
          humidity: data.humidity,
          wind_speed: data.wind_speed,
          visibility: data.visibility,
          created_at: now,
          updated_at: now,
      };
      
      await this.knex('weather_data').insert(cacheRecord);
      console.log('✅ Weather data cached successfully');
      

    } catch (error) {
      console.error('❌ Error caching weather data:', error);
      // Don't throw - we can still return the data even if caching fails
    }
  }

  /**
   * Validate coordinates
   */
  private isValidCoordinates(request: WeatherRequest): boolean {
    return !!(
      request.latitude >= -90 && request.latitude <= 90 &&
      request.longitude >= -180 && request.longitude <= 180
    );
  }

  // /**
  //  * Get weather statistics for analysis
  //  */
  // async getWeatherStatistics(hours: number = 24): Promise<any> {
  //   try {
  //     const since = new Date(Date.now() - hours * 60 * 60 * 1000);
      
  //     return await this.knex('weather_data')
  //       .where('timestamp', '>=', since)
  //       .select([
  //         this.knex.raw('AVG(temperature_celsius) as avg_temperature'),
  //         this.knex.raw('MIN(temperature_celsius) as min_temperature'),
  //         this.knex.raw('MAX(temperature_celsius) as max_temperature'),
  //         this.knex.raw('COUNT(*) as total_measurements'),
  //         this.knex.raw("COUNT(CASE WHEN weather_codes LIKE '%rain%' THEN 1 END) as rainy_conditions"),
  //         this.knex.raw("COUNT(CASE WHEN weather_codes LIKE '%snow%' THEN 1 END) as snowy_conditions"),
  //       ])
  //       .first();

  //   } catch (error) {
  //     console.error('❌ Error getting weather statistics:', error);
  //     return null;
  //   }
  // }

  // /**
  //  * Clean up old cache entries (utility method)
  //  */
  // async cleanupOldCache(): Promise<number> {
  //   try {
  //     const threshold = new Date(Date.now() - this.cacheExpiry);
  //     const deletedCount = await this.knex('weather_data')
  //       .where('updated_at', '<', threshold)
  //       .where('order_id', 0) // Only delete cache entries, not real order data
  //       .del();

  //     console.log(`🧹 Cleaned up ${deletedCount} old weather cache entries`);
  //     return deletedCount;

  //   } catch (error) {
  //     console.error('❌ Error cleaning up weather cache:', error);
  //     return 0;
  //   }
  // }
}