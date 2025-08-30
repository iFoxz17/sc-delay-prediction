import { z } from 'zod';



export interface BaseTable {
  id: number;
  created_at: Date;
  updated_at: Date;
}

export const BaseTableSchema = z.object({
  id: z.number(),
  created_at: z.date(),
  updated_at: z.date(),
});

// Core Business Tables
export interface Supplier extends BaseTable {
  manufacturer_id: number;
  location_id: number;
  name: string;
  total_rejections: number;
  alpha: number;
}

export const SupplierSchema = BaseTableSchema.extend({
  manufacturer_id: z.number(),
  location_id: z.number(),
  name: z.string(),
  total_rejections: z.number(),
  alpha: z.number(),
});


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
export const OrderSchema = BaseTableSchema.extend({
  tracking_id: z.string().min(1, 'Tracking ID is required'),
  distributor_name: z.string().min(1, 'Distributor name is required'),
  manufacturer_id: z.number().int().positive().optional(),
  supplier_id: z.number().int().positive().optional(),
  carrier_id: z.number().int().positive().optional(),
  status: z.string().default('InTransit'),
  total_steps: z.number().int().min(0).default(0),
  tracking_link: z.string().url().optional(),
  manufacture_creation_timestamp: z.string().datetime().optional(),
  manufacture_estimated_delivery_timestamp: z.string().datetime().optional().nullable(),
  manufacture_confirmed_delivery_timestamp: z.string().datetime().optional().nullable(),
  carrier_creation_timestamp: z.string().datetime().optional().nullable(),
  carrier_estimated_delivery_timestamp: z.string().datetime().optional().nullable(),
  carrier_confirmed_delivery_timestamp: z.string().datetime().optional().nullable(),
});

export interface Carrier extends BaseTable {
  name: string;
  total_orders: number;
}
export const CarrierSchema = BaseTableSchema.extend({
  name: z.string(),
  total_orders: z.number(),
});

export interface Country extends BaseTable {
  code: string;
  name: string;
  total_holidays: number;
  weekend_start: number;
  weekend_end: number;
}

export const CountrySchema = BaseTableSchema.extend({
  code: z.string(),
  name: z.string(),
  total_holidays: z.number(),
  weekend_start: z.number(),
  weekend_end: z.number(),
});
export interface Manufacturer extends BaseTable {
  location_id: number;
  name: string;
}

export const ManufacturerSchema = BaseTableSchema.extend({
  location_id: z.number(),
  name: z.string(),
});
// Location and Geographic Tables
export interface Location extends BaseTable {
  name: string;
  city: string;
  state: string | null;
  country_id: number;
  latitude: number;
  longitude: number;
}

export const LocationSchema = BaseTableSchema.extend({
  name: z.string(),
  city: z.string(),
  state: z.string().nullable(),
  country_id: z.number(),
  latitude: z.number(),
  longitude: z.number(),
});

export interface Route extends BaseTable {
  source_id: number;
  destination_id: number;
}

export const RouteSchema = BaseTableSchema.extend({
  source_id: z.number(),
  destination_id: z.number(),
});

export interface RouteOrder extends BaseTable {
  route_id: number;
  order_id: number;
  destination_id: number;
}

export const RouteOrderSchema = BaseTableSchema.extend({
  route_id: z.number(),
  order_id: z.number(),
  destination_id: z.number(),
});
// Time-based Tables
export interface DispatchTime extends BaseTable {
  supplier_id: number;
  median: number;
  mean: number;
  std_dev: number;
  n: number;
}

export const DispatchTimeSchema = BaseTableSchema.extend({
  supplier_id: z.number(),
  median: z.number(),
  mean: z.number(),
  std_dev: z.number(),
  n: z.number(),
});
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

export const DispatchTimeGammaSchema = BaseTableSchema.extend({
  supplier_id: z.number(),
  shape: z.number(),
  loc: z.number(),
  scale: z.number(),
  statistic: z.number(),
  critical: z.number(),
  mean: z.number(),
  std_dev: z.number(),
  n: z.number(),
});
export interface DeliveryTime extends BaseTable {
  supplier_id: number;
  carrier_id: number;
  median: number;
  mean: number;
  std_dev: number;
  n: number;
}
export const DeliveryTimeSchema = BaseTableSchema.extend({
  supplier_id: z.number(),
  carrier_id: z.number(),
  median: z.number(),
  mean: z.number(),
  std_dev: z.number(),
  n: z.number(),
});

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
export const DeliveryTimeGammaSchema = BaseTableSchema.extend({
  supplier_id: z.number(),
  carrier_id: z.number(),
  shape: z.number(),
  loc: z.number(),
  scale: z.number(),
  statistic: z.number(),
  critical: z.number(),
  mean: z.number(),
  std_dev: z.number(),
  n: z.number(),
});

// Sample Tables
export interface DispatchTimeSample extends BaseTable {
  supplier_id: number;
  median: number;
  mean: number;
  std_dev: number;
  n: number;
}
export const DispatchTimeSampleSchema = BaseTableSchema.extend({
  supplier_id: z.number(),
  median: z.number(),
  mean: z.number(),
  std_dev: z.number(),
  n: z.number(),
});

export interface DeliveryTimeSample extends BaseTable {
  supplier_id: number;
  carrier_id: number;
  median: number;
  mean: number;
  std_dev: number;
  n: number;
}

export const DeliveryTimeSampleSchema = BaseTableSchema.extend({
  supplier_id: z.number(),
  carrier_id: z.number(),
  median: z.number(),
  mean: z.number(),
  std_dev: z.number(),
  n: z.number(),
});


// Weather and External Data
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
  // The first location, source of every order (events list describes the location of a supplier)
}

export interface WeatherDataEnriched extends BaseTable {
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
// Order Steps
export interface OrderStep extends BaseTable {
  order_id: number;
  step_id: number;
  status: string;
  timestamp: Date;
  location_id: number;
}


export const OrderStepSchema = BaseTableSchema.extend({
  order_id: z.number(),
  status: z.string(),
  status_description: z.string(),
  timestamp: z.date(),
  location: z.string(),
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
});
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

export const OrderStepEnrichedSchema = BaseTableSchema.extend({
  order_id: z.number(),
  step_source_id: z.number(),
  timestamp_source: z.date(),
  location_source_id: z.number(),
  step_destination_id: z.number(),
  timestamp_destination: z.date(),
  location_destination_id: z.number(),
  hours: z.number(),
  geodesic_km: z.number(),
  distance_road_km: z.number(),
  time_years_for_traffic_hours: z.number(),
  time_road_traffic_hours: z.number(),
});
// Holiday Management
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

export const HolidaySchema = BaseTableSchema.extend({
  name: z.string(),
  category: z.enum(['WORKING', 'CLOSURE']),
  description: z.string(),
  year: z.number(),
  type: z.string(),
  date: z.date(),
  month: z.number(),
  year_day: z.number(),
});
// Estimation Tables
export interface EstimatedDeliveryTime extends BaseTable {
  vertex_id: number;
  order_id: number;
  timestamp: Date;
  hours: number;
}

export const EstimatedDeliveryTimeSchema = BaseTableSchema.extend({
  vertex_id: z.number(),
  order_id: z.number(),
  timestamp: z.date(),
  hours: z.number(),
});
export interface Delay extends BaseTable {
  vertex_id: number;
  order_id: number;
  timestamp: Date;
  hours_lower: number;
  hours_upper: number;
}

export const DelaySchema = BaseTableSchema.extend({
  vertex_id: z.number(),
  order_id: z.number(),
  timestamp: z.date(),
  hours_lower: z.number(),
  hours_upper: z.number(),
});
export interface OverallTransitIndex extends BaseTable {
  vertex_id: number;
  timestamp: Date;
  hours: number;
}

export const OverallTransitIndexSchema = BaseTableSchema.extend({
  vertex_id: z.number(),
  timestamp: z.date(),
  hours: z.number(),
});
export interface OverallResidenceIndex extends BaseTable {
  source_id: number;
  destination_id: number;
  timestamp: Date;
  hours: number;
}
export const OverallResidenceIndexSchema = BaseTableSchema.extend({
  source_id: z.number(),
  destination_id: z.number(),
  timestamp: z.date(),
  hours: z.number(),
});

export interface Vertex extends BaseTable {
  name: string;
  type: 'SUPPLIER' | 'INTERMEDIATE' | 'MANUFACTURER';
}

export const VertexSchema = BaseTableSchema.extend({
  name: z.string(),
  type: z.enum(['SUPPLIER', 'INTERMEDIATE', 'MANUFACTURER']),
});

// Overall Transit Index
export interface TrafficMetaIndex extends BaseTable {
  source_id: number;
  destination_id: number;
  timestamp: Date;
  transportation_mode: 'AIR' | 'RAIL' | 'ROAD' | 'SEA';
  value: number;
}

export const TrafficMetaIndexSchema = BaseTableSchema.extend({
  source_id: z.number(),
  destination_id: z.number(),
  timestamp: z.date(),
  transportation_mode: z.enum(['AIR', 'RAIL', 'ROAD', 'SEA']),
  value: z.number(),
});
// Warehouse Management Indicator  
export interface WeatherMetaIndex extends BaseTable {
  source_id: number;
  destination_id: number;
  timestamp: Date;
  interpolation_points: number;
  step_distance_km: number;
  value: number;
}
export const WeatherMetaIndexSchema = BaseTableSchema.extend({
  source_id: z.number(),
  destination_id: z.number(),
  timestamp: z.date(),
  interpolation_points: z.number(),
  step_distance_km: z.number(),
  value: z.number(),
});