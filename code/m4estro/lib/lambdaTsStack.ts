import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as nodejs from 'aws-cdk-lib/aws-lambda-nodejs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';
import * as path from 'path';
 

interface LambdaTsStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  database: rds.DatabaseCluster;
  databaseSecret: secretsmanager.Secret;
  queues: { [key: string]: sqs.Queue };
  securityGroups: { [key: string]: ec2.SecurityGroup };
}

export class LambdaTsStack extends cdk.Stack {
  public readonly functions: { [key: string]: lambda.Function };

  constructor(scope: Construct, id: string, props: LambdaTsStackProps) {
    super(scope, id, props);


    const knexOptionalExternals = [
      'better-sqlite3',
      'mysql',
      'mysql2',
      'oracledb',
      'pg-query-stream',
      'sqlite3',
      'tedious',
    ];
    // Common Lambda configuration
    const commonLambdaProps = {
      runtime: lambda.Runtime.NODEJS_22_X,
      timeout: cdk.Duration.seconds(60),
      vpc: props.vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [props.securityGroups.lambda],
      bundling: {
        externalModules: ['@aws-sdk/client-secrets-manager', 'pg-native', ...knexOptionalExternals],
        nodeModules: ['pg'],
        sourceMap: true,
        minify: true,
      },
      environment: {
        DB_HOST: props.database.clusterEndpoint.hostname,
        DATABASE_SECRET_ARN: props.databaseSecret.secretArn,
        NODE_OPTIONS: '--enable-source-maps',
      },
    };


    // TypeScript Lambda Functions
    this.functions = {
      databaseManagerLambda: new nodejs.NodejsFunction(this, 'DatabaseManagerFunction', {
        ...commonLambdaProps,
        entry: path.join(__dirname, '../LambdaTS/DbManager/dbMigrationHandler.ts'),
        functionName: 'DatabaseManagerFunction',
        handler: 'databaseHandler',
      }),
      injestorLambda: new nodejs.NodejsFunction(this, 'InjestorLambda', {
        ...commonLambdaProps,
        entry: path.join(__dirname, '../LambdaTS/Injestor/injestor.ts'),
        functionName: 'maestro-injestor',
        timeout: cdk.Duration.seconds(60),
        handler: 'injestorHandler',
        environment: {
          ...commonLambdaProps.environment,
          TRACKING_UPDATES_SQS_URL: props.queues.shipmentEvent.queueUrl,
        }
      }),
      externalApiLambda: new nodejs.NodejsFunction(this, 'ExternalApiLambda', {
        ...commonLambdaProps,
        entry: path.join(__dirname, '../LambdaTS/ExternalAPI/externalApi.ts'),
        functionName: 'maestro-external-api',
        handler: 'apiCallHandler',
      }),
      disruptLambda: new nodejs.NodejsFunction(this, 'DisruptLambda', {
        ...commonLambdaProps,
        timeout: cdk.Duration.minutes(2),
        entry: path.join(__dirname, '../LambdaTS/Disrupt/disrupt.ts'),
        functionName: 'maestro-disrupt-lambda',
        handler: 'disruptHandler',
        environment: {
          ...commonLambdaProps.environment,
          "KAFKA_BROKERS": '168.119.235.102:9092',
          "KAFKA_CLIENT_ID": 'maestro-disrupt-consumer',
          "KAFKA_GROUP_ID": 'maestro-disrupt-group',
          "KAFKA_TOPIC": 'M4ESTRO.external.indicators',
          "DISRUPTION_SQS_URL": props.queues.shipmentEvent.queueUrl,
        },
      }),
      carrierLambda: new nodejs.NodejsFunction(this, 'CarrierLambda', {
        ...commonLambdaProps,
        entry: path.join(__dirname, '../LambdaTS/Carrier/carrier.ts'),
        functionName: 'maestro-carrier-lambda',
        handler: 'carrierHandler',
        environment: {
          ...commonLambdaProps.environment,
          TRACKING_API_KEY: '0FC8B715EF247FC1D198C3EFA464D421',
          USE_TRACKING_SIMULATOR: 'false',
        }
      }),
      // trackingSimulatorLambda: new nodejs.NodejsFunction(this, 'TrackingSimulator', {
      //   ...commonLambdaProps,
      //   entry: path.join(__dirname, '../LambdaTS/TrackingSimulator/trackingSimulator.ts'),
      //   functionName: 'maestro-tracking-simulator',
      //   handler: 'trackingSimulatorHandler',
      // }),
      periodicLambda: new nodejs.NodejsFunction(this, 'PeriodicLambda', {
        ...commonLambdaProps,
        entry: path.join(__dirname, '../LambdaTS/Periodic/periodic.ts'),
        functionName: 'maestro-periodic-lambda',
        handler: 'periodicHandler',
        environment: {
          ...commonLambdaProps.environment,
          TRACKING_UPDATES_SQS_URL: props.queues.shipmentEvent.queueUrl,
          ORDER_STATUS_UPDATES_SQS_URL: props.queues.orderStatus.queueUrl,
        }
      }),
      reconfigureLambda: new nodejs.NodejsFunction(this, 'ReconfigureLambda', {
        ...commonLambdaProps,
        entry: path.join(__dirname, '../LambdaTS/Reconfigure/reconfigure.ts'),
        functionName: 'maestro-reconfigure-lambda',
        handler: 'reconfigureHandler',
        environment: {
          ...commonLambdaProps.environment,
          Deley_Status_SQS_URL: props.queues.delayStatusEvent.queueUrl,
        }
      }),
      deliveryPlanLambda: new nodejs.NodejsFunction(this, 'DeliveryPlanLambda', {
        ...commonLambdaProps,
        entry: path.join(__dirname, '../LambdaTS/DeliveryPlan/deliveryPlan.ts'),
        functionName: 'maestro-delivery-plan-lambda',
        handler: 'deliveryPlanHandler',
      }),
      recentDisruptionsLambda: new nodejs.NodejsFunction(this, 'RecentDisruptionsLambda', {
        ...commonLambdaProps,
        entry: path.join(__dirname, '../LambdaTS/queryDB/recentDisruptions.ts'),
        functionName: 'maestro-recent-disruptions',
        handler: 'recentDisruptionsHandler',
       timeout: cdk.Duration.seconds(30),
      }),
    };

 

    // Grant database secret access to functions that need it
    const dbFunctions = [
      this.functions.databaseManagerLambda,
      this.functions.injestorLambda,
      this.functions.externalApiLambda,
      this.functions.disruptLambda,
      this.functions.carrierLambda,
      this.functions.periodicLambda,
      this.functions.reconfigureLambda,
      this.functions.deliveryPlanLambda,
      this.functions.recentDisruptionsLambda,
      //this.functions.trackingSimulatorLambda,
    ];

    dbFunctions.forEach(func => {
      props.databaseSecret.grantRead(func);
    });

    this.functions.periodicLambda.addEnvironment('CARRIER_LAMBDA_ARN', this.functions.carrierLambda.functionArn);
    this.functions.injestorLambda.addEnvironment('CARRIER_LAMBDA_ARN', this.functions.carrierLambda.functionArn);
    // this.functions.carrierLambda.addEnvironment('USE_TRACKING_SIMULATOR', 'true'); // or 'false'
    // this.functions.carrierLambda.addEnvironment('TRACKING_SIMULATOR_LAMBDA_ARN', this.functions.trackingSimulatorLambda.functionArn);

    // Grant invoke permission
    // this.functions.trackingSimulatorLambda.grantInvoke(this.functions.carrierLambda);
    // Grant SQS permissions
    props.queues.shipmentEvent.grantSendMessages(this.functions.periodicLambda);
    props.queues.orderStatus.grantSendMessages(this.functions.periodicLambda);
    props.queues.shipmentEvent.grantSendMessages(this.functions.injestorLambda);
    props.queues.shipmentEvent.grantSendMessages(this.functions.disruptLambda);

    props.queues.delayStatusEvent.grantConsumeMessages(this.functions.reconfigureLambda);

    this.functions.reconfigureLambda.addEventSource(
      new lambdaEventSources.SqsEventSource(props.queues.delayStatusEvent, {
        batchSize: 10, // Process up to 10 messages at a time
        
      })
    );


    this.functions.carrierLambda.grantInvoke(this.functions.periodicLambda);
    this.functions.carrierLambda.grantInvoke(this.functions.injestorLambda);
  

    new events.Rule(this, 'PeriodicRule', {
      schedule: events.Schedule.rate(cdk.Duration.hours(24)), // 24 hours
      description: 'Rule to trigger periodic Lambda function every 24 hours',
      enabled: true,
      // Use the periodicLambda as the target for this rule
      targets: [new targets.LambdaFunction(this.functions.periodicLambda)],
    });
  
      new events.Rule(this, 'DisruptRule', {
      schedule: events.Schedule.rate(cdk.Duration.hours(24)), // 24 hours
      description: 'Rule to trigger disrupt Lambda function every 24 hours',
      enabled: true,
      // Use the disruptLambda as the target for this rule
        targets: [new targets.LambdaFunction(this.functions.disruptLambda)],
    });


   const lambdaLogPolicy = new iam.PolicyStatement({
          actions: ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
          resources: ['*'],
        });

    // Apply logging policy to all Lambda functions
    dbFunctions.forEach(func => {
      func.addToRolePolicy(lambdaLogPolicy);
    });

}
}
