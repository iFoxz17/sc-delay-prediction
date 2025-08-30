// src/utils/api-client.ts
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { logger } from './logger';

/**
 * Creates a configured axios instance for API requests
 */
export const createApiClient = (baseURL?: string, options: AxiosRequestConfig = {}): AxiosInstance => {
  // Default configuration for all API requests
  const defaultConfig: AxiosRequestConfig = {
    baseURL,
    timeout: 10000, // 10 second default timeout
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    ...options
  };

  // Create axios instance with configuration
  const apiClient = axios.create(defaultConfig);

  // Add request interceptor for logging
  apiClient.interceptors.request.use(
    (config) => {
      logger.debug('API Request', {
        method: config.method,
        url: config.url,
        params: config.params,
        timeout: config.timeout
      });
      return config;
    },
    (error) => {
      logger.error('API Request Error', { error });
      return Promise.reject(error);
    }
  );

  // Add response interceptor for logging
  apiClient.interceptors.response.use(
    (response) => {
      logger.debug('API Response', {
        status: response.status,
        statusText: response.statusText,
        url: response.config.url,
        size: response.headers['content-length'] || 'unknown'
      });
      return response;
    },
    (error) => {
      if (error.response) {
        // The request was made and the server responded with a non-2xx status
        logger.error('API Response Error', {
          status: error.response.status,
          statusText: error.response.statusText,
          url: error.config?.url,
          data: error.response.data
        });
      } else if (error.request) {
        // The request was made but no response was received
        logger.error('API No Response Error', {
          timeout: error.config?.timeout,
          url: error.config?.url
        });
      } else {
        // Something happened in setting up the request
        logger.error('API Setup Error', { message: error.message });
      }
      return Promise.reject(error);
    }
  );

  return apiClient;
};

/**
 * Retry mechanism for API requests
 * @param apiCall Function making the axios request
 * @param retries Number of retries
 * @param delay Delay between retries in ms
 */
export const withRetry = async <T>(
  apiCall: () => Promise<T>,
  retries = 3,
  delay = 1000
): Promise<T> => {
  try {
    return await apiCall();
  } catch (error) {
    if (retries <= 0) throw error;
    
    logger.warn(`Retrying API call. Attempts left: ${retries - 1}`, { error });
    await new Promise(resolve => setTimeout(resolve, delay));
    
    // Exponential backoff
    return withRetry(apiCall, retries - 1, delay * 2);
  }
};