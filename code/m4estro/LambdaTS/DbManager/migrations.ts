// migrations/20250527000001_create_m4estro_database.ts
import { Knex } from 'knex';
import { createCoreBusinessTables, dropCoreBusinessTables } from './coreBusinessTables';
import { createTimeBasedTables, dropTimeBasedTables } from './timeBasedTables';
import { createTrackingAndWeatherTables, dropTrackingAndWeatherTables } from './trackingAndWeatherTables';

/**
 * Create all M4ESTRO database tables
 * 
 * This migration creates the complete M4ESTRO data model with proper foreign key relationships.
 * Creates exactly 30 tables as per the M4ESTRO specification.
 * Tables are created in dependency order to ensure referential integrity.
 */
export const up = async (knex: Knex): Promise<void> => {
  console.log('🚀 Starting M4ESTRO database migration...');
  
  try {
    await down(knex); // Ensure we start with a clean slate
    console.log('🔄 Previous M4ESTRO database state cleared');
    // Step 1: Create core business tables (countries, locations, manufacturers, suppliers, carriers, orders)
    console.log('📦 Creating core business tables...');
    await createCoreBusinessTables(knex);
    console.log('✅ Core business tables created successfully');

    //Step 2: Create time-based tables (dispatch times, delivery times, holidays, vertices, etc.)
    console.log('⏰ Creating time-based tables...');
    await createTimeBasedTables(knex);
    console.log('✅ Time-based tables created successfully');

    // Step 3: Create order tracking and weather tables
    console.log('📊 Creating order tracking and weather tables...');
    await createTrackingAndWeatherTables(knex);
    console.log('✅ Order tracking and weather tables created successfully');

    console.log('🎉 M4ESTRO database migration completed successfully!');
    
  } catch (error) {
    console.error('❌ Error during migration:', error);
    throw error;
  }
};

/**
 * Drop all M4ESTRO database tables
 * 
 * Tables are dropped in reverse dependency order to maintain referential integrity.
 */
 const down = async (knex: Knex): Promise<void> => {
  console.log('🔄 Starting M4ESTRO database rollback...');
  
  try {
    // Step 1: Drop order tracking and weather tables
    console.log('🗑️ Dropping order tracking and weather tables...');
    await dropTrackingAndWeatherTables(knex);
    console.log('✅ Order tracking and weather tables dropped');

    // Step 2: Drop time-based tables
    console.log('🗑️ Dropping time-based tables...');
    await dropTimeBasedTables(knex);
    console.log('✅ Time-based tables dropped');

    // Step 3: Drop core business tables
    console.log('🗑️ Dropping core business tables...');
    await dropCoreBusinessTables(knex);
    console.log('✅ Core business tables dropped');

    console.log('✨ M4ESTRO database rollback completed successfully!');
    
  } catch (error) {
    console.error('❌ Error during rollback:', error);
    throw error;
  }
};