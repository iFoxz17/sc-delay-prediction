import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export class InfrastructureStack extends cdk.Stack {
    public readonly vpc: ec2.Vpc;
    public readonly databaseCluster: rds.DatabaseCluster;
    public readonly queues : { [key: string]: sqs.Queue } ;
    public readonly databaseSecret: secretsmanager.Secret;
    public readonly securityGroup: { [key: string]: ec2.SecurityGroup };

    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        // Create a VPC
        this.vpc = new ec2.Vpc(this, 'MaestroVPC', {
            maxAzs: 2,
            natGateways: 1,
            subnetConfiguration: [
                {
                    cidrMask: 24,
                    name: 'Public',
                    subnetType: ec2.SubnetType.PUBLIC,
                },
                {
                    cidrMask: 24,
                    name: 'Private',
                    subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,

                },
                {
                    cidrMask: 24,
                    name: 'Isolated',
                    subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
                },
            ],
        });


        // Create security groups
        this.securityGroup = {
            lambda: new ec2.SecurityGroup(this, 'LambdaSecurityGroup', {
                vpc: this.vpc,
                description: 'Security group for Lambda functions',
                allowAllOutbound: true,
            }),
            database: new ec2.SecurityGroup(this, 'RDSSecurityGroup', {
                vpc: this.vpc,
                description: 'Security group for RDS instance',
                allowAllOutbound: false,
            }),
          

        };

        this.securityGroup.database.addIngressRule(
            this.securityGroup.lambda,
            ec2.Port.tcp(5432),
            'Allow Lambda access to RDS'
        );

        // RDS Secret Credentials

        this.databaseSecret = new secretsmanager.Secret(this, 'DatabaseSecret', {
            secretName: 'maestro/database/credentials',
            description: 'RDS PostgreSQL database credentials for MyApp',
            generateSecretString: {
                secretStringTemplate: JSON.stringify({
                    username: 'dbadmin',
                    dbname: 'maestroApp',
                    engine: 'postgres',
                    port: 5432
                }),
                generateStringKey: 'password',
                excludeCharacters: ' %+~`#[]{}:;<>?!\'/@"\\',
                includeSpace: false,
                passwordLength: 32,
            },
        });

         // Create database subnet group
        const dbSubnetGroup = new rds.SubnetGroup(this, 'DatabaseSubnetGroup', {
            vpc: this.vpc,
            description: 'Subnet group for Aurora Serverless cluster',
            vpcSubnets: {
                subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
            },
        });
        
        this.databaseCluster = new rds.DatabaseCluster(this, 'MaestroDatabase', {
            engine: rds.DatabaseClusterEngine.auroraPostgres({
                version: rds.AuroraPostgresEngineVersion.VER_16_4, // Updated to v16 to match your original
            }),
            vpc: this.vpc,
            subnetGroup: dbSubnetGroup,
            securityGroups: [this.securityGroup.database],
            defaultDatabaseName: 'maestroApp',
            credentials: rds.Credentials.fromSecret(this.databaseSecret),

            // Serverless v2 configuration
            serverlessV2MinCapacity: 0.5, // Minimum ACUs
            serverlessV2MaxCapacity: 16,  // Maximum ACUs
            
            writer: rds.ClusterInstance.serverlessV2('writer', {
                enablePerformanceInsights: false, // Disable for cost savings in dev
            }),
            // Security settings
            storageEncrypted: true,
            deletionProtection: false, // Disable for dev/test environments
            
            // Backup configuration
            backup: {
                retention: cdk.Duration.days(7),
                preferredWindow: '03:00-04:00',
            },
            
        
            
            // Enable logging
            cloudwatchLogsExports: ['postgresql'],
            cloudwatchLogsRetention: cdk.aws_logs.RetentionDays.ONE_WEEK,
            
            // Removal policy for dev/test
            removalPolicy: cdk.RemovalPolicy.DESTROY,
        });

        this.queues = {
            shipmentEvent: new sqs.Queue(this, 'ShipmentEventQueue', {
                queueName: 'shipment-event-queue',
                visibilityTimeout: cdk.Duration.seconds(300),
                deadLetterQueue: {
                    queue: new sqs.Queue(this, 'ShipmentEventDLQ', {
                        queueName: 'shipment-event-dlq',
                    }),
                    maxReceiveCount: 3,
                },
            }),
            orderStatus: new sqs.Queue(this, 'OrderStatusQueue', {
                queueName: 'order-status-queue',
                visibilityTimeout: cdk.Duration.seconds(300),
                deadLetterQueue: {
                    queue: new sqs.Queue(this, 'OrderStatusDLQ', {
                        queueName: 'order-status-dlq',
                    }),
                    maxReceiveCount: 3,
                },
            }),

            delayStatusEvent: new sqs.Queue(this, 'DelayStatusEventQueue', {
                queueName: 'delay-status-event-queue',
                visibilityTimeout: cdk.Duration.seconds(300),
                deadLetterQueue: {
                    queue: new sqs.Queue(this, 'DelayStatusEventDLQ', {
                        queueName: 'delay-status-event-dlq',
                    }),
                    maxReceiveCount: 3,
                },
            }),
           
        };
    }
}

