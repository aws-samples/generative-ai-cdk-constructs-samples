/**
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 *  with the License. A copy of the License is located at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 *  and limitations under the License.
 */

import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as sm from 'aws-cdk-lib/aws-sagemaker';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as s3assets from 'aws-cdk-lib/aws-s3-assets';
import * as genai from '@cdklabs/generative-ai-cdk-constructs';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import * as path from 'path';

export class GenaiDeployStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create a new VPC
    const vpc = new ec2.Vpc(this, 'LLMExperimentVpc', {
      maxAzs: 2,
    });

    // Create VPC Endpoints for private connectivity
    vpc.addInterfaceEndpoint('SageMakerAPIVpcEndpoint', {
      service: ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_API,
    });
    vpc.addGatewayEndpoint('S3VpcEndpoint', {
      service: ec2.GatewayVpcEndpointAwsService.S3,
    });
    vpc.addInterfaceEndpoint('SageMakerRuntimeVpcEndpoint', {
      service: ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_RUNTIME,
    });
    vpc.addInterfaceEndpoint('SageMakerNotebookVpcEndpoint', {
      service: ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_NOTEBOOK,
    });
    vpc.addInterfaceEndpoint('awslogsVpcEndpoint', {
      service: ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
    });

    // Declare which model to use from AWS Deep Learning Container Image
    const SM_ENDPOINT_NAME = 'TGIFalcon40B-Endpoint';
    const HUGGING_FACE_MODEL_ID = 'tiiuae/falcon-40b';

    // Create Log Group for SageMaker Inference Endpoint
    const endpointLogGroup = new logs.LogGroup(this, 'SageMakerEndpointLogGroup', {
      logGroupName: `/aws/sagemaker/Endpoints/${SM_ENDPOINT_NAME}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    // Create a Role for the SageMaker Inference Endpoint
    const sageMakerModelRole = new iam.Role(this, 'sageMakerModelRole', {
      assumedBy: new iam.ServicePrincipal('sagemaker.amazonaws.com'),
      inlinePolicies: {
        CloudWatchMetrics: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              resources: ['*'],
              actions: ['cloudwatch:PutMetricData'],
            }),
          ],
        }),
      },
    });

    // Grant Logging permissions to Role for SageMaker Inference Endpoint
    endpointLogGroup.grantWrite(sageMakerModelRole);

    // Create a SageMaker Inference Endpoint from the GenAI Constructs
    const HuggingFaceEndpoint = new genai.HuggingFaceSageMakerEndpoint(
      this,
      'Endpoint',
      {
        modelId: HUGGING_FACE_MODEL_ID,
        instanceType: genai.SageMakerInstanceType.ML_G4DN_12XLARGE,
        startupHealthCheckTimeoutInSeconds: 900,
        container:
          genai.DeepLearningContainerImage.fromDeepLearningContainerImage(
            'huggingface-pytorch-tgi-inference',
            '2.0.1-tgi1.0.3-gpu-py39-cu118-ubuntu20.04',
            '442386744353'
          ),
        environment: {
          SM_NUM_GPUS: '4',
          MAX_INPUT_LENGTH: '1024',
          MAX_TOTAL_TOKENS: '2048',
          HF_MODEL_QUANTIZE: 'bitsandbytes-nf4',
          HUGGINGFACE_HUB_CACHE: '/tmp/huggingface',
          SAGEMAKER_CONTAINER_LOG_LEVEL: '20',
          SAGEMAKER_REGION: `${cdk.Aws.REGION}`,
        },
        endpointName: SM_ENDPOINT_NAME,
        role: sageMakerModelRole,
      }
    );

    // Output the SageMaker Endpoint's Arn
    new cdk.CfnOutput(this, 'SageMakerEndpointArn', {
      value: HuggingFaceEndpoint.endpointArn,
    });

    // Define name for SageMaker Notebook Instance to test Endpoint invocation
    const NOTEBOOK_NAME = 'TGIFalcon40BNotebook';

    // Upload .ipynb into S3 to go to SageMaker Notebook Instance
    const asset = new s3assets.Asset(this, 'SampleAsset', {
      path: path.join(__dirname, 'sagemaker-notebook'),
    });


    // Create Role for SageMaker Notebook Instance and grant Log Permissions
    const notebookRole = new iam.Role(this, 'NotebookRole', {
      assumedBy: new iam.ServicePrincipal('sagemaker.amazonaws.com'),
    });

    // Grant the Notebook Role permission to invoke Inference Endpoint
    HuggingFaceEndpoint.grantInvoke(notebookRole);

    // Allow the Notebook Role logging permissions to the associated log group
    notebookRole.addToPrincipalPolicy(new iam.PolicyStatement({
      resources: [
        // Arns for Log Group and Log Streams
        cdk.Arn.format(
          { service: 'logs', resource: 'log-group:/aws/sagemaker/NotebookInstances' },
          this
        ),
        cdk.Arn.format(
          { service: 'logs', resource: 'log-group:/aws/sagemaker/NotebookInstances*' },
          this
        ),
      ],
      actions: [
        'logs:CreateLogStream',
        'logs:PutLogEvents',
        'logs:CreateLogGroup',
        'logs:DescribeLogStreams',
      ],
    }));

    // Create Notebook Instance Security Group and KMS Key
    const notebookSg = new ec2.SecurityGroup(this, 'notebookSg', {
      vpc: vpc,
    });

    const sageMakerKey = new kms.Key(this, 'NotebookKey', {
      enableKeyRotation: true,
    });

    // Create SageMaker Notebook Instance
    const notebookInstance = new sm.CfnNotebookInstance(this, NOTEBOOK_NAME, {
      instanceType: 'ml.t2.medium',
      roleArn: notebookRole.roleArn,
      platformIdentifier: 'notebook-al2-v2',
      volumeSizeInGb: 50,
      directInternetAccess: 'Disabled',
      subnetId: vpc.privateSubnets[0].subnetId,
      securityGroupIds: [notebookSg.securityGroupId],
      kmsKeyId: sageMakerKey.keyId,
      lifecycleConfigName: 'notebookInstanceLifecycleConfigName',
    });

    // ensure the S3 Read permissions happen before the Notebook Instance Creates and attempts to download the .ipynb Asset
    asset.bucket.grantRead(notebookRole).applyBefore(notebookInstance);

    // Place the test .ipynb asset into the SageMaker Notebook Instance after instance create
    new sm.CfnNotebookInstanceLifecycleConfig(
      this,
      'notebookInstanceLifecycleConfig',
      {
        notebookInstanceLifecycleConfigName:
          'notebookInstanceLifecycleConfigName',
        onCreate: [
          {
            content: cdk.Fn.base64(
              `aws s3 cp ${asset.s3ObjectUrl} asset.zip && unzip asset.zip -d /home/ec2-user/SageMaker`
            ),
          },
        ],
      }
    );
  }
}
