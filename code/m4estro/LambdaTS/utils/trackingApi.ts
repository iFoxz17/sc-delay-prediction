import axios, { AxiosInstance, AxiosError } from 'axios';
import { z } from 'zod';

// ============================================================================
// TYPES AND SCHEMAS
// ============================================================================

export const TrackingRequestSchema = z.object({
  number: z.string().min(1),
  carrier: z.union([z.string(), z.number()]).optional(),
  auto_detection: z.boolean().default(true),
});

export const DeleteTrackingResponseSchema = z.object({
  code: z.number(),
  msg: z.string().optional(),
  data: z.union([
    z.object({
      accepted: z.array(z.object({
        number: z.string(),
      })),
      rejected: z.array(z.object({
        number: z.string(),
        error: z.object({
          code: z.number(),
          message: z.string(),
        }),
      })),
    }),
    z.string(),
  ]),
});

export type DeleteTrackingResponse = z.infer<typeof DeleteTrackingResponseSchema>;

export type TrackingRequest = z.infer<typeof TrackingRequestSchema>;

export const RegistrationResponseSchema = z.object({
  code: z.number(),
  msg: z.string().optional(),
  data: z.union([
    z.object({
      accepted: z.array(z.object({
        number: z.string(),
        carrier: z.number().optional(),
        carrier_name: z.string().optional(),
      })),
      rejected: z.array(z.object({
        number: z.string(),
        error: z.object({
          code: z.number(),
          message: z.string(),
        }),
      })),
    }),
    z.string(),
  ]),
});

export type RegistrationResponse = z.infer<typeof RegistrationResponseSchema>;

export const TrackingInfoResponseSchema = z.object({
  code: z.number(),
  msg: z.string().optional(),
  data: z.union([
    z.object({
      accepted: z.array(z.object({
        number: z.string(),
        carrier: z.number().optional(),
        carrier_name: z.string().optional(),
        track_info: z.any().optional(),
      })),
      rejected: z.array(z.object({
        number: z.string(),
        error: z.object({
          code: z.number(),
          message: z.string(),
        }),
      })),
    }),
    z.string(),
  ]),
});

export type TrackingInfoResponse = z.infer<typeof TrackingInfoResponseSchema>;

interface TrackingApiConfig {
  apiKey?: string;
  timeout?: number;
  retries?: number;
}

// ============================================================================
// TRACKING API CLASS
// ============================================================================

export class TrackingApi {
  private readonly apiClient: AxiosInstance;
  private readonly baseUrl = 'https://api.17track.net';
  private readonly config: TrackingApiConfig;
  private apiKey: string | null = null;

  constructor(config: TrackingApiConfig = {}) {
    this.config = {
      timeout: 30000,
      retries: 3,
      ...config,
    };

    this.apiClient = axios.create({
      baseURL: this.baseUrl,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
  }

  private async getApiKey(): Promise<string> {
    if (this.apiKey) return this.apiKey;

    if (this.config.apiKey) {
      this.apiKey = this.config.apiKey;
      return this.apiKey;
    }

    if (process.env.TRACKING_API_KEY) {
      this.apiKey = process.env.TRACKING_API_KEY;
      return this.apiKey;
    }

    throw new Error('17TRACK API key not found. Set TRACKING_API_KEY environment variable.');
  }

  private async getRequestHeaders(): Promise<Record<string, string>> {
    const apiKey = await this.getApiKey();
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      '17token': apiKey,
    };
  }

  private async makeRequest<T>(method: 'GET' | 'POST', endpoint: string, data?: any): Promise<T> {
    const headers = await this.getRequestHeaders();
    
    for (let attempt = 1; attempt <= (this.config.retries || 3); attempt++) {
      try {
        const response = await this.apiClient.request({
          method,
          url: endpoint,
          data,
          headers,
        });

        return response.data;
      } catch (error) {
        if (attempt === this.config.retries) {
          throw this.createTrackingError(error, endpoint);
        }

        const delay = 1000 * Math.pow(2, attempt - 1);
        await this.sleep(delay);
      }
    }

    throw new Error('Max retries exceeded');
  }

  async registerTrackingNumber(trackingInfo: TrackingRequest): Promise<RegistrationResponse> {
    try {
      const processedTrackingInfo = this.processTrackingRequest(trackingInfo);
      
      const response = await this.makeRequest<any>(
        'POST',
        '/track/v2.2/register',
        [processedTrackingInfo]
      );

      let validatedResponse: RegistrationResponse;
      try {
        validatedResponse = RegistrationResponseSchema.parse(response);
      } catch (schemaError) {
        validatedResponse = {
          code: response.code || -1,
          msg: response.msg || 'Schema validation failed',
          data: typeof response.data === 'string' ? response.data : 'Invalid response format'
        };
      }

      if (validatedResponse.code !== 0) {
        const errorMsg = typeof validatedResponse.data === 'string' 
          ? validatedResponse.data 
          : validatedResponse.msg || 'Registration failed';
        throw new Error(`17TRACK API error (${validatedResponse.code}): ${errorMsg}`);
      }

      return validatedResponse;

    } catch (error) {
      console.error(`❌ Registration failed for ${trackingInfo.number}:`, error);
      throw error;
    }
  }

  async getTrackingInfo(trackingInfo: TrackingRequest): Promise<TrackingInfoResponse> {
    try {
      const processedTrackingInfo = this.processTrackingRequest(trackingInfo);
      
      const response = await this.makeRequest<any>(
        'POST',
        '/track/v2.2/getTrackInfo',
        [processedTrackingInfo]
      );

      if (!response || typeof response !== 'object') {
        throw new Error('Invalid response format');
      }

      if (typeof response.code !== 'number') {
        throw new Error('Invalid response format: missing code field');
      }

      if (response.code !== 0) {
        const errorMsg = typeof response.data === 'string' 
          ? response.data 
          : response.msg || 'API returned error code';
        throw new Error(`17TRACK API error (${response.code}): ${errorMsg}`);
      }

      try {
        return TrackingInfoResponseSchema.parse(response);
      } catch (schemaError) {
        return {
          code: response.code,
          msg: response.msg,
          data: response.data || 'No data available'
        } as TrackingInfoResponse;
      }

    } catch (error) {
      console.error(`❌ Failed to get tracking info for ${trackingInfo.number}:`, error);
      throw error;
    }
  }

  async deleteTrackingNumber(trackingInfo: TrackingRequest): Promise<DeleteTrackingResponse> {
    try {
      const processedTrackingInfo = this.processTrackingRequest(trackingInfo);
      
      const response = await this.makeRequest<any>(
        'POST',
        '/track/v2.2/deletetrack',
        [{ number: processedTrackingInfo.number }]
      );

      let validatedResponse: DeleteTrackingResponse;
      try {
        validatedResponse = DeleteTrackingResponseSchema.parse(response);
      } catch (schemaError) {
        validatedResponse = {
          code: response.code || -1,
          msg: response.msg || 'Schema validation failed',
          data: typeof response.data === 'string' ? response.data : 'Invalid response format'
        };
      }

      if (validatedResponse.code !== 0) {
        const errorMsg = typeof validatedResponse.data === 'string' 
          ? validatedResponse.data 
          : validatedResponse.msg || 'Delete failed';
        throw new Error(`17TRACK API error (${validatedResponse.code}): ${errorMsg}`);
      }

      return validatedResponse;

    } catch (error) {
      console.error(`❌ Delete failed for ${trackingInfo.number}:`, error);
      throw error;
    }
  }

  async testConnection(): Promise<boolean> {
    try {
      await this.makeRequest<any>('POST', '/track/v2.2/getCarrierList', {});
      return true;
    } catch (error) {
      return false;
    }
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  private processTrackingRequest(trackingInfo: TrackingRequest): any {
    const validatedInput = TrackingRequestSchema.parse({
      number: trackingInfo.number,
      auto_detection: trackingInfo.auto_detection ?? true,
      ...(trackingInfo.carrier && { carrier: trackingInfo.carrier }),
    });

    return {
      ...validatedInput,
      ...(validatedInput.carrier && {
        carrier: typeof validatedInput.carrier === 'string' 
          ? parseInt(validatedInput.carrier, 10) 
          : validatedInput.carrier
      })
    };
  }

  private createTrackingError(error: any, endpoint: string): Error {
    if (axios.isAxiosError(error)) {
      if (error.response) {
        const status = error.response.status;
        const data = error.response.data;
        
        switch (status) {
          case 401:
            return new Error('17TRACK API authentication failed. Check your API key.');
          case 429:
            return new Error('17TRACK API rate limit exceeded. Try again later.');
          case 503:
          case 502:
          case 504:
            return new Error('17TRACK API service temporarily unavailable.');
          default:
            return new Error(`17TRACK API error (${status}): ${data?.msg || 'Unknown error'}`);
        }
      } else if (error.request) {
        return new Error('Failed to connect to 17TRACK API.');
      }
    }

    return new Error(`17TRACK API ${endpoint} failed: ${this.getErrorMessage(error)}`);
  }

  private getErrorMessage(error: any): string {
    if (axios.isAxiosError(error)) {
      if (error.response?.data?.msg) return error.response.data.msg;
      if (error.response?.data?.message) return error.response.data.message;
      if (error.message) return error.message;
    }
    
    if (error instanceof Error) return error.message;
    return String(error);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

export const createTrackingApi = (config?: TrackingApiConfig): TrackingApi => {
  return new TrackingApi(config);
};

export const validateTrackingNumber = (trackingNumber: string): boolean => {
  if (!trackingNumber || trackingNumber.trim().length === 0) {
    return false;
  }

  const trackingRegex = /^[A-Za-z0-9]+$/;
  const trimmed = trackingNumber.trim();
  
  return trimmed.length >= 5 && trimmed.length <= 50 && trackingRegex.test(trimmed);
};

export default TrackingApi;