// src/utils/logger.ts
import { inspect } from 'util';
import { string } from 'zod';

/**
 * Log levels in ascending order of severity
 */
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  NONE = 4 // Used to disable logging
}

/**
 * Configuration options for the logger
 */
interface LoggerConfig {
  minLevel: LogLevel;
  includeTimestamp: boolean;
  colorize: boolean;
  prettyPrint: boolean;
  maxObjectDepth: number;
  serviceName: string;
  includeRequestId: boolean;
}

/**
 * Default configuration values
 */
const defaultConfig: LoggerConfig = {
  minLevel: process.env.LOG_LEVEL ? 
    (LogLevel[process.env.LOG_LEVEL as keyof typeof LogLevel] || LogLevel.INFO) : 
    (process.env.NODE_ENV === 'production' ? LogLevel.INFO : LogLevel.DEBUG),
  includeTimestamp: true,
  colorize: process.env.NODE_ENV !== 'production',
  prettyPrint: process.env.NODE_ENV !== 'production',
  maxObjectDepth: 5,
  serviceName: process.env.SERVICE_NAME || 'api-aggregator',
  includeRequestId: true
};

// ANSI color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  gray: '\x1b[90m'
};

// Store the request ID for the current execution context
let currentRequestId: string | undefined;

/**
 * Logger class for consistent, structured logging
 */
class Logger {
  private config: LoggerConfig;
  private context: Record<string, any>;
  
  constructor(config: Partial<LoggerConfig> = {}, context: Record<string, any> = {}) {
    this.config = { ...defaultConfig, ...config };
    this.context = context;
  }
  
  /**
   * Set the request ID for the current execution context
   */
  static setRequestId(requestId: string): void {
    currentRequestId = requestId;
  }
  
  /**
   * Get the current request ID
   */
  static getRequestId(): string | undefined {
    return currentRequestId;
  }
  
  /**
   * Clear the request ID when the execution context ends
   */
  static clearRequestId(): void {
    currentRequestId = undefined;
  }
  
  /**
   * Format a log message with optional metadata
   */
  private formatMessage(level: string, message: string, data?: any): string {
    const timestamp = this.config.includeTimestamp ? new Date().toISOString() : undefined;
    
    // Merge context with provided data
    const mergedData = {
      ...this.context,
      ...(data || {})
    };
    
    // Add request ID if enabled and available
    if (this.config.includeRequestId && currentRequestId) {
      mergedData.requestId = currentRequestId;
    }
    
    // Format data objects for better readability
    let formattedData: string | undefined;
    if (Object.keys(mergedData).length > 0) {
      if (this.config.prettyPrint) {
        // For development: readable format with indentation
        formattedData = inspect(mergedData, {
          colors: this.config.colorize,
          depth: this.config.maxObjectDepth,
          breakLength: 100
        });
      } else {
        // For production: compact JSON
        try {
          // Filter out undefined values
          const filteredData = Object.entries(mergedData)
            .filter(([_, value]) => value !== undefined)
            .reduce((obj, [key, value]) => ({ ...obj, [key]: value }), {});
            
          formattedData = JSON.stringify(filteredData);
        } catch (error) {
          formattedData = `[Unserializable data: ${error instanceof Error ? error.message : error}]`;
        }
      }
    }
    
    // Construct the log entry object
    const logEntry: Record<string, any> = {
      level,
      service: this.config.serviceName,
      timestamp,
      message,
      ...mergedData
    };
    
    // For production: return JSON string
    if (!this.config.prettyPrint) {
      return JSON.stringify(logEntry);
    }
    
    // For development: return formatted string
    let colorCode = '';
    switch (level) {
      case 'DEBUG':
        colorCode = colors.gray;
        break;
      case 'INFO':
        colorCode = colors.blue;
        break;
      case 'WARN':
        colorCode = colors.yellow;
        break;
      case 'ERROR':
        colorCode = colors.red;
        break;
    }
    
    // Build the log line
    let logLine = '';
    
    // Add timestamp if enabled
    if (timestamp) {
      logLine += `${colors.gray}${timestamp}${colors.reset} `;
    }
    
    // Add request ID if available
    if (this.config.includeRequestId && currentRequestId) {
      logLine += `${colors.cyan}[${currentRequestId}]${colors.reset} `;
    }
    
    // Add level with color
    logLine += `${colorCode}${level.padEnd(5)}${colors.reset} `;
    
    // Add service name
    logLine += `[${this.config.serviceName}] `;
    
    // Add message
    logLine += message;
    
    // Add data if available
    if (formattedData) {
      logLine += `\n${formattedData}`;
    }
    
    return logLine;
  }
  
  /**
   * Log a message at DEBUG level
   */
  debug(message: string, data?: any): void {
    if (this.config.minLevel <= LogLevel.DEBUG) {
      console.debug(this.formatMessage('DEBUG', message, data));
    }
  }
  
  /**
   * Log a message at INFO level
   */
  info(message: string, data?: any): void {
    if (this.config.minLevel <= LogLevel.INFO) {
      console.info(this.formatMessage('INFO', message, data));
    }
  }
  
  /**
   * Log a message at WARN level
   */
  warn(message: string, data?: any): void {
    if (this.config.minLevel <= LogLevel.WARN) {
      console.warn(this.formatMessage('WARN', message, data));
    }
  }
  
  /**
   * Log a message at ERROR level
   */
  error(message: string, data?: any): void {
    if (this.config.minLevel <= LogLevel.ERROR) {
      console.error(this.formatMessage('ERROR', message, data));
    }
  }
  
  /**
   * Create a child logger with additional context
   */
  child(context: Record<string, any>): Logger {
    return new Logger(
      this.config,
      { ...this.context, ...context }
    );
  }
  
  /**
   * Time an operation and log its duration
   */
  async time<T>(
    message: string, 
    operation: () => Promise<T>, 
    level: LogLevel = LogLevel.INFO
  ): Promise<T> {
    const start = Date.now();
    try {
      const result = await operation();
      const duration = Date.now() - start;
      
      switch (level) {
        case LogLevel.DEBUG:
          this.debug(`${message} completed`, { durationMs: duration });
          break;
        case LogLevel.INFO:
          this.info(`${message} completed`, { durationMs: duration });
          break;
        case LogLevel.WARN:
          this.warn(`${message} completed`, { durationMs: duration });
          break;
        case LogLevel.ERROR:
          this.error(`${message} completed`, { durationMs: duration });
          break;
      }
      
      return result;
    } catch (error) {
      const duration = Date.now() - start;
      this.error(`${message} failed`, { error, durationMs: duration });
      throw error;
    }
  }
  
  /**
   * Update logger configuration
   */
  setConfig(config: Partial<LoggerConfig>): void {
    this.config = { ...this.config, ...config };
  }
  
  /**
   * Set minimum log level
   */
  setLevel(level: LogLevel): void {
    this.config.minLevel = level;
  }
  
  /**
   * Add persistent context to all log messages
   */
  addContext(context: Record<string, any>): void {
    this.context = { ...this.context, ...context };
  }
}

// Create and export the default logger instance
export const logger = new Logger();

// Export utility to create a new logger with custom configuration
export const createLogger = (config: Partial<LoggerConfig> = {}, context: Record<string, any> = {}): Logger => {
  return new Logger(config, context);
};

/**
 * Lambda middleware to set request ID from context
 */
export const loggerMiddleware = (handler: Function) => {
  return async (event: any, context: any) => {
    try {
      // Set request ID from Lambda context
      Logger.setRequestId(context.awsRequestId);
      
      // Log the incoming event
      logger.info('Lambda invocation started', {
        functionName: context.functionName,
        remainingTime: context.getRemainingTimeInMillis(),
        eventType: event.httpMethod ? 'http' : 'event'
      });
      
      // Execute the handler
      const result = await handler(event, context);
      
      // Log successful completion
      logger.info('Lambda invocation completed successfully');
      
      return result;
    } catch (error) {
      // Log the error
      logger.error('Lambda invocation failed', { error });
      
      // Rethrow to allow Lambda error handling
      throw error;
    } finally {
      // Clear request ID to prevent leaking between invocations
      Logger.clearRequestId();
    }
  };
};