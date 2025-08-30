// src/services/LocationService.ts
import { Knex } from 'knex';
import axios, { AxiosInstance } from 'axios';
import { z } from 'zod';

// ============================================================================
// TYPES AND INTERFACES
// ============================================================================

interface LocationRequest {
  latitude?: number;
  longitude?: number;
  city?: string;
  country?: string;
  address?: string;
}

interface LocationServiceResult {
  data: LocationData | null;
  source: 'cache' | 'api';
}


export interface LocationData {
  name: string;
  city: string;
  state?: string;
  country: string;
  country_code: string;
  latitude: number;
  longitude: number;
}


const GeoNamesResponseSchema = z.object({
  geonames: z.array(
    z.object({
      name: z.string(),
      adminName1: z.string().optional(),
      countryName: z.string(),
      countryCode: z.string(),
      lat: z.string(),
      lng: z.string()
    })
  ).min(1, "No location data found")
});
 
const LocationDataSchema = z.object({
  name: z.string(),
  city: z.string(),
  state: z.string(),
  country: z.string(),
  country_code: z.string(),
  latitude: z.number(),
  longitude: z.number()
});

// ============================================================================
// LOCATION SERVICE CLASS
// ============================================================================

export class LocationService {
  private readonly geonamesApiUrl = 'http://api.geonames.org';
  private readonly geonamesUsername = process.env.GEONAMES_USERNAME || 'ifoxz18';
  private readonly apiClient: AxiosInstance;
  private readonly cacheExpiry = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds

  constructor(private knex: Knex) {
    this.apiClient = axios.create({
      timeout: 8000,
      headers: {
        'User-Agent': 'TrackingSystem/1.0',
      },
    });
  }

  /**
   * Get location information with database-first caching
   */
  async getLocationInfo(
    request: LocationRequest, 
  ): Promise<LocationServiceResult> {
    try {
      console.log('🌍 Processing location request:', {
        coordinates: request.latitude && request.longitude ? 
          `${request.latitude},${request.longitude}` : undefined,
        city: request.city,
        address: request.address,
      });

      // Validate request
      if (!this.isValidRequest(request)) {
        throw new Error('Invalid location request - provide coordinates, city, or address');
      }

      // Check cache first (unless skipped or forced refresh)
     
        // const cachedData = await this.getCachedLocationData(request);
        // if (cachedData) {
        //   console.log('✅ Location data retrieved from cache');
        //   return {
        //     data: cachedData,
        //     cached: true,
        //     source: 'cache',
        //   };
        // }
      //console.log('❌ No cached location data found, fetching from API');
      
      
      // Fetch from API
      console.log('🌐 Fetching location data from GeoNames API');
      const apiData = await this.fetchFromGeoNamesApi(request);
      
      if (apiData === null) {
        return {
          data: null,
          source: 'api',
        };
      }

      // Cache the result
      //await this.cacheLocationData(apiData);

      return {
        data: apiData,
        source: 'api',
      };

    } catch (error) {
      console.error('❌ Error in location service:', error);
      return {
        data: null,
        source: 'api',
      };
    }
  }

  // /**
  //  * Get cached location data from database
  //  */
  // private async getCachedLocationData(request: LocationRequest): Promise<LocationData | null> {
  //   try {
  //     const timeWindow = this.cacheExpiry;
  //     const now = new Date();
  //     const cacheThreshold = new Date(now.getTime() - timeWindow);

  //     let query = this.knex('locations')
  //       .leftJoin('countries', 'locations.country_code', 'countries.code')
  //       .select([
  //         'locations.*',
  //         'countries.name as country_name'
  //       ])
  //       .where('locations.updated_at', '>=', cacheThreshold);

  //     // Search by coordinates (with tolerance)
  //     if (request.latitude && request.longitude) {
  //       const tolerance = 0.01; // ~1km tolerance
  //       query = query
  //         .whereBetween('locations.latitude', [
  //           request.latitude - tolerance,
  //           request.latitude + tolerance
  //         ])
  //         .whereBetween('locations.longitude', [
  //           request.longitude - tolerance,
  //           request.longitude + tolerance
  //         ]);
  //     }
  //     // Search by city name
  //     else if (request.city) {
  //       query = query.whereRaw('LOWER(locations.city) = ?', [request.city.toLowerCase()]);
        
  //       if (request.country) {
  //         query = query.whereRaw('LOWER(countries.name) = ?', [request.country.toLowerCase()]);
  //       }
  //     }
  //     // Search by address/name
  //     else if (request.address) {
  //       query = query.whereRaw('LOWER(locations.name) LIKE ?', [`%${request.address.toLowerCase()}%`]);
  //     }

  //     const cachedRecord = await query.first();

  //     if (cachedRecord) {
  //       return {
  //         name: cachedRecord.name,
  //         city: cachedRecord.city,
  //         state: cachedRecord.state,
  //         country: cachedRecord.country_name || cachedRecord.country,
  //         country_code: cachedRecord.country_code,
  //         latitude: parseFloat(cachedRecord.latitude),
  //         longitude: parseFloat(cachedRecord.longitude),
  //       };
  //     }

  //     return null;

  //   } catch (error) {
  //     console.error('❌ Error retrieving cached location data:', error);
  //     return null;
  //   }
  // }

  /**
   * Fetch location data from GeoNames API
   */
  private async fetchFromGeoNamesApi(request: LocationRequest): Promise<LocationData | null> {
    try {
      // Use coordinates if available
      if (request.latitude && request.longitude) {
        return await this.fetchByCoordinates(request.latitude, request.longitude);
      }

      // Use city name
      if (request.city) {
        return await this.fetchByCity(request.city, request.country);
      }

      // Use address
      if (request.address) {
        return await this.fetchByAddress(request.address);
      }

      throw new Error('Insufficient location data provided');

    } catch (error) {
      console.error('❌ Error fetching from GeoNames API:', error);
      return null;
    }
  }

  /**
   * Fetch location by coordinates
   */ 
private async fetchByCoordinates(lat: number, lng: number): Promise<LocationData | null> {
  try {
    const url = `${this.geonamesApiUrl}/findNearbyPlaceNameJSON`;
    const params = {
      lat: lat.toString(),
      lng: lng.toString(),
      username: this.geonamesUsername
    };
 
    const response = await this.apiClient.get(url, { params });
    console.log('🌐 Raw Response Data:', JSON.stringify(response.data, null, 2));
 
    // Validate response structure using Zod
    const validationResult = GeoNamesResponseSchema.safeParse(response.data);
    if (!validationResult.success) {
      console.error('❌ Invalid response structure:', validationResult.error.issues);
      console.error('❌ Received data:', response.data);
      throw new Error(`Invalid response from GeoNames API: ${validationResult.error.message}`);
    }
 
    const data = validationResult.data.geonames[0];
    console.log('🌍 Location data fetched by coordinates:', data);
 
    const locationData: LocationData = {
      name: `${data.name}, ${data.adminName1 || 'UNKNOWN'}, ${data.countryCode}`.toUpperCase(),
      city: data.name.toUpperCase(),
      state: (data.adminName1 || "UNKNOWN").toUpperCase(),
      country: data.countryName.toUpperCase(),
      country_code: data.countryCode.toUpperCase(),
      latitude: lat,
      longitude: lng,
    };
 
    // Validate final location data structure
    const locationValidation = LocationDataSchema.safeParse(locationData);
    if (!locationValidation.success) {
      console.error('❌ Invalid location data structure:', locationValidation.error.issues);
      throw new Error('Failed to create valid location data object');
    }
 
    return locationData;
 
  } catch (error) {
    if (axios.isAxiosError(error)) {
      console.error('❌ Axios error fetching location by coordinates:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        message: error.message
      });
    } else {
      console.error('❌ Error fetching location by coordinates:', error);
    }
    return null;
  }
}

  /**
   * Fetch location by city name
   */
  private async fetchByCity(city: string, country?: string): Promise<LocationData | null> {
    try {
      const searchQuery = country ? `${city}, ${country}` : city;
      
      const response = await this.apiClient.get(
        `${this.geonamesApiUrl}/searchJSON`,
        {
          params: {
            q: searchQuery,
            maxRows: 1,
            username: this.geonamesUsername,
            featureClass: 'P', // Populated places
          }
        }
      );

      console.log('🌐 Request URL:', response.config.url);

      if (!response.data?.geonames?.length) {
        throw new Error('No location found for city');
      }

      const location = response.data.geonames[0];
      console.log('🌍 Location data fetched by city:', location);
      return {
        name: `${location.name}, ${location.adminName1 || "UNKNOWN"}, ${location.countryCode}`.toUpperCase(),
        city: location.name.toUpperCase(),
        state: (location.adminName1 || "UNKNOWN").toUpperCase(),
        country: location.countryName.toUpperCase(),
        country_code: location.countryCode.toUpperCase(),
        latitude: parseFloat(location.lat),
        longitude: parseFloat(location.lng),
      };

    } catch (error) {
      console.error('❌ Error fetching location by city:', error);
      return null;
    }
  }

  /**
   * Fetch location by address
   */
  private async fetchByAddress(address: string): Promise<LocationData | null> {
    try {
      // For address search, we'll try the search endpoint with the full address
      const response = await this.apiClient.get(
        `${this.geonamesApiUrl}/searchJSON`,
        {
          params: {
            q: address,
            maxRows: 1,
            username: this.geonamesUsername,
          }
        }
      );

      if (!response.data?.geonames?.length) {
        throw new Error('No location found for address');
      }

      const location = response.data.geonames[0];
      return {
        name: `${location.name}, ${location.countryName}`,
        city: location.name,
        state: location.adminName1 || undefined,
        country: location.countryName,
        country_code: location.countryCode,
        latitude: parseFloat(location.lat),
        longitude: parseFloat(location.lng),
      };

    } catch (error) {
      console.error('❌ Error fetching location by address:', error);
      return null;
    }
  }

  // /**
  //  * Cache location data in database
  //  */
  // private async cacheLocationData(data: LocationData): Promise<void> {
  //   try {
  //     const now = new Date();
      
  //     // Check if location already exists to avoid duplicates
  //     const existing = await this.knex('locations')
  //       .where('name', data.name)
  //       .orWhere(function() {
  //         this.whereRaw('ABS(latitude - ?) < 0.001 AND ABS(longitude - ?) < 0.001', 
  //           [data.latitude, data.longitude]);
  //       })
  //       .first();

  //     if (existing) {
  //       // Update existing record
  //       await this.knex('locations')
  //         .where('id', existing.id)
  //         .update({
  //           name: data.name,
  //           city: data.city,
  //           state: data.state,
  //           country_code: data.country_code,
  //           latitude: data.latitude,
  //           longitude: data.longitude,
  //           updated_at: now,
  //         });
  //       console.log('✅ Location data updated successfully');
  //     } else {
  //       // Ensure country exists
  //       // await this.ensureCountryExists(data.country_code, data.country);

  //       // Insert new location
  //       const locationRecord = {
  //         name: `${data.city}, ${data.state ?? 'Unknown'}, ${data.country}`.toUpperCase(),
  //         city: data.city,
  //         state: data.state,
  //         country_code: data.country_code,
  //         latitude: data.latitude,
  //         longitude: data.longitude,
  //         created_at: now,
  //         updated_at: now,
  //       };

  //       await this.knex('locations').insert(locationRecord);
  //       console.log('✅ Location data cached successfully');
  //     }

  //   } catch (error) {
  //     console.error('❌ Error caching location data:', error);
  //     // Don't throw - we can still return the data even if caching fails
  //   }
  // }

  // /**
  //  * Ensure country exists in the database
  //  */
  // private async ensureCountryExists(countryCode: string, countryName: string): Promise<void> {
  //   try {
  //     const existingCountry = await this.knex('countries')
  //       .where('code', countryCode)
  //       .first();

  //     if (!existingCountry) {
  //       const now = new Date();
  //       await this.knex('countries').insert({
  //         code: countryCode,
  //         name: countryName,
  //         total_holidays: 0,
  //         weekend_start: 6,
  //         weekend_end: 7,
  //         created_at: now,
  //         updated_at: now,
  //       });
  //       console.log(`✅ Created country: ${countryName} (${countryCode})`);
  //     }

  //   } catch (error) {
  //     console.error('❌ Error ensuring country exists:', error);
  //     // Don't throw - this is not critical for the main operation
  //   }
  // }

  /**
   * Validate location request
   */
  private isValidRequest(request: LocationRequest): boolean {
    return !!(
      (request.latitude && request.longitude) ||
      request.city ||
      request.address
    );
  }

  /**
   * Search locations (utility method for autocomplete, etc.)
   */
  async searchLocations(query: string, limit: number = 10): Promise<LocationData[]> {
    try {
      const results = await this.knex('locations')
        .leftJoin('countries', 'locations.country_code', 'countries.code')
        .select([
          'locations.*',
          'countries.name as country_name'
        ])
        .whereRaw('LOWER(locations.name) LIKE ?', [`%${query.toLowerCase()}%`])
        .orWhereRaw('LOWER(locations.city) LIKE ?', [`%${query.toLowerCase()}%`])
        .limit(limit)
        .orderBy('locations.name');

      return results.map(record => ({
        name: record.name,
        city: record.city,
        state: record.state,
        country: record.country_name || record.country,
        country_code: record.country_code,
        latitude: parseFloat(record.latitude),
        longitude: parseFloat(record.longitude),
      }));

    } catch (error) {
      console.error('❌ Error searching locations:', error);
      return [];
    }
  }

//   /**
//    * Clean up old cache entries (utility method)
//    */
//   async cleanupOldCache(): Promise<number> {
//     try {
//       const threshold = new Date(Date.now() - this.cacheExpiry);
//       const deletedCount = await this.knex('locations')
//         .where('updated_at', '<', threshold)
//         .del();

//       console.log(`🧹 Cleaned up ${deletedCount} old location cache entries`);
//       return deletedCount;

//     } catch (error) {
//       console.error('❌ Error cleaning up location cache:', error);
//       return 0;
//     }
//   }
}