// migrations/tables/timeBasedTables.ts
import { Knex } from 'knex';
import { 
  addBaseFields, 
  addForeignKey, 
  addSampleFields, 
  addGammaFields,
  addCompositeIndex,
  addTimestampWithTz
} from './tableHelpers';

export const createTimeBasedTables = async (knex: Knex): Promise<void> => {
  // Dispatch Times table
  await knex.schema.createTable('dispatch_times', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'site_id', 'sites');
    table.decimal('hours', 12, 6).notNullable();

    table.comment('Dispatch Times table - contains the measured dispatch times for each site.');
  });

  // Dispatch Time Gammas table
  await knex.schema.createTable('dispatch_time_gammas', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'site_id', 'sites');
    addGammaFields(table);

    table.comment('Dispatch Time Gammas table - contains the parameters of the gamma distributions used to model sites dispatch times.');
  });
 
  // Dispatch Time Samples table
  await knex.schema.createTable('dispatch_time_samples', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'site_id', 'sites');
    addSampleFields(table);

    table.comment('Dispatch Time Samples table - contains statistical measures of the dispatch times samples.');
  });


  // Shipment Times table
  await knex.schema.createTable('shipment_times', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'site_id', 'sites');
    addForeignKey(table, 'carrier_id', 'carriers');
    table.decimal('hours', 12, 6).notNullable();

    table.comment('Shipment Times table - contains the measured shipment times for each site and carrier combination.');
  });

  // Shipment Times Gamma table
  await knex.schema.createTable('shipment_time_gammas', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'site_id', 'sites');
    addForeignKey(table, 'carrier_id', 'carriers');
    addGammaFields(table);

    table.comment('Shipment Times Gamma table - contains the parameters of the gamma distributions used to model shipment times for each site and carrier combination.');
  });

  // Shipment Time Samples table
  await knex.schema.createTable('shipment_time_samples', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'site_id', 'sites');
    addForeignKey(table, 'carrier_id', 'carriers');
    addSampleFields(table);

    table.comment('Shipment Time Samples table - contains statistical measures of the shipment times samples for each site and carrier combination.');
  });

  // Holidays table
  await knex.schema.createTable('holidays', (table) => {
    addBaseFields(table);
    
    table.string('name', 255).notNullable();
    addForeignKey(table, 'country_code', 'countries', 'code', false, 'string', 3);

    table.enum('category', ['WORKING', 'CLOSURE']).notNullable();
    table.text('description').nullable();
    table.text('url').nullable();
    table.string('type', 50).nullable();
    table.date('date').notNullable();
    table.integer('week_day').unsigned().notNullable();
    table.integer('month').unsigned().notNullable();
    table.integer('year_day').unsigned().notNullable();

    table.comment('Holidays table - contains holidays information for each country, including working days and closures.');
  });

  // Global parameters table
  await knex.schema.createTable('params', (table) => {
    addBaseFields(table);
    table.string('name', 50).unique().notNullable();
    table.string('general_category', 50).notNullable();
    table.string('category', 50).notNullable();
    table.text('description').nullable();
    table.decimal('value', 16, 6).notNullable();

    table.comment('Global Parameters table - contains global parameters used in the system, such as thresholds and default confidence levels.');
  });

  // Optimal alphas parameters table
  await knex.schema.createTable('alphas_opt', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'site_id', 'sites');
    addForeignKey(table, 'carrier_id', 'carriers');
    table.decimal('tt_weight', 7, 6).defaultTo(0.5).notNullable();

    table.unique(['site_id', 'carrier_id'], { indexName: 'unique_site_carrier_alphas_opt' });

    table.comment('Optimal alphas table - contains optimal alphas parameters used for the TFST indicator, specific to each site and carrier combination.');
  });

  // Historical alphas parameters table
  await knex.schema.createTable('alphas', (table) => {
    addBaseFields(table);
    table.enum('type', ['CONST', 'EXP', 'MARKOV']).notNullable();
    
    table.decimal('tt_weight', 7, 6).nullable().comment('Weight for transit time in the TFST calculation, applicable for EXP types.');
    table.decimal("tau", 10, 6).nullable().comment('Tau = t / AST parameter for the TFST calculation, applicable for EXP and MARKOV types.');
    table.decimal('gamma', 7, 6).nullable().comment('Gamma = ETTA(v) / ETTA(s) parameter for the TFST calculation, applicable for MARKOV types.');

    table.decimal('input', 10, 6).notNullable();
    table.decimal('value', 10, 6).notNullable();

    table.comment('Alphas table - contains historical alphas parameters used for the TFST indicator.');
  });

  // Time deviations table
  await knex.schema.createTable('time_deviations', (table) => {
    addBaseFields(table);

    table.decimal('dt_hours_lower', 12, 6).notNullable();
    table.decimal('dt_hours_upper', 12, 6).notNullable();
    table.decimal('st_hours_lower', 12, 6).notNullable();
    table.decimal('st_hours_upper', 12, 6).notNullable();
    
    table.decimal('dt_confidence', 7, 6).notNullable();
    table.decimal('st_confidence', 7, 6).notNullable();

    table.comment('Time Deviations table - stores the estimated time deviations for dispatches and shipments, including lower and upper bounds.');
  });

  // Estimation params table
  await knex.schema.createTable('estimation_params', (table) => {
    addBaseFields(table);

    table.decimal('dt_confidence', 7, 6).notNullable();

    table.boolean('consider_closure_holidays').notNullable();
    table.boolean('consider_working_holidays').notNullable();
    table.boolean('consider_weekends_holidays').notNullable();

    table.decimal('rte_mape', 12, 6).notNullable();
    table.boolean('use_rte_model').notNullable().defaultTo(true);

    table.boolean('use_traffic_service').notNullable().defaultTo(false);
    table.decimal('tmi_max_timediff_hours', 12, 6).notNullable();

    table.boolean('use_weather_service').notNullable().defaultTo(false);
    table.decimal('wmi_max_timediff_hours', 12, 6).notNullable();
    table.decimal('wmi_step_distance_km', 12, 6).notNullable();
    table.integer('wmi_max_points').unsigned().notNullable();

    table.decimal('pt_path_min_prob', 12, 6).notNullable();
    table.integer('pt_max_paths').unsigned().notNullable();
    table.decimal('pt_ext_data_min_prob', 12, 6).notNullable();
    table.decimal('pt_confidence', 7, 6).notNullable();
    
    table.decimal('tt_confidence', 7, 6).notNullable();

    table.decimal('tfst_tolerance', 7, 6).notNullable();
  });

  // Estimated Times table
  await knex.schema.createTable('estimated_times', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'vertex_id', 'vertices');
    addForeignKey(table, 'order_id', 'orders');
  
    addTimestampWithTz(table, 'shipment_time', false);
    addTimestampWithTz(table, 'event_time', false);
    addTimestampWithTz(table, 'estimation_time', false);  
    table.string('status', 100).notNullable();
    
    table.integer('DT_weekend_days').unsigned().notNullable().defaultTo(0);
    table.decimal('DT', 12, 6).notNullable();
    table.decimal('DT_lower', 12, 6).notNullable();
    table.decimal('DT_upper', 12, 6).notNullable();
    table.integer('PT_n_paths').unsigned().notNullable();
    table.decimal('PT_avg_tmi', 7, 6).notNullable();
    table.decimal('PT_avg_wmi', 7, 6).notNullable();
    table.decimal('PT_lower', 12, 6).notNullable();
    table.decimal('PT_upper', 12, 6).notNullable();
    table.decimal('TT_lower', 12, 6).notNullable();
    table.decimal('TT_upper', 12, 6).notNullable();
    table.decimal('TFST_lower', 12, 6).notNullable();
    table.decimal('TFST_upper', 12, 6).notNullable();
    table.decimal('EST', 12, 6).notNullable();
    table.decimal('EODT', 12, 6).notNullable();
    table.decimal('CFDI_lower', 12, 6).notNullable();
    table.decimal('CFDI_upper', 12, 6).notNullable();
    addTimestampWithTz(table, 'EDD', false);

    addForeignKey(table, 'time_deviation_id', 'time_deviations');
    addForeignKey(table, 'alpha_id', 'alphas');
    addForeignKey(table, 'estimation_params_id', 'estimation_params');

    table.comment('Estimated times table - stores the realtime lcdi for each order and vertex');
  });

  // Estimated Times - Holidays table
  await knex.schema.createTable('estimated_times_holidays', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'estimated_time_id', 'estimated_times');
    addForeignKey(table, 'holiday_id', 'holidays');

    table.unique(['estimated_time_id', 'holiday_id'], { indexName: 'unique_estimated_time_holiday' });

    table.comment('Estimated Times Holidays table - stores the holidays considered in the estimated times calculations.');
  });

  // Disruptions table
  await knex.schema.createTable('disruptions', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'order_id', 'orders');

    table.boolean('SLS').notNullable().defaultTo(false);

    table.boolean('external').defaultTo(false).notNullable();
    table.text('external_data').nullable();

    table.boolean('delayed').defaultTo(false).notNullable();
    table.text('delay_data').nullable();
    
    table.text('message').nullable();

    table.comment('Disruptions table - stores disruptions related to orders, including packages lost, delays and external disruptions.');
  });

  await knex.schema.createTable('kafka_disruption', (table) => {
    addBaseFields(table); // Adds: id (primary key), created_at, updated_at
    
    table.boolean('external').notNullable().comment('True for external disruptions (Kafka), false for internal');
    table.text('message').notNullable().comment('Human-readable description of the disruption');
    table.text('raw_data').notNullable().comment('Raw message data as received (JSON string)');

    // Indexes for common queries
    table.index('external', 'idx_disruptions_external');
    table.index('created_at', 'idx_disruptions_created_at');
    table.index(['external', 'created_at'], 'idx_disruptions_external_created');

    table.comment('Disruptions table - stores external disruptions from Kafka and internal disruptions from other sources');
  });

  // Overall Residence Indices (ORI) table
  await knex.schema.createTable('overall_residence_indices', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'vertex_id', 'vertices');
    table.decimal('hours', 12, 6).notNullable();

    table.comment('Overall Residence Indices table - contains the residence indices measures for each vertex.');
  });

  // Overall Transit Indices (OTI) table
  await knex.schema.createTable('overall_transit_indices', (table) => {
    addBaseFields(table);
    addForeignKey(table, 'source_id', 'vertices');
    addForeignKey(table, 'destination_id', 'vertices');
    table.decimal('hours', 12, 6).notNullable();

    table.comment('Overall Transit Indices table - contains the transit indices measures for each route.');
  });

  await knex.schema.createTable('tracking_simulator', (table) => {
    addBaseFields(table);
    table.string('tracking_number', 100).notNullable().unique();
    table.integer('carrier_code').notNullable();
    table.string('carrier_name', 100).notNullable();
    table.string('scenario', 50).notNullable();
    table.timestamp('registered_at').notNullable();
    table.integer('current_event_index').defaultTo(0);
    table.enum('status', ['active', 'completed', 'expired']).defaultTo('active');
    table.string('completion_type', 20).nullable();
    
    table.index('tracking_number');
    table.index('status');
    table.index('registered_at');
  });
};

  export const tables = [
    'params',
    'overall_residence_indices',
    'overall_transit_indices',
    'holidays',
    'alphas_opt',
    'alphas',
    'time_deviations',
    'estimation_params',
    'disruptions',
    'estimated_times_holidays',
    'estimated_times',
    'shipment_time_samples',
    'dispatch_time_samples',
    'shipment_time_gammas',
    'dispatch_time_gammas',
    'shipment_times',
    'dispatch_times',
    'kafka_disruption',
    'tracking_simulator'
  ];
export const dropTimeBasedTables = async (knex: Knex): Promise<void> => {

  
  for (const tableName of tables) {

      await knex.raw(`DROP TABLE IF EXISTS ${tableName} CASCADE;`);
    }
  
};