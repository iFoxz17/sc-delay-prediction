// migrations/tables/trackingAndWeatherTables.ts
import { Knex } from 'knex';
import { 
  addBaseFields, 
  addForeignKey, 
  addTimestampWithTz,
  addLocationFields,
} from './tableHelpers';

export const createTrackingAndWeatherTables = async (knex: Knex): Promise<void> => {
 
  // Traffic data table
  await knex.schema.createTable('traffic_data', (table) => {
    addBaseFields(table);
    
    table.decimal('source_latitude', 9, 7).notNullable();
    table.decimal('source_longitude', 10, 7).notNullable();
    table.decimal('destination_latitude', 9, 7).notNullable();
    table.decimal('destination_longitude', 10, 7).notNullable();

    addTimestampWithTz(table, 'departure_time', false);
    table.string('transportation_mode', 50).notNullable();

    table.decimal('distance_km', 10, 2).notNullable();
    table.decimal('travel_time_hours', 10, 4).notNullable();
    table.decimal('no_traffic_travel_time_hours', 10, 4).notNullable();
    table.decimal('traffic_delay_hours', 10, 4).notNullable();

    table.comment('Traffic Data table - cache traffic data retrieved from external APIs.');
  });


  // Weather Data table
  await knex.schema.createTable('weather_data', (table) => {
    addBaseFields(table);

    addLocationFields(table);
    table.decimal('resolved_latitude', 9, 7).notNullable();
    table.decimal('resolved_longitude', 10, 7).notNullable();

    table.string('location_name', 100).nullable();
    table.string('resolved_location_name', 100).notNullable();
    table.enum('resolved_by', ['LOCATION', 'COORDINATES']).notNullable();    
    
    addTimestampWithTz(table, 'timestamp', false);
    table.string('weather_codes', 100).notNullable();
    table.decimal('temperature_celsius', 10, 4).notNullable();
    table.decimal('humidity', 10, 4).notNullable();
    table.decimal('wind_speed', 10, 4).notNullable();
    table.decimal('visibility', 10, 4).notNullable();
    
    table.comment('Weather Data table - contains weather data retrieved from external APIs');
  });


  // Order Step Weather Data table
  await knex.schema.createTable('order_step_weather_data', (table) => {
    addBaseFields(table);

    addForeignKey(table, 'order_id', 'orders');
    table.integer('order_step_source').unsigned().notNullable();
    table.foreign(['order_id', 'order_step_source'])
      .references(['order_id', 'step_source'])
      .inTable('order_steps_enriched')
      .onUpdate('CASCADE')
      .onDelete('RESTRICT');
    
    table.integer('interpolation_step').unsigned().notNullable();
    table.decimal('step_distance_km', 10, 2).notNullable();
    addForeignKey(table, 'weather_data_id', 'weather_data');

    table.unique(['order_id', 'order_step_source', 'interpolation_step'], { indexName: 'unique_weather_data_order_step' });

    table.comment('Weather Data table - contains weather information for each pair of order steps (used to compute the WMI).');
  });


   // Traffic Meta Indices (TMI) table
  await knex.schema.createTable('traffic_meta_indices', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'estimated_time_id', 'estimated_times', 'id', true, 'integer', 0, true, null);
    addForeignKey(table, 'source_id', 'vertices');
    addForeignKey(table, 'destination_id', 'vertices');
    addTimestampWithTz(table, 'timestamp', false);
    table.enum('transportation_mode', ['AIR', 'RAIL', 'ROAD', 'SEA']).notNullable();
    table.decimal('value', 8, 7).notNullable();

    table.comment('Traffic Meta Indices table - contains TMI values.');
  });


  // Weather Meta Indices (WMI) table
 await knex.schema.createTable('weather_meta_indices', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'estimated_time_id', 'estimated_times', 'id', true, 'integer', 0, true, null);
    addForeignKey(table, 'source_id', 'vertices');
    addForeignKey(table, 'destination_id', 'vertices');
    addTimestampWithTz(table, 'timestamp', false);
    table.integer('n_interpolation_points').unsigned().notNullable();
    table.decimal('step_distance_km', 10, 2).unsigned().notNullable();
    table.decimal('value', 8, 7).notNullable();

    table.comment('Weather Meta Indices table - contains WMI values.');
  });
};

 export const tables = [
    'traffic_data',
    'weather_data',
    'order_step_weather_data',
    'traffic_meta_indices',
    'weather_meta_indices'
  ];
  
export const dropTrackingAndWeatherTables = async (knex: Knex): Promise<void> => {

  for (const tableName of tables) {
  
      await knex.raw(`DROP TABLE IF EXISTS ${tableName} CASCADE;`);
    }
  
};