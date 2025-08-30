// migrations/tables/coreBusinessTables.ts
import { Knex } from 'knex';
import { 
  addBaseFields, 
  addForeignKey, 
  addLocationFields, 
  addTimestampWithTz,
  addCompositeIndex
} from './tableHelpers';

export const createCoreBusinessTables = async (knex: Knex): Promise<void> => {
  // Countries table (no dependencies)
  await knex.schema.createTable('countries', (table) => {
    addBaseFields(table);
    table.string('code', 3).notNullable();
    table.string('name', 100).notNullable();
    table.integer('total_holidays').unsigned().defaultTo(0).notNullable();
    table.integer('weekend_start').unsigned().defaultTo(6).notNullable()
    table.integer('weekend_end').unsigned().defaultTo(7).notNullable();

    table.unique('code', { indexName: 'unique_countries_code' }); // Ensure unique country codes
    table.index('code', 'idx_countries_code');

    table.comment('Countries table.');
  });

  await knex.schema.createTable('locations', (table) => {
    addBaseFields(table);
    table.string('name', 255).notNullable();
    table.string('city', 100).notNullable();
    table.string('state', 100).nullable();
    addForeignKey(table, 'country_code', 'countries', 'code', false, 'string', 3);
    addLocationFields(table);

    table.unique('name', { indexName: 'unique_locations_name' }); // Ensure unique location names
    table.index('name', 'idx_locations_name');

    table.comment('Locations table to identify univocally locations across the system.');
  });


  // Manufacturers table (depends on locations)
  await knex.schema.createTable('manufacturers', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'location_name', 'locations', 'name', false, 'string');
    table.string('name', 255).notNullable();

    table.comment('Manufacturers table - actually only one manufacturer is considered.');
  });

  // Suppliers table (simplified - no dependencies on manufacturers/locations)
  await knex.schema.createTable('suppliers', (table) => {
    addBaseFields(table);
    table.integer('manufacturer_supplier_id').unsigned().unique().notNullable().comment('Unique ID for the supplier given by the user.');
    table.string('name', 255).notNullable();

    table.comment('Suppliers table - each supplier can have multiple sites.');
  });

  // Sites table (links suppliers to locations with performance metrics)
  await knex.schema.createTable('sites', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'supplier_id', 'suppliers');
    addForeignKey(table, 'location_name', 'locations', 'name', false, 'string');
    table.integer('n_rejections').unsigned().defaultTo(0).notNullable();
    table.integer('n_orders').unsigned().defaultTo(0).notNullable();
  
    table.boolean('consider_closure_holidays').defaultTo(true).notNullable().comment('Whether to consider closure holidays for this site');
    table.boolean('consider_working_holidays').defaultTo(true).notNullable().comment('Whether to consider working holidays on weekends for this site');
    table.boolean('consider_weekends_holidays').defaultTo(true).notNullable().comment('Whether to consider weekends as closure for this site');
    
    addCompositeIndex(table, ['supplier_id', 'location_name']);
    table.unique(['supplier_id', 'location_name'], { indexName: 'unique_sites_supplier_location' }); // Ensure unique sites per supplier and location

    table.comment('Sites table - contains supplier sites information.');
  });

  // Carriers table (no dependencies)
  await knex.schema.createTable('carriers', (table) => {
    addBaseFields(table);
    table.string('name', 100).notNullable();
    table.string('carrier_17track_id', 100).nullable().comment('Unique ID for the carrier given by the 17track.');
    table.integer('n_losses').unsigned().defaultTo(0).notNullable();
    table.integer('n_orders').unsigned().defaultTo(0).notNullable();

    table.unique('carrier_17track_id', { indexName: 'unique_carriers_17track_id' }); // Ensure unique carrier IDs from 17track
    table.unique('name', { indexName: 'unique_carriers_name' }); // Ensure unique carrier names

    table.comment('Carriers table.');
  });

 // Orders table (depends on sites, manufacturers, carriers)
  await knex.schema.createTable('orders', (table) => {
    addBaseFields(table);
    
    addForeignKey(table, 'manufacturer_id', 'manufacturers');
    table.integer('manufacturer_order_id').unsigned().notNullable().comment('ID for the order given by the manufacturer. There could be multiple orders with the same manufacturer_order_id.');
    addForeignKey(table, 'site_id', 'sites');    
    addForeignKey(table, 'carrier_id', 'carriers');
    
    table.string('status', 100).notNullable();    
    table.string('sub_status', 100).nullable().comment('17track sub-status for granular tracking details');
    // Exception details for SLS cases
    table.text('exception_details').nullable().comment('Detailed exception information for SLS scenarios');
    // Completion type for better categorization
    table.enum('completion_type', ['DELIVERED', 'EXCEPTION', 'RETURNED', 'EXPIRED']).nullable().comment('Type of order completion');
    
    table.integer('n_steps').unsigned().defaultTo(0);
    table.text('tracking_link').nullable();
    table.string('tracking_number', 100).notNullable()
    
    // Manufacture timestamps
    addTimestampWithTz(table, 'manufacturer_creation_timestamp', false);
    addTimestampWithTz(table, 'manufacturer_estimated_delivery_timestamp', true);
    addTimestampWithTz(table, 'manufacturer_confirmed_delivery_timestamp', true);
    
    // Carrier timestamps
    addTimestampWithTz(table, 'carrier_creation_timestamp', true);
    addTimestampWithTz(table, 'carrier_estimated_delivery_timestamp', true);
    addTimestampWithTz(table, 'carrier_confirmed_delivery_timestamp', true);
    
    table.boolean('SLS').defaultTo(false).notNullable(); // Shipment Loss Status
    table.boolean('SRS').defaultTo(false).notNullable(); // Shipment Reorder Status

    table.comment('Orders table.');
  });

   // Order Steps table
   await knex.schema.createTable('order_steps', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'order_id', 'orders');
    table.integer('step').unsigned().notNullable();
    table.string('status', 100).notNullable();
    table.string('sub_status', 100).nullable().comment('17track sub-status for step-level tracking details');
    // Enhanced status description with better formatting
    table.text('enhanced_description').nullable().comment('Enhanced description with sub-status and SLS information');
    
    table.string('status_description', 255).notNullable();
    addLocationFields(table);
    addTimestampWithTz(table, 'timestamp', false);
    table.string('location', 100).notNullable();

    table.comment('Order Steps table - tracks the events of each order with statues, timestamps and not uniformed locations.');
  });


  // Order Steps Enriched table
  await knex.schema.createTable('order_steps_enriched', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'order_id', 'orders');
    
    // Source information
    table.integer('step_source').unsigned().notNullable();
    addTimestampWithTz(table, 'timestamp_source', false);
    addForeignKey(table, 'location_name_source', 'locations', 'name', false, 'string');
    
    // Destination information
    table.integer('step_destination').unsigned().notNullable();
    addTimestampWithTz(table, 'timestamp_destination', false);
    addForeignKey(table, 'location_name_destination', 'locations', 'name', false, 'string');
    
    // Distance, time and traffic metrics
    table.decimal('hours', 8, 2).notNullable();
    table.decimal('geodesic_km', 10, 2).notNullable();
    table.decimal('distance_road_km', 10, 2).notNullable();
    table.decimal('time_road_no_traffic_hours', 8, 2).notNullable();
    table.decimal('time_road_traffic_hours', 8, 2).notNullable();

    table.unique(['order_id', 'step_source'], { indexName: 'unique_order_steps_enriched' }); // Ensure unique order steps enriched per order and step source

    table.comment('Order Steps Enriched table - contains validated and enriched information about each pair of order steps (only delivered orders).');
  });


  await knex.schema.createTable('vertices', (table) => {
    addBaseFields(table);
    table.string('name', 100).notNullable();
    table.enum('type', ['SUPPLIER_SITE', 'INTERMEDIATE', 'MANUFACTURER']).notNullable();

    table.unique(['name', 'type'], { indexName: 'unique_vertices_name_type' }); // Ensure unique vertices by name and type

    table.comment('Vertices table - contains all the vertices of the supply chain graph.'); 
  });


  // Routes table (depends on locations)
  await knex.schema.createTable('routes', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'source_id', 'vertices');
    addForeignKey(table, 'destination_id', 'vertices');

    addCompositeIndex(table, ['source_id', 'destination_id']);
    table.unique(['source_id', 'destination_id'], { indexName: 'unique_routes_source_destination' }); // Ensure unique routes

    table.comment('Routes table - contains all the edges of the supply chain graph.');
  });


  // Route Orders table (depends on vertices, routes and orders)
  await knex.schema.createTable('route_orders', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'source_id', 'vertices');
    addForeignKey(table, 'destination_id', 'vertices');
    addForeignKey(table, 'order_id', 'orders');

    addCompositeIndex(table, ['source_id', 'destination_id', 'order_id']);
    table.unique(['source_id', 'destination_id', 'order_id'], { indexName: 'unique_route_orders' }); // Ensure unique route orders

    table.comment('Route Orders table - contains the orders associated with each route in the supply chain graph.');
  });
};

  export const tables = [
    'route_orders',
    'routes',
    'vertices',
    'orders',
    'order_steps_enriched',
    'order_steps',
    'sites',
    'carriers',
    'suppliers',
    'manufacturers',
    'locations',
    'countries'
  ];

export const dropCoreBusinessTables = async (knex: Knex): Promise<void> => {
  for (const tableName of tables) {
   
      await knex.raw(`DROP TABLE IF EXISTS ${tableName} CASCADE;`);
    }
};