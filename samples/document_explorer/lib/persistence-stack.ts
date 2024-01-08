import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Stack, StackProps } from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';

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
  masterNodeInstanceType: 'm6g.large.search' | 'm6g.4xlarge.search' | 'm6g.8xlarge.search';
  dataNodeInstanceType: 'm6g.large.search' | 'r6g.4xlarge.search' | 'r6g.8xlarge.search';
  availabilityZoneCount:number;
  volumeSize: number;
  removalPolicy: cdk.RemovalPolicy;
  logRemovalPolicy: cdk.RemovalPolicy;
}

//-----------------------------------------------------------------------------
// Persistence Stack
//-----------------------------------------------------------------------------
export class PersistenceStack extends Stack {
  public readonly accesslogBucket: s3.Bucket;
  public readonly inputsAssetsBucket: s3.Bucket;
  public readonly processedAssetsBucket: s3.Bucket;
  public readonly opensearchDomain: opensearch.Domain;

  constructor(scope: Construct, id: string, props: PersistenceProps) {
    super(scope, id, props);

      //---------------------------------------------------------------------
      // S3 - Input Access Logs
      //---------------------------------------------------------------------
      // 
      this.accesslogBucket = new s3.Bucket(this, 'AccessLogs', {
        enforceSSL: true,
        versioned: true,
        publicReadAccess: false,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        encryption: s3.BucketEncryption.S3_MANAGED,
        removalPolicy: props.logRemovalPolicy
      });
      NagSuppressions.addResourceSuppressions(this.accesslogBucket, [
        {id: 'AwsSolutions-S1', reason: 'There is no need to enable access logging for the AccessLogs bucket.'},
      ])

      //---------------------------------------------------------------------
      // S3 - Input Assets
      //---------------------------------------------------------------------
      this.inputsAssetsBucket = new s3.Bucket(this, 'InputsAssets', {
        enforceSSL: true,
        versioned: true,
        publicReadAccess: false,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        encryption: s3.BucketEncryption.S3_MANAGED,
        removalPolicy: props.removalPolicy,
        serverAccessLogsBucket: this.accesslogBucket,
        serverAccessLogsPrefix: 'inputsAssetsBucketLogs/',
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
        versioned: true,
        publicReadAccess: false,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        encryption: s3.BucketEncryption.S3_MANAGED,
        removalPolicy: props.removalPolicy,
        serverAccessLogsBucket: this.accesslogBucket,
        serverAccessLogsPrefix: 'processedAssetsBucketLogs/',
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
          actions: [
            'es:ESHttpDelete',
            'es:ESHttpGet',
            'es:ESHttpHead',
            'es:ESHttpPost',
            'es:ESHttpPut'
          ],
          principals: [new iam.AccountPrincipal(cdk.Stack.of(this).account)],
          effect: iam.Effect.ALLOW,
          resources: [this.opensearchDomain.domainArn, `${this.opensearchDomain.domainArn}/*`],
          conditions: {
            StringEquals: {
              'aws:SourceVpc': props.vpc.vpcId
            }
          }
        }),
      );
      NagSuppressions.addResourceSuppressions(this.opensearchDomain, [
        {id: 'AwsSolutions-OS3', reason: 'Access policy restricting access to the VPC'},
        {id: 'AwsSolutions-IAM5', reason: 'Access policy restricting access to the VPC'},
      ])

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