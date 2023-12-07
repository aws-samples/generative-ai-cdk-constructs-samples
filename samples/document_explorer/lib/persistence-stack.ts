import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Stack, StackProps } from 'aws-cdk-lib';

import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';

//-----------------------------------------------------------------------------
// Stack Properties
//-----------------------------------------------------------------------------
export interface PersistenceProps extends StackProps {
  vpc: ec2.Vpc;
  securityGroups: ec2.SecurityGroup[];
  masterNodes: 1 | 3 | 5;
  dataNodes: number;
  masterNodeInstanceType: 't3.small.search' | 't3.medium.search' | 'm6g.4xlarge.search' | 'm6g.8xlarge.search';
  dataNodeInstanceType: 't3.small.search' | 't3.medium.search' | 'r6g.4xlarge.search' | 'r6g.8xlarge.search';
  availabilityZoneCount:number;
  volumeSize: number;
  removalPolicy: cdk.RemovalPolicy;
}

//-----------------------------------------------------------------------------
// Persistence Stack
//-----------------------------------------------------------------------------
export class PersistenceStack extends Stack {
  public readonly inputsAssetsBucket: s3.Bucket;
  public readonly processedAssetsBucket: s3.Bucket;
  public readonly opensearchDomain: opensearch.Domain;

  constructor(scope: Construct, id: string, props: PersistenceProps) {
    super(scope, id, props);

      //---------------------------------------------------------------------
      // S3 - Input Assets
      //---------------------------------------------------------------------
      this.inputsAssetsBucket = new s3.Bucket(this, 'InputsAssets', {
        enforceSSL: true,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        encryption: s3.BucketEncryption.S3_MANAGED,
        removalPolicy: props.removalPolicy,
        cors: [
          {
            allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
            allowedOrigins: [
              'http://localhost:5173'
            ],
            allowedHeaders: ['*'],
            exposedHeaders: ['Access-Control-Allow-Origin'],
          },
        ],
      });


      //---------------------------------------------------------------------
      // S3 - Processed Assets
      //---------------------------------------------------------------------
      this.processedAssetsBucket = new s3.Bucket(this, 'ProcessedAssets', {
        enforceSSL: true,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        encryption: s3.BucketEncryption.S3_MANAGED,
        removalPolicy: props.removalPolicy,
        cors: [
          {
            allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
            allowedOrigins: [
              'http://localhost:5173'
            ],
            allowedHeaders: ['*'],
            exposedHeaders: ['Access-Control-Allow-Origin'],
          },
        ],
      });

      //---------------------------------------------------------------------
      // OpenSearch Domain
      //---------------------------------------------------------------------
      this.opensearchDomain = new opensearch.Domain(this, 'opensearch', {
        version: opensearch.EngineVersion.OPENSEARCH_2_9,
        enableVersionUpgrade: true,
        capacity: {
          masterNodes: props.masterNodes,
          masterNodeInstanceType: props.masterNodeInstanceType,
          dataNodes: props.dataNodes,
          dataNodeInstanceType: props.masterNodeInstanceType,
        },
        vpc: props.vpc,
        securityGroups: props.securityGroups,
        zoneAwareness: { availabilityZoneCount: props.availabilityZoneCount },
        ebs: {
          volumeType: ec2.EbsDeviceVolumeType.GP3,
          volumeSize: props.volumeSize,
        },
        nodeToNodeEncryption: true,
        encryptionAtRest: {
          enabled: true,
        },
        enforceHttps: true,
        logging: {
          slowSearchLogEnabled: true,
          appLogEnabled: true,
          slowIndexLogEnabled: true,
        },
        tlsSecurityPolicy: opensearch.TLSSecurityPolicy.TLS_1_2,
        removalPolicy: props.removalPolicy,
      });

      //---------------------------------------------------------------------
      // Service Access Policy
      //---------------------------------------------------------------------
      this.opensearchDomain.addAccessPolicies(
        new iam.PolicyStatement({
          actions: ['es:*'],
          principals: [new iam.AccountPrincipal(cdk.Stack.of(this).account)],
          effect: iam.Effect.ALLOW,
          resources: [this.opensearchDomain.domainArn, `${this.opensearchDomain.domainArn}/*`],
        }),
      );

      //---------------------------------------------------------------------
      // Export values
      //---------------------------------------------------------------------
      new cdk.CfnOutput(this, "S3InputBucket", {
        value: this.inputsAssetsBucket.bucketName,
      });
      new cdk.CfnOutput(this, "S3ProcessedBucket", {
        value: this.processedAssetsBucket.bucketName,
      });

    }
}