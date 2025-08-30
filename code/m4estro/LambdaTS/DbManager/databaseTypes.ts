// src/types/databaseTypes.ts (Updated with additional types)
import { Knex } from 'knex';

// Database Schema Type
export interface DatabaseSchema {
  suppliers: Supplier;
  orders: Order;
  carriers: Carrier;
  countries: Country;
  manufacturers: Manufacturer;
  locations: Location;
  routes: Route;
  route_orders: RouteOrder;
  dispatch_times: DispatchTime;
  dispatch_times_gamma: DispatchTimeGamma;
  delivery_times: DeliveryTime;
  delivery_times_gamma: DeliveryTimeGamma;
  dispatch_time_samples: DispatchTimeSample;
  delivery_time_samples: DeliveryTimeSample;
  weather_data: WeatherData;
  order_steps: OrderStep;
  order_steps_enriched: OrderStepEnriched;
  holidays: Holiday;
  estimated_delivery_times: EstimatedDeliveryTime;
  delays: Delay;
  overall_residence_indices: OverallResidenceIndex;
  overall_transit_indices: OverallTransitIndex;
  vertices: Vertex;
}

export type DatabaseOperation =  
  | 'rollback' 
  | 'insert' 
  | 'update'
  | 'delete'
  | 'select'
  | 'truncate'
  | 'health-check';

export interface QueryOptions {
  select?: string[];
  where?: Record<string, any>;
  orderBy?: { column: string; direction: 'asc' | 'desc' };
  limit?: number;
  offset?: number;
  joins?: JoinOptions[];
}

export interface JoinOptions {
  table: string;
  type: 'inner' | 'left' | 'right' | 'full';
  on: { column1: string; column2: string };
}

export interface DatabaseHealth {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  database: string;
  tableCount: number;
  connectionPool: {
    min: number;
    max: number;
    used: number;
    waiting: number;
  };
  error?: string;
}

export interface ValidationError {
  field: string;
  message: string;
  value?: any;
}

export interface DatabaseError extends Error {
  code?: string;
  table?: string;
  operation?: string;
  constraint?: string;
}

// Bulk operations types
export interface BulkOperation {
  type: 'insert' | 'update' | 'delete';
  tableName: string;
  data?: Record<string, any>;
  whereClause?: Record<string, any>;
}

export interface BulkOperationResult {
  operation: string;
  tableName: string;
  recordsAffected: number;
  data: any;
}

export interface BulkRequest {
  operations: BulkOperation[];
  useTransaction?: boolean;
}

export interface BulkResponse {
  success: boolean;
  message: string;
  data: BulkOperationResult[];
  meta: {
    recordsAffected: number;
    executionTime: number;
  };
  timestamp: string;
}

// Pagination types
export interface PaginationRequest {
  page?: number;
  pageSize?: number;
  orderBy?: string;
  direction?: 'asc' | 'desc';
}

export interface PaginationResponse<T = any> {
  data: T[];
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
}

// Table management types
export interface TableInfo {
  tableName: string;
  columnCount: number;
  rowCount: number;
  primaryKey: string[];
  foreignKeys: Array<{
    column: string;
    referencedTable: string;
    referencedColumn: string;
  }>;
  columns?: Array<{
    name: string;
    type: string;
    nullable: boolean;
    default?: string;
  }>;
}

export interface TableStatistics {
  tableName: string;
  exists: boolean;
  rowCount: number;
  size?: string;
  sizeBytes?: number;
  sizeKB: number;
  error?: string;
}

// API Response types
export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  meta?: {
    recordsAffected?: number;
    executionTime?: number;
    pagination?: {
      page: number;
      pageSize: number;
      total: number;
      totalPages: number;
    };
  };
  timestamp: string;
  requestId?: string;
}

export interface ApiErrorResponse {
  success: false;
  error: string;
  message: string;
  details?: any;
  timestamp: string;
  requestId?: string;
}

// Knex Configuration
export type KnexConfig = Knex.Config;
export type Migration = (knex: Knex) => Promise<void>;

// Entity types (from your dataType.ts)
export interface BaseTable {
  id: number;
  created_at: Date;
  updated_at: Date;
}

export interface Supplier extends BaseTable {
  manufacturer_id: number;
  location_id: number;
  name: string;
  total_rejections: number;
  alpha: number;
}

export interface Order extends BaseTable {
  manufacturer_id: number;
  supplier_id: number;
  carrier_id: number;
  status: string;
  total_steps: number;
  tracking_link: string;
  manufacture_creation_timestamp: Date;
  manufacture_estimated_delivery_timestamp: Date | null;
  manufacture_confirmed_delivery_timestamp: Date | null;
  carrier_creation_timestamp: Date | null;
  carrier_estimated_delivery_timestamp: Date | null;
  carrier_confirmed_delivery_timestamp: Date | null;
}

export interface Carrier extends BaseTable {
  name: string;
  total_orders: number;
}

export interface Country extends BaseTable {
  code: string;
  name: string;
  total_holidays: number;
  weekend_start: number;
  weekend_end: number;
}

export interface Manufacturer extends BaseTable {
  location_id: number;
  name: string;
}

export interface Location extends BaseTable {
  name: string;
  city: string;
  state: string | null;
  country_id: number;
  latitude: number;
  longitude: number;
}

export interface Route extends BaseTable {
  source_id: number;
  destination_id: number;
}

export interface RouteOrder extends BaseTable {
  route_id: number;
  order_id: number;
  destination_id: number;
}

export interface DispatchTime extends BaseTable {
  supplier_id: number;
  median: number;
  mean: number;
  std_dev: number;
  n: number;
}

export interface DispatchTimeGamma extends BaseTable {
  supplier_id: number;
  shape: number;
  loc: number;
  scale: number;
  statistic: number;
  critical: number;
  mean: number;
  std_dev: number;
  n: number;
}

export interface DeliveryTime extends BaseTable {
  supplier_id: number;
  carrier_id: number;
  median: number;
  mean: number;
  std_dev: number;
  n: number;
}

export interface DeliveryTimeGamma extends BaseTable {
  supplier_id: number;
  carrier_id: number;
  shape: number;
  loc: number;
  scale: number;
  statistic: number;
  critical: number;
  mean: number;
  std_dev: number;
  n: number;
}

export interface DispatchTimeSample extends BaseTable {
  supplier_id: number;
  median: number;
  mean: number;
  std_dev: number;
  n: number;
}

export interface DeliveryTimeSample extends BaseTable {
  supplier_id: number;
  carrier_id: number;
  median: number;
  mean: number;
  std_dev: number;
  n: number;
}

export interface WeatherData extends BaseTable {
  order_id: number;
  step_source_id: number;
  timestamp_source: Date;
  location_source_id: number;
  step_destination_id: number;
  timestamp_destination: Date;
  location_destination_id: number;
  hours: number;
  geodesic_km: number;
  distance_road_km: number;
  time_years_for_traffic_hours: number;
  time_road_traffic_hours: number;
  description: string;
}

export interface OrderStep extends BaseTable {
  order_id: number;
  step_id: number;
  status: string;
  timestamp: Date;
  location_id: number;
}

export interface OrderStepEnriched extends BaseTable {
  order_id: number;
  step_source_id: number;
  timestamp_source: Date;
  location_source_id: number;
  step_destination_id: number;
  timestamp_destination: Date;
  location_destination_id: number;
  hours: number;
  geodesic_km: number;
  distance_road_km: number;
  time_years_for_traffic_hours: number;
  time_road_traffic_hours: number;
}

export interface Holiday extends BaseTable {
  name: string;
  category: 'WORKING' | 'CLOSURE';
  description: string;
  year: number;
  type: string;
  date: Date;
  month: number;
  year_day: number;
}

export interface EstimatedDeliveryTime extends BaseTable {
  vertex_id: number;
  order_id: number;
  timestamp: Date;
  hours: number;
}

export interface Delay extends BaseTable {
  vertex_id: number;
  order_id: number;
  timestamp: Date;
  hours_lower: number;
  hours_upper: number;
}

export interface OverallTransitIndex extends BaseTable {
  vertex_id: number;
  timestamp: Date;
  hours: number;
}

export interface OverallResidenceIndex extends BaseTable {
  source_id: number;
  destination_id: number;
  timestamp: Date;
  hours: number;
}

export interface Vertex extends BaseTable {
  name: string;
  type: 'SUPPLIER' | 'INTERMEDIATE' | 'MANUFACTURER';
}