// src/types.ts

// Request structure when invoking the Lambda
export interface TrafficRequest {
   source_lat: number;
   source_lon: number;
   dest_lat: number;
   dest_lon: number;
   departure_time?: string;
   arrival_time?: string;
}

  export interface LocationResponse {
    city?: string;
    country?: string;
    latitude?: number;
    longitude?: number;
    error?: any;
    
  }
  export interface LocationRequest {
    lat?: number;
    lon?: number;
    city?: string;
    country?: string;
    datetime?: string;
  }
  
  // TomTom API Response (simplified)
  export interface TrafficResponse {
    lengthInMeters: number;
    travelTimeInSeconds: number;
    trafficDelayInSeconds: number;
    trafficLengthInMeters: number;
    noTrafficTravelTimeInSeconds: number;
    historicTrafficTravelTimeInSeconds: number;
    liveTrafficIncidentsTravelTimeInSeconds: number;
  }
  
  // Visual Crossing API Response (simplified)
  export interface WeatherResponse {
    temperature: number | null;
    conditions: string | null;
  }

  export interface WeatherRequest {
    location: string;
    lat: number;
    lon: number;
    datetime?: string;
  }
  
  // Cache table structure
  export interface CacheItem<T> {
    cache_key: string;
    data: T;
    expiry: number;
    created_at?: Date;
    updated_at?: Date;
  }

  
  // Error response
  export interface ErrorResponse {
    error: string;
    details?: any;
    timestamp?: string;
  }
