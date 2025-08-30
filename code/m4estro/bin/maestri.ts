
import * as cdk from 'aws-cdk-lib';
import { InfrastructureStack } from '../lib/InfrastructureStack';
import { LambdaTsStack } from '../lib/lambdaTsStack';
import { LambdaPyStack} from '../lib/lambdaPyStack';
import { IntegrationStack } from '../lib/IntegrationStack';

const app = new cdk.App();

// Environment configuration
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'us-east-1'
};

// 1. Infrastructure Stack (foundational resources)
const infraStack = new InfrastructureStack(app, 'Maestro-backend-Infrastructure', {
  env,
  stackName: 'maestro-backend-infrastructure'
});


// // 2. TypeScript Services Stack
const tsStack = new LambdaTsStack(app, 'Maestro-TSlambda-Services', {
  env,
  stackName: 'maestro-backend-Tslambda',
  // Pass shared resources from infrastructure
  vpc: infraStack.vpc,
  database: infraStack.databaseCluster,
  databaseSecret: infraStack.databaseSecret,
  queues: infraStack.queues,
  securityGroups: infraStack.securityGroup,
});


// 3. Python Services Stack
const pythonStack = new LambdaPyStack(app, 'Maestro-PyLambda-Services', {
  env,
  stackName: 'maestro-backend-PyLambda',
  // Pass shared resources from infrastructure
  vpc: infraStack.vpc,
  database: infraStack.databaseCluster,
  databaseSecret: infraStack.databaseSecret,
  queues: infraStack.queues,
  securityGroups: infraStack.securityGroup,
});


// // // 4. Integration Stack (connects everything)
const integrationStack = new IntegrationStack(app, 'Maestro-Integration', {
  env,
  stackName: 'maestro-backend-integration',
  TsLambdaFunctions: tsStack.functions,
  PyLambdaFunctions: pythonStack.functions,
  queues: infraStack.queues
});  

// Stack dependencies
tsStack.addDependency(infraStack);
pythonStack.addDependency(infraStack);
integrationStack.addDependency(tsStack);
integrationStack.addDependency(pythonStack);

app.synth();