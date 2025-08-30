import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import { DockerImageCode, DockerImageFunction } from 'aws-cdk-lib/aws-lambda';
import * as path from 'path';
import { RemovalPolicy } from 'aws-cdk-lib';

interface LambdaPyStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  database: rds.DatabaseCluster;
  databaseSecret: secretsmanager.Secret;
  queues: { [key: string]: sqs.Queue };
  securityGroups: { [key: string]: ec2.SecurityGroup };
}

export class LambdaPyStack extends cdk.Stack {
  public readonly functions: { [key: string]: lambda.Function };

  // private readonly RT_ESTIMATOR_LAMBDA_ARN_KEY: 'RT_ESTIMATOR_LAMBDA_ARN';
  // private readonly ROUTE_TIME_ESTIMATOR_MODEL_KEY: 'ROUTE_TIME_ESTIMATOR_MODEL_KEY';
  // private readonly RECONFIGURATION_QUEUE_URL_KEY: 'RECONFIGURATION_QUEUE_URL';

  constructor(scope: Construct, id: string, props: LambdaPyStackProps) {
    super(scope, id, props);

    // S3 Bucket scgraph and ML model storage
    const scGraphBucket = new s3.Bucket(this, 'SCGraphBucket', {
      bucketName: 'sc-graph-bucket',
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      publicReadAccess: false,
      // removalPolicy: RemovalPolicy.RETAIN,                         // For production
      removalPolicy: RemovalPolicy.DESTROY,                           // For development/testing
      autoDeleteObjects: false,
      lifecycleRules: [
        {
          id: 'ExpireOldFiles',
          expiration: cdk.Duration.days(730),
        },
      ],
    });

    const commonLambdaProps = {
      timeout: cdk.Duration.seconds(60),
      vpc: props.vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [props.securityGroups.lambda],
      environment: {
        DATABASE_SECRET_ARN: props.databaseSecret.secretArn,
        SC_GRAPH_BUCKET: scGraphBucket.bucketName,
        LOG_LEVEL: 'DEBUG',
      },
      memorySize: 512,
    };

    /*
    // Python Docker Lambda Functions
    this.functions = {
      dataProcessor: new DockerImageFunction(this, 'DataProcessorFunction', {
        ...commonDockerLambdaProps,
        code: DockerImageCode.fromImageAsset(path.join(__dirname, '../LambdaPY/data-processor'), {
          cmd: ['handler.main'],
        }),
        functionName: 'myapp-data-processor',
        timeout: cdk.Duration.minutes(15), // Heavy processing
        memorySize: 2048, // Increased memory for data processing
        architecture: lambda.Architecture.X86_64,
      }),
    */

    const statsLayer = new lambda.LayerVersion(this, 'StatsLayer', {
      code: lambda.Code.fromAsset(path.join(__dirname, '../LambdaPY/stats_layer'), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          command: [
            'bash', '-c',
            [
              'pip install --no-cache-dir -r requirements.txt -t /asset-output/python',

              // Remove numpy and scipy tests, docs, build files
              'rm -rf /asset-output/python/numpy/tests',
              'rm -rf /asset-output/python/scipy/tests',
              'rm -rf /asset-output/python/scipy/_build',
              'rm -rf /asset-output/python/scipy/doc',

              // Remove .dll files if any (optional)
              'rm -f /asset-output/python/**/*.dll || true',

              // Clean Python caches
              'find /asset-output/python -name "__pycache__" -exec rm -rf {} +',
              'find /asset-output/python -name "*.pyc" -delete',
              'find /asset-output/python -name "*.pyo" -delete',

              // Remove dist-info and egg-info folders recursively
              'find /asset-output/python -name "*.dist-info" -exec rm -rf {} +',
              'find /asset-output/python -name "*.egg-info" -exec rm -rf {} +',

              // Copy the custom python modules to the layer output directory
              'cp -r python/* /asset-output/python/'
            ].join(' && ')
          ]
        }
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: 'Lambda layer for statistical utilities (NumPy and SciPy)',
      // removalPolicy: RemovalPolicy.RETAIN,                         // For production
      removalPolicy: RemovalPolicy.DESTROY,                           // For development/testing
      compatibleArchitectures: [lambda.Architecture.X86_64],
    });

    const platformCommLayer = new lambda.LayerVersion(this, 'PlatformCommLayer', {
      code: lambda.Code.fromAsset(path.join(__dirname, '../LambdaPY/platform_comm_layer'), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          command: [
            'bash', '-c',
            [
              // Install dependencies into /asset-output/python
              'pip install --no-cache-dir -r requirements.txt -t /asset-output/python',

              // Remove test folders (common ones for these libs)
              'rm -rf /asset-output/python/sqlalchemy/tests',
              'rm -rf /asset-output/python/pydantic/tests',
              'rm -rf /asset-output/python/aws_lambda_powertools/tests',

              // Remove psycopg2 test and extra files if present
              'rm -rf /asset-output/python/psycopg2/tests',

              // Remove __pycache__, .pyc, .pyo files
              'find /asset-output/python -name "__pycache__" -exec rm -rf {} +',
              'find /asset-output/python -name "*.pyc" -delete',
              'find /asset-output/python -name "*.pyo" -delete',

              // Remove dist-info and egg-info folders recursively
              'find /asset-output/python -name "*.dist-info" -exec rm -rf {} +',
              'find /asset-output/python -name "*.egg-info" -exec rm -rf {} +',

              // Copy the custom python modules to the layer output directory
              'cp -r python/* /asset-output/python/'
            ].join(' && ')
          ],
        }
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: 'Lambda layer for platform communication utilities (API management, DB access, etc.)',
      // removalPolicy: RemovalPolicy.RETAIN,                         // For production
      removalPolicy: RemovalPolicy.DESTROY,                           // For development/testing
      compatibleArchitectures: [lambda.Architecture.X86_64],
    });

    const graphLayer = new lambda.LayerVersion(this, 'GraphLayer', {
      code: lambda.Code.fromAsset(path.join(__dirname, '../LambdaPY/graph_layer'), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          command: [
            'bash', '-c',
            [
              // Install dependencies into /asset-output/python
              'pip install --no-cache-dir -r requirements.txt -t /asset-output/python',

              // Clean up unnecessary files
              'rm -rf /asset-output/python/*/tests',
              'rm -rf /asset-output/python/*/__pycache__',
              'find /asset-output/python -name "*.pyc" -delete',
              'find /asset-output/python -name "*.pyo" -delete',
              'find /asset-output/python -name "*.dist-info" -exec rm -rf {} +',
              'find /asset-output/python -name "*.egg-info" -exec rm -rf {} +',

              // Copy custom modules if any
              'cp -r python/* /asset-output/python/'
            ].join(' && ')
          ]
        }
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: 'Lambda layer with igraph and geopy dependencies',
      // removalPolicy: RemovalPolicy.RETAIN,                         // For production
      removalPolicy: RemovalPolicy.DESTROY,                           // For development/testing
      compatibleArchitectures: [lambda.Architecture.X86_64],
    });

    // HistoricalLCDI Lambda Function
    const histLCDILambda = new lambda.Function(this, 'HistoricalLCDILambda', {
      ...commonLambdaProps,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'historical_lcdi_handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../LambdaPY/historical_lcdi/'), {
        exclude: ['**/__pycache__', '**/*.pyc', '**/*.pyo'],
      }),
      description: 'Lambda responsible for managing historical LCDIs',
      layers: [statsLayer, platformCommLayer],
    });

    // RTEstimator Lambda Function
    const rtEstimatorLambda = new lambda.DockerImageFunction(this, 'RTEstimatorLambda', {
      ...commonLambdaProps,
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../LambdaPY/rt_estimator')),
      description: 'Lambda responsible for estimating route times using ML models',
    });
    rtEstimatorLambda.addEnvironment("ROUTE_TIME_ESTIMATOR_MODEL_KEY", 'rt_estimator_xgboost.json');

    // RealtimeLCDIApi Lambda Function
    const realtimeLCDIApiLambda = new lambda.Function(this, 'RealtimeLCDIApiLambda', {
      ...commonLambdaProps,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'api/realtime_lcdi_api_handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../LambdaPY/realtime_lcdi'), {
        exclude: ['**/__pycache__', '**/*.pyc', '**/*.pyo', 'sqs/**'],
      }),
      description: 'Lambda responsible for managing external real-time LCDIs requests via API',
      layers: [platformCommLayer, graphLayer, statsLayer],
    });
    rtEstimatorLambda.grantInvoke(realtimeLCDIApiLambda);
    realtimeLCDIApiLambda.addEnvironment("RT_ESTIMATOR_LAMBDA_ARN", rtEstimatorLambda.functionArn);

    // RealtimeLCDISqs Lambda Function
    const realtimeLCDISqsLambda = new lambda.Function(this, 'RealtimeLCDISqsLambda', {
      ...commonLambdaProps,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'sqs/realtime_lcdi_sqs_handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../LambdaPY/realtime_lcdi'), {
        exclude: ['**/__pycache__', '**/*.pyc', '**/*.pyo', 'api/**'],
      }),
      description: 'Lambda responsible for managing internal real-time LCDIs requests via SQS',
      layers: [platformCommLayer, graphLayer, statsLayer],
    });
    rtEstimatorLambda.grantInvoke(realtimeLCDISqsLambda);
    realtimeLCDISqsLambda.addEnvironment("RT_ESTIMATOR_LAMBDA_ARN", rtEstimatorLambda.functionArn);

    // Graph manager Lambda Function
    const graphManagerLambda = new lambda.Function(this, 'graphManagerLambda', {
      ...commonLambdaProps,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'graph_manager_handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../LambdaPY/graph_manager/'), {
        exclude: ['**/__pycache__', '**/*.pyc', '**/*.pyo', '**/local/**'],
      }),
      description: 'Lambda responsible for managing the graph representing the supply chain',
      layers: [platformCommLayer, graphLayer],
    });

    // Domain model Lambda Function
    const domainModelLambda = new lambda.Function(this, 'domainModelLambda', {
      ...commonLambdaProps,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'domain_model_handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../LambdaPY/domain_model/'), {
        exclude: ['**/__pycache__', '**/*.pyc', '**/*.pyo', '**/local/**'],
      }),
      description: 'Lambda responsible for accessing and managing the domain model data (orders, suppliers, carriers, etc.)',
      layers: [platformCommLayer, graphLayer],
    });

    // Add all functions here to access them from other stacks
    this.functions = {
      histLCDILambda: histLCDILambda,
      realtimeLCDIApiLambda: realtimeLCDIApiLambda,
      realtimeLCDISqsLambda: realtimeLCDISqsLambda,
      graphManagerLambda: graphManagerLambda,
      domainModelLambda: domainModelLambda,
      rtEstimatorLambda: rtEstimatorLambda,
    };

    scGraphBucket.grantRead(domainModelLambda);
    scGraphBucket.grantRead(rtEstimatorLambda);
    scGraphBucket.grantReadWrite(graphManagerLambda);
    scGraphBucket.grantReadWrite(realtimeLCDIApiLambda);
    scGraphBucket.grantReadWrite(realtimeLCDISqsLambda);

    // Grant database secret access to functions that need it
    const dbFunctions = [
      this.functions.histLCDILambda,
      this.functions.realtimeLCDIApiLambda,
      this.functions.realtimeLCDISqsLambda,
      this.functions.graphManagerLambda,
      this.functions.domainModelLambda,
    ];

    const lambdaLogPolicy = new iam.PolicyStatement({
        actions: ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
        resources: ['*'],
        });

    dbFunctions.forEach(func => {
      props.databaseSecret.grantRead(func);
      func.addToRolePolicy(lambdaLogPolicy);
    });

    props.database.connections.allowDefaultPortFrom(props.securityGroups.lambda);

    // -- Abilitate realtimeLCDISqsLambda to utilize the sqs queues --
    // Add environment variables
    this.functions.realtimeLCDISqsLambda.addEnvironment("RECONFIGURATION_QUEUE_URL", props.queues.delayStatusEvent.queueUrl);

    // Add SQS event source
    this.functions.realtimeLCDISqsLambda.addEventSource(
      new lambdaEventSources.SqsEventSource(props.queues.shipmentEvent, {
        batchSize: 10,
        enabled: true,
      })
    );

    // Grant SQS permissions
    props.queues.shipmentEvent.grantConsumeMessages(this.functions.realtimeLCDISqsLambda);
    props.queues.delayStatusEvent.grantSendMessages(this.functions.realtimeLCDISqsLambda);
    }
}