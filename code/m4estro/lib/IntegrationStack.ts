import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { Construct } from 'constructs';

interface IntegrationStackProps extends cdk.StackProps {
  TsLambdaFunctions: { [key: string]: lambda.Function };
  PyLambdaFunctions: { [key: string]: lambda.Function };
  queues: { [key: string]: sqs.Queue };
}

export class IntegrationStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: IntegrationStackProps) {
    super(scope, id, props);

    const { TsLambdaFunctions, PyLambdaFunctions, queues } = props;

    // --- Additional environment Variables for PyLambdaFunctions ---
    PyLambdaFunctions.realtimeLCDIApiLambda.addEnvironment('EXTERNAL_API_LAMBDA_ARN', TsLambdaFunctions.externalApiLambda.functionArn);
    PyLambdaFunctions.realtimeLCDISqsLambda.addEnvironment('EXTERNAL_API_LAMBDA_ARN', TsLambdaFunctions.externalApiLambda.functionArn);
    PyLambdaFunctions.domainModelLambda.addEnvironment('EXTERNAL_API_LAMBDA_ARN', TsLambdaFunctions.externalApiLambda.functionArn);
    
    // External API Lambda invocation permissions for PyLambdaFunctions
    TsLambdaFunctions.externalApiLambda.grantInvoke(PyLambdaFunctions.realtimeLCDIApiLambda);
    TsLambdaFunctions.externalApiLambda.grantInvoke(PyLambdaFunctions.realtimeLCDISqsLambda);
    TsLambdaFunctions.externalApiLambda.grantInvoke(PyLambdaFunctions.domainModelLambda);

    // --- API Gateway ---
    const api = new apigateway.RestApi(this, 'Maestro', {
      restApiName: 'Dev API Service',
      deployOptions: { 
        stageName: 'dev',
        description: 'Development stage with complete CRUD and delete operations',
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: [
          ...apigateway.Cors.DEFAULT_HEADERS,
          'X-Request-ID',
          'X-Api-Version',
        ],
      },
      description: 'M4ESTRO API Gateway with comprehensive database management',
    });

    // --- Database API Integrations ---
    const databaseIntegration = new apigateway.LambdaIntegration(TsLambdaFunctions.databaseManagerLambda, {

      proxy: true,
      integrationResponses: [
        {
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': "'*'",
          },
        },
        {
          statusCode: '400',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': "'*'",
          },
        },
        {
          statusCode: '500',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': "'*'",
          },
        },
      ],
    });

    // Common method response parameters for CORS
    const commonMethodResponses = [
      {
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      },
      {
        statusCode: '400',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      },
      {
        statusCode: '404',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      },
      {
        statusCode: '500',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      },
    ];

    // --- Database API Routes ---
    const dbResource = api.root.addResource('db');
    
    // Health check endpoint - GET /db/health
    const healthResource = dbResource.addResource('health');
    healthResource.addMethod('GET', databaseIntegration, {
      methodResponses: commonMethodResponses,
    });
    
    // Migration endpoint - GET /db/migration
    const migrationResource = dbResource.addResource('migration');
    migrationResource.addMethod('GET', databaseIntegration, {
      methodResponses: commonMethodResponses,
    });
    
    // Tables endpoint - GET /db/tables (list all tables)
    const tablesResource = dbResource.addResource('tables');
    tablesResource.addMethod('GET', databaseIntegration, {
      methodResponses: commonMethodResponses,
    });
    
    // Table operations with proxy - /db/tables/{tableName+}
    // This handles:
    // - GET /db/tables/{tableName} (get table info)
    // - GET /db/tables/{tableName}/data (get table data)
    // - GET /db/tables/{tableName}/data/{id} (get record by ID)
    // - POST /db/tables/{tableName} (insert data)
    // - PUT /db/tables/{tableName}/{id} (update record)
    // - DELETE /db/tables/{tableName}/{id} (delete single record)
    // - DELETE /db/tables/{tableName}/all-records (delete all records)
    const tableProxyResource = tablesResource.addResource('{tableName+}');
    tableProxyResource.addMethod('GET', databaseIntegration, {
      methodResponses: commonMethodResponses,
      requestParameters: {
        'method.request.path.tableName': true,
      },
    });
    tableProxyResource.addMethod('POST', databaseIntegration, {
      methodResponses: [
        {
          statusCode: '201',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
        ...commonMethodResponses,
      ],
    });
    tableProxyResource.addMethod('PUT', databaseIntegration, {
      methodResponses: commonMethodResponses,
    });
    tableProxyResource.addMethod('DELETE', databaseIntegration, {
      methodResponses: commonMethodResponses,
    });
    
    // Bulk operations endpoint - POST /db/bulk
    const bulkResource = dbResource.addResource('bulk');
    bulkResource.addMethod('POST', databaseIntegration, {
      methodResponses: commonMethodResponses,
    });
    
    // Bulk delete endpoint - DELETE /db/bulk-delete/{tableName}
    const bulkDeleteResource = dbResource.addResource('bulk-delete');
    const bulkDeleteTableResource = bulkDeleteResource.addResource('{tableName}');
    bulkDeleteTableResource.addMethod('DELETE', databaseIntegration, {
      methodResponses: commonMethodResponses,
      requestParameters: {
        'method.request.path.tableName': true,
      },
    });
    
    // Raw query endpoint - POST /db/query
    const queryResource = dbResource.addResource('query');
    queryResource.addMethod('POST', databaseIntegration, {
      methodResponses: commonMethodResponses,
    });

    // --- Business Logic API Routes ---
    
    // Order injestor endpoint - /injestor
    const injestorResource = api.root.addResource('injestor');
    injestorResource.addMethod('GET', new apigateway.LambdaIntegration(TsLambdaFunctions.injestorLambda, {

    }), {
      methodResponses: commonMethodResponses,
    });
    injestorResource.addMethod('POST', new apigateway.LambdaIntegration(TsLambdaFunctions.injestorLambda, {

    }), {
      methodResponses: [
        {
          statusCode: '201',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
        ...commonMethodResponses,
      ],
    });

    const recentDisruptionsResource = api.root.addResource('recent');

// GET /disruptions?order_id=123
recentDisruptionsResource.addMethod('GET', new apigateway.LambdaIntegration(TsLambdaFunctions.recentDisruptionsLambda, {
  proxy: true,
  integrationResponses: [
    {
      statusCode: '200',
      responseParameters: {
        'method.response.header.Access-Control-Allow-Origin': "'*'",
      },
    },
    {
      statusCode: '400',
      responseParameters: {
        'method.response.header.Access-Control-Allow-Origin': "'*'",
      },
    },
    {
      statusCode: '500',
      responseParameters: {
        'method.response.header.Access-Control-Allow-Origin': "'*'",
      },
    },
  ],
}), {
  methodResponses: commonMethodResponses,
  apiKeyRequired: false,
});

    // Orders endpoints - /orders
    const ordersResource = api.root.addResource('orders');
    ordersResource.addMethod('GET', new apigateway.LambdaIntegration(PyLambdaFunctions.domainModelLambda, {
      }), {
        methodResponses: commonMethodResponses,
    });

    const orderIdResource = ordersResource.addResource('{id}');
    orderIdResource.addMethod('GET', new apigateway.LambdaIntegration(PyLambdaFunctions.domainModelLambda, {
      }), {
        methodResponses: commonMethodResponses,
        requestParameters: {
          'method.request.path.id': true,
        },
    });

    orderIdResource.addMethod('PATCH', new apigateway.LambdaIntegration(PyLambdaFunctions.domainModelLambda, {
      }), {
        methodResponses: commonMethodResponses,
        requestParameters: {
          'method.request.path.id': true,
        },
      });

    // Vertex endpoints - /vertices
    const verticesResource = api.root.addResource('vertices');
    verticesResource.addMethod('GET', new apigateway.LambdaIntegration(PyLambdaFunctions.domainModelLambda, {
      }), {
        methodResponses: commonMethodResponses,
    });

    const vertexIdResource = verticesResource.addResource('{id}');
    vertexIdResource.addMethod('GET', new apigateway.LambdaIntegration(PyLambdaFunctions.domainModelLambda, {
      }), {
        methodResponses: commonMethodResponses,
        requestParameters: {
          'method.request.path.id': true,
        },
    });

    

    // --- LCDI API Routes ---

    // Main LCDI endpoint - /lcdi
    const lcdiResource = api.root.addResource('lcdi');
    lcdiResource.addMethod('GET', new apigateway.MockIntegration({
      integrationResponses: [{
        statusCode: '204',
        responseTemplates: {
          'application/json': '',
        },
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': "'*'",
        },
      }],
      passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
      requestTemplates: {
        'application/json': '{"statusCode": 204}'
      },
    }), {
      methodResponses: [
        {
          statusCode: '204',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        }
      ],
    });

    // Historical LCDI endpoints - /lcdi/historical/*
    const historicalLCDIResource = lcdiResource.addResource('historical');
    
    // Direct method on /lcdi/historical 
    historicalLCDIResource.addMethod('GET', new apigateway.LambdaIntegration(PyLambdaFunctions.histLCDILambda, {
      }), {
        methodResponses: commonMethodResponses,
    });
    
    // Proxy resource to capture all subpaths under /lcdi/historical/**
    const histProxy = historicalLCDIResource.addResource('{proxy+}');
    histProxy.addMethod('GET', new apigateway.LambdaIntegration(PyLambdaFunctions.histLCDILambda, {
      }), {
        methodResponses: commonMethodResponses,
        requestParameters: {
          'method.request.path.proxy': true,
        },
    });

    // Realtime LCDI endpoints - /lcdi/realtime
    const realtimeLCDIResource = lcdiResource.addResource('realtime');
    realtimeLCDIResource.addMethod('GET', new apigateway.LambdaIntegration(PyLambdaFunctions.realtimeLCDIApiLambda, {
      }), {
        methodResponses: commonMethodResponses,
    });
    realtimeLCDIResource.addMethod('POST', new apigateway.LambdaIntegration(PyLambdaFunctions.realtimeLCDIApiLambda, {
      }), {
        methodResponses: commonMethodResponses,
    });
    const realtimeLCDIVolatileResource = realtimeLCDIResource.addResource('volatile');
    realtimeLCDIVolatileResource.addMethod('POST', new apigateway.LambdaIntegration(PyLambdaFunctions.realtimeLCDIApiLambda, {
      }), {
        methodResponses: commonMethodResponses,
    });

    // Supply Chain Graph endpoints - /lcdi/sc-graph
    const scGraphResource = lcdiResource.addResource('sc-graph');
    scGraphResource.addMethod('GET', new apigateway.LambdaIntegration(PyLambdaFunctions.graphManagerLambda, {
      }), {
        methodResponses: commonMethodResponses,
    });
    scGraphResource.addMethod('POST', new apigateway.LambdaIntegration(PyLambdaFunctions.graphManagerLambda, {
      }), {
        methodResponses: commonMethodResponses,
    });

    const scGraphPathsResource = scGraphResource.addResource('paths');
    scGraphPathsResource.addMethod('GET', new apigateway.LambdaIntegration(PyLambdaFunctions.realtimeLCDIApiLambda, {
      }), {
        methodResponses: commonMethodResponses,
    });

    // --- Lambda Permissions ---
    // Grant TypeScript Lambda functions permission to invoke each other
    
    // External API Lambda can be invoked by other TS functions
    TsLambdaFunctions.externalApiLambda.grantInvoke(TsLambdaFunctions.injestorLambda);
    TsLambdaFunctions.externalApiLambda.grantInvoke(TsLambdaFunctions.periodicLambda);
    
    // Carrier Lambda can be invoked by injestor and periodic
    TsLambdaFunctions.carrierLambda.grantInvoke(TsLambdaFunctions.injestorLambda);
    TsLambdaFunctions.carrierLambda.grantInvoke(TsLambdaFunctions.periodicLambda);
    
    // Database manager can be invoked by all functions
    Object.values(TsLambdaFunctions).forEach(func => {
      if (func !== TsLambdaFunctions.databaseManagerLambda) {
        TsLambdaFunctions.databaseManagerLambda.grantInvoke(func);
      }
    });

    // --- API Documentation ---
    
    // Add API documentation
    const apiDocumentation = api.addUsagePlan('MaestroUsagePlan', {
      name: 'M4ESTRO API Usage Plan',
      description: 'Usage plan for M4ESTRO API with rate limiting',
      throttle: {
        rateLimit: 1000,
        burstLimit: 2000,
      },
      quota: {
        limit: 10000,
        period: apigateway.Period.DAY,
      },
    });

    // --- CloudFormation Outputs ---
    
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: api.url,
      description: 'The URL of the API Gateway',
      exportName: 'MaestroApiUrl',
    });

    new cdk.CfnOutput(this, 'ApiId', {
      value: api.restApiId,
      description: 'The ID of the API Gateway',
      exportName: 'MaestroApiId',
    });

    new cdk.CfnOutput(this, 'DatabaseEndpoints', {
      value: JSON.stringify({
        health: `${api.url}db/health`,
        migration: `${api.url}db/migration`,
        tables: `${api.url}db/tables`,
        bulk: `${api.url}db/bulk`,
        bulkDelete: `${api.url}db/bulk-delete/{tableName}`,
        query: `${api.url}db/query`,
      }),
      description: 'Database API endpoints',
      exportName: 'MaestroDatabaseEndpoints',
    });

    new cdk.CfnOutput(this, 'BusinessEndpoints', {
      value: JSON.stringify({
        injestor: `${api.url}injestor`,
        deliveryPlan: `${api.url}plan`,
        orders: `${api.url}orders`,
        lcdi: `${api.url}lcdi`,
      }),
      description: 'Business logic API endpoints',
      exportName: 'MaestroBusinessEndpoints',
    });

    // --- Resource-based Policy (Optional) ---
    // Uncomment if you need IP-based restrictions
    /*
    api.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      principals: [new iam.AnyPrincipal()],
      actions: ['execute-api:Invoke'],
      resources: [api.arnForExecuteApi()],
      conditions: {
        IpAddress: {
          'aws:SourceIp': ['YOUR_IP_RANGE/CIDR']
        }
      }
    }));
    */
  }
}