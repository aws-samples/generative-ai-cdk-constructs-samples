#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
// import * as cdknag from 'cdk-nag';

import { NetworkingStack } from '../lib/networking-stack';
import { PersistenceStack } from '../lib/persistence-stack';
import { ApiStack } from '../lib/api-stack';

const env = {
    region: process.env.CDK_DEFAULT_REGION,
    account: process.env.CDK_DEFAULT_ACCOUNT,
}
const app = new cdk.App();
cdk.Tags.of(app).add("app", "generative-ai-cdk-constructs-samples");

// cdk.Aspects.of(app).add(new cdknag.AwsSolutionsChecks({verbose:true}));

//-----------------------------------------------------------------------------
// Networking Layer
//-----------------------------------------------------------------------------
const network = new NetworkingStack(app, 'NetworkingStack', {env: env});
cdk.Tags.of(network).add("stacl", "network");

//-----------------------------------------------------------------------------
// Persistence Layer
//-----------------------------------------------------------------------------
const persistence = new PersistenceStack(app, 'PersistenceStack', {
  env: env,
  vpc: network.vpc,
  securityGroups: network.securityGroups,
  masterNodes: 3,
  dataNodes: 3,
  masterNodeInstanceType: 'm6g.4xlarge.search',
  dataNodeInstanceType: 'r6g.8xlarge.search',
  availabilityZoneCount: 3,
  volumeSize: 100,
  removalPolicy: cdk.RemovalPolicy.DESTROY
});
cdk.Tags.of(persistence).add("stack", "persistence");

//-----------------------------------------------------------------------------
// API Layer
//-----------------------------------------------------------------------------
const api = new ApiStack(app, 'ApiStack', {
  env: env,
  existingOpensearchDomain: persistence.opensearchDomain,
  existingVpc: network.vpc,
  existingSecurityGroup: network.securityGroups[0],
  existingInputAssetsBucketObj: persistence.inputsAssetsBucket,
  existingProcessedAssetsBucketObj: persistence.processedAssetsBucket,
  openSearchIndexName: 'joyride',
  cacheNodeType: 'cache.r6g.xlarge',
  engine: 'redis',
  numCacheNodes: 1,
  removalPolicy: cdk.RemovalPolicy.DESTROY,
  clientUrl: 'http://localhost:8501/'
});
cdk.Tags.of(api).add("stack", "api");