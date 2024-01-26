import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Stack, StackProps, ResourceProps } from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';

import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as openSearchServerless from 'aws-cdk-lib/aws-opensearchserverless';

//-----------------------------------------------------------------------------
// Stack Properties
//-----------------------------------------------------------------------------
export interface OpenSearchServiceProps extends ResourceProps {
  masterNodes: 1 | 3 | 5;
  dataNodes: number;
  masterNodeInstanceType: 'm6g.large.search' | 'm6g.4xlarge.search' | 'm6g.8xlarge.search';
  dataNodeInstanceType: 'm6g.large.search' | 'r6g.4xlarge.search' | 'r6g.8xlarge.search';
  availabilityZoneCount:number;
  volumeSize: number;
}

export interface OpenSearchServerlessProps extends ResourceProps {
  openSearchVpcEndpointId: string;
  collectionName: string;
}

export interface PersistenceProps extends StackProps {
  vpc: ec2.Vpc;
  securityGroups: ec2.SecurityGroup[];
  openSearchServiceType: 'es' | 'aoss';
  openSearchProps: ResourceProps;
  removalPolicy: cdk.RemovalPolicy;
}

//-----------------------------------------------------------------------------
// Persistence Stack
//-----------------------------------------------------------------------------
export class PersistenceStack extends Stack {
  public readonly accessLogsBucket: s3.Bucket;
  public readonly inputAssetsBucket: s3.Bucket;
  public readonly processedAssetsBucket: s3.Bucket;
  public readonly opensearchDomain: opensearch.Domain;
  public readonly opensearchCollection: openSearchServerless.CfnCollection;

  constructor(scope: Construct, id: string, props: PersistenceProps) {

    super(scope, id, props);

    //---------------------------------------------------------------------
    // S3 - Input Access Logs
    //---------------------------------------------------------------------
    this.accessLogsBucket = new s3.Bucket(this, 'AccessLogs', {
      enforceSSL: true,
      versioned: true,
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: props.removalPolicy
    });
    NagSuppressions.addResourceSuppressions(this.accessLogsBucket, [
      {id: 'AwsSolutions-S1', reason: 'There is no need to enable access logging for the AccessLogs bucket.'},
    ]);

    //---------------------------------------------------------------------
    // S3 - Input Assets
    //---------------------------------------------------------------------
    this.inputAssetsBucket = new s3.Bucket(this, 'InputAssets', {
      enforceSSL: true,
      versioned: true,
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: props.removalPolicy,
      autoDeleteObjects: props.removalPolicy == cdk.RemovalPolicy.DESTROY ? true : false,
      serverAccessLogsBucket: this.accessLogsBucket,
      serverAccessLogsPrefix: 'inputsAssetsBucketLogs/',
      cors: [
        {
          allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
          allowedOrigins: [
            'http://localhost:5173'
          ],
          allowedHeaders: ['*'],
          exposedHeaders: ['Access-Control-Allow-Origin'],
        }
      ]
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
      serverAccessLogsBucket: this.accessLogsBucket,
      serverAccessLogsPrefix: 'processedAssetsBucketLogs/',
      cors: [
        {
          allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
          allowedOrigins: [
            'http://localhost:5173'
          ],
          allowedHeaders: ['*'],
          exposedHeaders: ['Access-Control-Allow-Origin'],
        }
      ]
    });

    //---------------------------------------------------------------------
    // AWS OpenSearch Service
    //---------------------------------------------------------------------
    if (props.openSearchServiceType === 'es') {
      const openSearchProps = props.openSearchProps as OpenSearchServiceProps;
      this.opensearchDomain = new opensearch.Domain(this, 'opensearch', {
        version: opensearch.EngineVersion.OPENSEARCH_2_9,
        enableVersionUpgrade: true,
        capacity: {
          masterNodes: openSearchProps.masterNodes,
          masterNodeInstanceType: openSearchProps.masterNodeInstanceType,
          dataNodes: openSearchProps.dataNodes,
          dataNodeInstanceType: openSearchProps.masterNodeInstanceType,
        },
        vpc: props.vpc,
        securityGroups: props.securityGroups,
        zoneAwareness: { availabilityZoneCount: openSearchProps.availabilityZoneCount },
        ebs: {
          volumeType: ec2.EbsDeviceVolumeType.GP3,
          volumeSize: openSearchProps.volumeSize,
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

    } else if (props.openSearchServiceType === 'aoss') {
      const openSearchProps = props.openSearchProps as OpenSearchServerlessProps;
    
      // Encryption policy
      const encryptionPolicy = new openSearchServerless.CfnSecurityPolicy(this, `EncryptionPolicy`, {
        name: `${openSearchProps.collectionName}-encryption-policy`,
        type: 'encryption',
        policy: JSON.stringify({
          AWSOwnedKey: true,
          Rules: [
            {
              ResourceType: 'collection',
              Resource: [`collection/${openSearchProps.collectionName}`]
            }
          ]
        })
      });

      // Data Access Policy
      const accountId = Stack.of(this).account;
      const dataAccessPolicy = new openSearchServerless.CfnAccessPolicy(this, `DataAccessPolicy`, {
        name: `${openSearchProps.collectionName}-data-access-policy`,
        type: 'data', 
        policy: JSON.stringify([
          {
            Rules: [
              {
                ResourceType: 'index',
                Resource: [`index/${openSearchProps.collectionName}/*`],
                Permission: [
                  'aoss:CreateIndex',
                  'aoss:DescribeIndex',
                  'aoss:ReadDocument',
                  'aoss:WriteDocument',
                  'aoss:UpdateIndex',
                  'aoss:DeleteIndex'
                ]
              },
              {
                ResourceType: 'collection',
                Resource: [`collection/${openSearchProps.collectionName}`],
                Permission: ['aoss:*']
              }
            ],
            Principal: [`arn:aws:iam::${accountId}:root`]
          }
        ])
      });

      // Attach network policy to collection
      const networkPolicy = new openSearchServerless.CfnSecurityPolicy(this, `NetworkPolicy`, {
        name: `${openSearchProps.collectionName}-network-policy`,
        type: 'network',
        policy: JSON.stringify([
          {
            AllowFromPublic: false,
            Rules: [
              {
                ResourceType: 'collection',
                Resource: [`collection/${openSearchProps.collectionName}`]
              }
            ],
            SourceVPCEs: [openSearchProps.openSearchVpcEndpointId]
          },
          {
            AllowFromPublic: false, 
            Rules: [
              {
                ResourceType: 'dashboard',
                Resource: [`collection/${openSearchProps.collectionName}`]  
              }
            ],
            SourceVPCEs: [openSearchProps.openSearchVpcEndpointId]
          }
        ])
      });

      // Collection
      this.opensearchCollection = new openSearchServerless.CfnCollection(this, 'Collection', {
        name: openSearchProps.collectionName,
        description: 'Vector search collection',
        type: 'VECTORSEARCH'
      });
      this.opensearchCollection.addDependency(encryptionPolicy);
      this.opensearchCollection.addDependency(dataAccessPolicy);
      this.opensearchCollection.addDependency(networkPolicy);
    }

    //---------------------------------------------------------------------
    // Export values
    //---------------------------------------------------------------------
    new cdk.CfnOutput(this, "S3InputBucket", {
      value: this.inputAssetsBucket.bucketName 
    });

    new cdk.CfnOutput(this, "S3ProcessedBucket", {
      value: this.processedAssetsBucket.bucketName
    });

  }
}