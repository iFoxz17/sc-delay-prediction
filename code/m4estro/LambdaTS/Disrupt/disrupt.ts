// src/functions/disrupt.ts
// TEMPORARY VERSION: Forces reading all messages from beginning
import { ScheduledEvent, Context } from 'aws-lambda';
import { Kafka, Consumer, EachMessagePayload } from 'kafkajs';
import { SQSClient, SendMessageCommand } from '@aws-sdk/client-sqs';
import { z } from 'zod';
import { DatabaseUtil } from '../utils/DatabaseUtils';

// ============================================================================
// ENVIRONMENT VARIABLES & CONFIGURATION
// ============================================================================

const KAFKA_BROKERS = (process.env.KAFKA_BROKERS || '168.119.235.102:9092').split(',');
const KAFKA_CLIENT_ID = process.env.KAFKA_CLIENT_ID || 'maestro-disrupt-consumer';

// TEMPORARY: Use unique group to read all messages OR set environment variable
const FORCE_READ_ALL = true; // process.env.FORCE_READ_ALL_MESSAGES === 'true';
const KAFKA_GROUP_ID = (process.env.KAFKA_GROUP_ID || 'maestro-disrupt-persistent-group');

const KAFKA_TOPIC = process.env.KAFKA_TOPIC || 'M4ESTRO.external.indicators';
const DISRUPTION_SQS_URL = process.env.DISRUPTION_SQS_URL!;

// Initialize SQS client
const sqsClient = new SQSClient({
  region: process.env.AWS_REGION || 'us-east-1'
});

// ============================================================================
// SCHEMAS (same as before)
// ============================================================================

const IndicatorReportSchema = z.object({
  IndicatorReport: z.object({
    dataSourceID: z.string().optional(),
    systemID: z.string().optional(),
    timestamp: z.string().optional(),
    id: z.string().optional(),
    Location: z.object({
      type: z.string().optional(),
      features: z.array(z.object({
        type: z.string().optional(),
        id: z.string().optional(),
        properties: z.object({
          name: z.string().optional(),
          radius_km: z.number().optional(),
        }).optional(),
        geometry: z.object({
          type: z.string().optional(),
          coordinates: z.array(z.number()).optional(),
        }).optional(),
      })).optional(),
    }).optional(),
    Value: z.object({
      indicatorType: z.string().optional(),
      disruptionType: z.string().optional(),
      duration: z.number().optional(),
      timestamp: z.string().optional(),
      datasetsDerived: z.object({
        dataset: z.array(z.string()).optional(),
      }).optional(),
      Location: z.object({
        type: z.string().optional(),
        features: z.array(z.object({
          type: z.string().optional(),
          id: z.string().optional(),
          properties: z.object({
            name: z.string().optional(),
            radius_km: z.number().optional(),
          }).optional(),
          geometry: z.object({
            type: z.string().optional(),
            coordinates: z.array(z.number()).optional(),
          }).optional(),
        })).optional(),
      }).optional(),
      Measurements: z.array(z.object({
        name: z.string().optional(),
        value: z.number().optional(),
      })).optional(),
    }).optional(),
  }).optional(),
});

interface DisruptResult {
  totalMessages: number;
  validMessages: number;
  disruptionsStored: number;
  affectedOrdersFound: number;
  sentToSQS: number;
  errors: string[];
  connectionStatus: 'success' | 'failed';
  processingTimeMs: number;
  consumerGroup: string;
  readFromBeginning: boolean;
}
interface OrderLastStep {
  order_id: number;
  order_status: string;
  order_tracking_number: string;
  last_step_location: string;
  last_step_timestamp: Date;
  last_step_latitude: number;
  last_step_longitude: number;
}

// ============================================================================
// MAIN HANDLER
// ============================================================================

export const disruptHandler = async (
  event: ScheduledEvent,
  context: Context
): Promise<DisruptResult> => {
  
  const startTime = Date.now();
  let consumer: Consumer | null = null;
  let dbUtil: DatabaseUtil | null = null;
  
  const result: DisruptResult = {
    totalMessages: 0,
    validMessages: 0,
    disruptionsStored: 0,
    affectedOrdersFound: 0,
    sentToSQS: 0,
    errors: [],
    connectionStatus: 'failed',
    processingTimeMs: 0,
    consumerGroup: KAFKA_GROUP_ID,
    readFromBeginning: FORCE_READ_ALL,
  };

  let isProcessing = true;
  let messageCount = 0;

  try {
    console.log('🚨 Starting disruption monitoring from Kafka');
    console.log('⏰ Triggered at:', new Date().toISOString());
    console.log('🔗 Connecting to brokers:', KAFKA_BROKERS);
    console.log('👥 Consumer Group:', KAFKA_GROUP_ID);
    console.log('📢 Topic:', KAFKA_TOPIC);
    console.log('🔄 Read from beginning:', FORCE_READ_ALL ? 'YES (unique group)' : 'NO (persistent group)');

    if (FORCE_READ_ALL) {
      console.log('⚠️ TEMPORARY MODE: Using unique consumer group to read ALL messages');
      console.log('💡 To disable, remove FORCE_READ_ALL_MESSAGES environment variable');
    }

    // Validate SQS URL
    if (!DISRUPTION_SQS_URL) {
      throw new Error('DISRUPTION_SQS_URL environment variable is required');
    }

    // Initialize database connection
    dbUtil = DatabaseUtil.fromEnvironment();
    const knex = await dbUtil.getKnex();

    // Initialize Kafka consumer
    const kafka = new Kafka({
      clientId: KAFKA_CLIENT_ID,
      brokers: KAFKA_BROKERS,
      connectionTimeout: 15000,
      requestTimeout: 60000,
      retry: {
        initialRetryTime: 100,
        retries: 5,
        maxRetryTime: 30000,
      },
      logLevel: 2, // WARN level
    });

    consumer = kafka.consumer({
      groupId: KAFKA_GROUP_ID,
      // sessionTimeout: 60000,
      // heartbeatInterval: 3000,
      // maxWaitTimeInMs: 5000,
      // allowAutoTopicCreation: false,
      // maxBytesPerPartition: 1024 * 1024,
      // minBytes: 1,
      // maxBytes: 1024 * 1024 * 10,
    });

    // Set up event listeners
    consumer.on('consumer.connect', () => {
      console.log('✅ Consumer connected to Kafka');
    });

    consumer.on('consumer.group_join', (event) => {
      console.log('👥 Joined consumer group:', {
        groupId: event.payload.groupId,
        memberId: event.payload.memberId,
        isLeader: event.payload.isLeader,
        memberAssignment: event.payload.memberAssignment,
      });
    });

    consumer.on('consumer.fetch', () => {
      console.log('📥 Fetching messages from Kafka');
    });

    consumer.on('consumer.crash', (event) => {
      console.error('💥 Consumer crashed:', event.payload.error);
      result.errors.push(`Consumer crash: ${event.payload.error.message}`);
    });

    // Connect to Kafka
    await consumer.connect();
    console.log('✅ Connected to Kafka broker');
    result.connectionStatus = 'success';

    // Subscribe to topic with appropriate fromBeginning setting
    await consumer.subscribe({ 
      topic: KAFKA_TOPIC,
      fromBeginning: FORCE_READ_ALL // Read from beginning if using unique group
    });
    console.log(`✅ Subscribed to topic: ${KAFKA_TOPIC} (fromBeginning: ${FORCE_READ_ALL})`);

    // Calculate processing timeout
    const processingTimeout = Math.min(
      context.getRemainingTimeInMillis() - 20000,
      90000 // Increase to 90 seconds for processing all messages
    );

    console.log(`⏱️ Processing messages for ${processingTimeout}ms`);

    // Set timeout to stop processing
    const timeoutHandle = setTimeout(() => {
      console.log('⏰ Processing timeout reached');
      isProcessing = false;
    }, processingTimeout);

    // Process messages
    await consumer.run({
      partitionsConsumedConcurrently: 1,
      eachMessage: async (payload: EachMessagePayload) => {
        if (!isProcessing) {
          return;
        }

        messageCount++;
        result.totalMessages = messageCount;

        // Log progress for every message when reading all
        if (FORCE_READ_ALL || messageCount === 1 || messageCount % 5 === 0) {
          console.log(`📨 Processing message ${messageCount} (partition: ${payload.partition}, offset: ${payload.message.offset})`);
        }

        try {
          await handleMessage(payload, result, knex);
        } catch (error) {
          console.error(`❌ Error processing message ${messageCount}:`, error);
          result.errors.push(`Message ${messageCount}: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
      },
    });

    // Wait for processing to complete or timeout
    await new Promise<void>((resolve) => {
      const checkInterval = setInterval(() => {
        if (!isProcessing) {
          clearInterval(checkInterval);
          clearTimeout(timeoutHandle);
          resolve();
        }
      }, 1000);
    });

  } catch (error) {
    console.error('❌ Error in disruption handler:', error);
    result.errors.push(error instanceof Error ? error.message : 'Unknown error');
    result.connectionStatus = 'failed';

  } finally {
    // Cleanup
    isProcessing = false;

    if (consumer) {
      try {
        await consumer.stop();
        await consumer.disconnect();
        console.log('🔌 Kafka consumer disconnected');
      } catch (error) {
        console.error('⚠️ Error disconnecting consumer:', error);
      }
    }

    if (dbUtil) {
      await dbUtil.closeConnection();
    }

    result.processingTimeMs = Date.now() - startTime;
    
    console.log('📊 Final Results:');
    console.log(`   Consumer Group: ${result.consumerGroup}`);
    console.log(`   Read from Beginning: ${result.readFromBeginning}`);
    console.log(`   Messages processed: ${result.totalMessages}`);
    console.log(`   Valid reports: ${result.validMessages}`);
    console.log(`   Disruptions stored: ${result.disruptionsStored}`);
    console.log(`   Affected orders found: ${result.affectedOrdersFound}`);
    console.log(`   Sent to SQS: ${result.sentToSQS}`);
    console.log(`   Connection: ${result.connectionStatus}`);
    console.log(`   Processing time: ${result.processingTimeMs}ms`);
    
    if (result.errors.length > 0) {
      console.log('❌ Errors:', result.errors);
    }

    if (result.totalMessages === 0) {
      console.log('');
      if (FORCE_READ_ALL) {
        console.log('🔍 No messages found even when reading from beginning');
        console.log('   This suggests the topic is truly empty or all messages have expired');
      } else {
        console.log('🔍 No new messages since last run (using committed offsets)');
        console.log('💡 To read all messages, set environment variable: FORCE_READ_ALL_MESSAGES=true');
      }
    } else {
      console.log('');
      console.log(`✅ Successfully processed ${result.totalMessages} messages!`);
      if (result.validMessages > 0) {
        console.log(`🎯 Found ${result.validMessages} valid IndicatorReports`);
      }
    }
  }

  return result;
};

// ============================================================================
// MESSAGE HANDLING (same as before but with enhanced logging)
// ============================================================================

async function handleMessage(
  { message }: EachMessagePayload,
  result: DisruptResult,
  knex: any
): Promise<void> {
  
  try {
    const rawMessage = message.value?.toString();
    
    if (!rawMessage) {
      console.log(`⚠️ Empty message at offset ${message.offset}`);
      return;
    }

    // Log first 200 chars of each message when reading all
    if (result.readFromBeginning || result.totalMessages <= 5) {
      console.log(`📝 Message ${result.totalMessages} preview: ${rawMessage.substring(0, 200)}...`);
    }
    
    try {
      const parsed = JSON.parse(rawMessage);
      
      // Validate against IndicatorReport schema
      const validationResult = IndicatorReportSchema.safeParse(parsed);
      
      if (validationResult.success) {
        result.validMessages++;
        console.log(`✅ Valid IndicatorReport detected (${result.validMessages}/${result.totalMessages})`);
        
        const report = validationResult.data;
        
        // Find affected orders
        const affectedOrders = await getInTransitOrdersWithLastSteps(knex);
        result.affectedOrdersFound = Math.max(result.affectedOrdersFound, affectedOrders.length);
        
        console.log(`🚛 Found ${affectedOrders.length} IN_TRANSIT orders that may be affected`);

        // Send to SQS
        await sendDisruptionToSQS(report, affectedOrders);
        result.sentToSQS++;
        console.log(`📤 Successfully sent disruption #${result.sentToSQS} to SQS`);
        
        // Log key information
        // logIndicatorReport(report);

      } else {
        console.log(`⚠️ Message ${result.totalMessages}: Invalid IndicatorReport format`);
        console.log(`   Validation errors: ${validationResult.error.errors.length}`);
        console.log(`   First error: ${validationResult.error.errors[0]?.message}`);
        
        // Log the structure for debugging
        if (result.totalMessages <= 3) {
          console.log(`   Message structure: ${JSON.stringify(Object.keys(parsed), null, 2)}`);
        }
      }
      
    } catch (parseError) {
      console.log(`❌ Message ${result.totalMessages}: Failed to parse as JSON`);
      console.log(`   Error: ${parseError instanceof Error ? parseError.message : 'Unknown error'}`);
      
      // Show first part of unparseable message for debugging
      if (result.totalMessages <= 3) {
        console.log(`   Content: ${rawMessage.substring(0, 300)}`);
      }
    }

  } catch (error) {
    console.error(`❌ Error handling message ${result.totalMessages}:`, error);
    throw error;
  }
}

// Rest of the functions (getInTransitOrdersWithLastSteps, sendDisruptionToSQS, etc.) remain the same...
// [Previous implementations of these functions would go here]

async function getInTransitOrdersWithLastSteps(knex: any): Promise<any[]> {
  try {
    const query = `
      WITH last_steps AS (
        SELECT 
          os.order_id,
          os.location,
          os.timestamp,
          os.latitude,
          os.longitude,
          ROW_NUMBER() OVER (
            PARTITION BY os.order_id 
            ORDER BY os.step DESC, os.timestamp DESC
          ) as rn
        FROM order_steps os
        INNER JOIN orders o ON os.order_id = o.id
        WHERE o.status IN ('IN_TRANSIT', 'PICKED_UP', 'DEPARTED', 'ARRIVED', 'CUSTOMS_PROCESSING', 'CUSTOMS_CLEARED', 'OUT_FOR_DELIVERY')
          AND o.tracking_number IS NOT NULL
          AND o.tracking_number != ''
          AND o.sls = false
      )
      SELECT 
        o.id as order_id,
        o.status as order_status,
        o.tracking_number as order_tracking_number,
        ls.location as last_step_location,
        ls.timestamp as last_step_timestamp,
        ls.latitude as last_step_latitude,
        ls.longitude as last_step_longitude
      FROM orders o
      LEFT JOIN last_steps ls ON o.id = ls.order_id AND ls.rn = 1
      WHERE o.status IN ('IN_TRANSIT', 'PICKED_UP', 'DEPARTED', 'ARRIVED', 'CUSTOMS_PROCESSING', 'CUSTOMS_CLEARED', 'OUT_FOR_DELIVERY')
        AND o.tracking_number IS NOT NULL
        AND o.tracking_number != ''
        AND o.sls = false
      ORDER BY o.updated_at DESC
      LIMIT 1000
    `;

    const result = await knex.raw(query);
    return result.rows as OrderLastStep[];

  } catch (error) {
    console.error('❌ Error getting orders:', error);
    return [];
  }
}


async function sendDisruptionToSQS(report: any, affectedOrders: any[]): Promise<void> {
  try {
    const ir = report.IndicatorReport;
    
    const sqsMessage = {
      eventType: 'EXTERNAL_EVENT',
      timestamp: new Date().toISOString(),
      source: 'kafka_consumer',
      data: {
        disruption: {
            eventTimestamp: ir?.Value?.timestamp || new Date().toISOString(),
            disruptionType: ir?.Value?.disruptionType || 'unknown',
            disruptionLocation: {
              name: ir?.Value?.location || 'unknown',
              coordinates: ir?.Value?.coordinates || [0, 0],
              radiusKm: ir?.Value?.radiusKm || 0
            },
            measurements: {
              severity: ir?.Value?.measurements?.severity || 0,
            },
        },
        affectedOrders: {
          total: affectedOrders.length,
          summary: {
            orderIds: affectedOrders.slice(0, 10).map(order => order.order_id),
            statuses: [...new Set(affectedOrders.map(order => order.order_status))],
            locations: [...new Set(affectedOrders.map(order => order.last_step_location))].slice(0, 5),
          },
        }
      },
    };

    console.log(`📤 Sending disruption to SQS: ${JSON.stringify(sqsMessage, null, 2)}`);

    const command = new SendMessageCommand({
      QueueUrl: DISRUPTION_SQS_URL,
      MessageBody: JSON.stringify(sqsMessage),
      MessageAttributes: {
        eventType: { DataType: 'String', StringValue: 'EXTERNAL_DISRUPTION' },
        affectedOrderCount: { DataType: 'Number', StringValue: affectedOrders.length.toString() },
        disruptionType: { DataType: 'String', StringValue: ir?.Value?.disruptionType || 'unknown' },
      },
    });

    await sqsClient.send(command);

  } catch (error) {
    console.error('❌ SQS error:', error);
    throw error;
  }
}

// function logIndicatorReport(report: any): void {
//   // Same implementation as before
//   const ir = report.IndicatorReport;
//   if (!ir) return;

//   console.log('📋 IndicatorReport Summary:');
//   console.log(`   🆔 ID: ${ir.id || 'N/A'}`);
//   console.log(`   📡 Source: ${ir.dataSourceID || 'N/A'}`);
//   console.log(`   🖥️ System: ${ir.systemID || 'N/A'}`);
//   console.log(`   ⏰ Timestamp: ${ir.timestamp || 'N/A'}`);
// }

export default disruptHandler;