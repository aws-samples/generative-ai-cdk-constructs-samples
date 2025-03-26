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

// NodeJS Built-Ins:
import * as path from "path";

// External Dependencies:
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";

export interface IDemoInvokersProps {
  /**
   * URL of the Langfuse deployment to connect to (including protocol e.g. https://)
   * 
   * @default "https://cloud.langfuse.com" Langfuse public cloud (US)
   */
  langfuseUrl: string;
  /**
   * Optional tags to apply to created resources
   */
  tags?: cdk.Tag[];
}

/**
 * Construct for example Lambda function(s) that invoke Amazon Bedrock and log traces to Langfuse
 */
export class DemoInvokers extends Construct {
  /**
   * (Shared) execution role used by the example Lambda functions
   * 
   * This role is granted fairly broad permissions to invoke models/agents/etc on Bedrock
   */
  public readonly invokeRole: iam.Role;
  /**
   * (Shared) Langfuse secret used by the example Lambda functions
   *
   * This secret must be manually initialized with a {public_key, secret_key} pair created from the
   * Langfuse UI.
   */
  public readonly keySecret: secretsmanager.Secret;

  constructor(scope: Construct, id: string, props: IDemoInvokersProps) {
    super(scope, id);
    const langfuseUrl = props.langfuseUrl || "https://cloud.langfuse.com";

    this.keySecret = new secretsmanager.Secret(this, "Key", {
      description: "Demo Langfuse {public_key, secret_key} pair (must be initialized by user)",
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      secretObjectValue: {
        public_key: cdk.SecretValue.unsafePlainText("PLACEHOLDER"),
        secret_key: cdk.SecretValue.unsafePlainText("PLACEHOLDER"),
      },
    });
    if (props.tags) {
      props.tags.forEach((tag) => cdk.Tags.of(this.keySecret).add(tag.key, tag.value));
    }
    NagSuppressions.addResourceSuppressions(this.keySecret, [
      {
        id: "AwsSolutions-SMG4",
        reason: "Rotation requires manual action in Langfuse UI",
      },
    ]);

    new cdk.CfnOutput(this, "LangfuseKeyPairSecret", {
      value: this.keySecret.secretName,
    });

    this.invokeRole = new iam.Role(this, "InvokeRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      inlinePolicies: {
        LangfuseInvoke: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: [
                "bedrock:ApplyGuardrail",
                "bedrock:CreateInvocation",
                "bedrock:CreateSession",
                // "bedrock:DeleteSession",
                "bedrock:EndSession",
                "bedrock:GenerateQuery",
                "bedrock:GetAgent",
                "bedrock:GetAsyncInvoke",
                "bedrock:GetInferenceProfile",
                "bedrock:GetPrompt",
                "bedrock:GetProvisionedModelThroughput",
                "bedrock:GetSession",
                "bedrock:IngestKnowledgeBaseDocuments",
                "bedrock:InvokeAgent",
                "bedrock:InvokeDataAutomationAsync",
                "bedrock:InovkeFlow",
                "bedrock:InvokeInlineAgent",
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:OptimizePrompt",
                "bedrock:PutInvocationStep",
                "bedrock:RenderPrompt",
                "bedrock:Rerank",
                "bedrock:Retrieve",
                "bedrock:RetrieveAndGenerate",
                "bedrock:TagResource",
                "bedrock:UpdateSession",
              ],
              resources: ["*"],
            }),
          ],
        }),
      },
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"),
      ],
    });
    this.keySecret.grantRead(this.invokeRole);
    if (props.tags) {
      props.tags.forEach((tag) => cdk.Tags.of(this.invokeRole).add(tag.key, tag.value));
    }
    NagSuppressions.addResourceSuppressions(
      this.invokeRole,
      [
        {
          id: "AwsSolutions-IAM4",
          reason: "Allow AWSLambdaBasicExecutionRole for example invocation Lambdas",
        },
        {
          id: "AwsSolutions-IAM5",
          reason: "Function can invoke all Bedrock agents/models/etc by design",
        },
      ],
      true,
    );

    const langchainInvokeFn = new PythonFunction(this, "LcLfInvoke", {
      runtime: lambda.Runtime.PYTHON_3_13,
      entry: path.join(__dirname, "..", "assets", "functions", "invoke-langchain"),
      environment: {
        LANGFUSE_HOST: props.langfuseUrl,
        LANGFUSE_SECRET_ID: this.keySecret.secretArn,
      },
      paramsAndSecrets: lambda.ParamsAndSecretsLayerVersion.fromVersion(
        lambda.ParamsAndSecretsVersions.V1_0_103,
      ),
      role: this.invokeRole,
      timeout: cdk.Duration.minutes(3),
      // adotInstrumentation: {
      //   layerVersion: lambda.AdotLayerVersion.fromPythonSdkLayerVersion(
      //     lambda.AdotLambdaLayerPythonSdkVersion.LATEST,
      //   ),
      //   execWrapper: lambda.AdotLambdaExecWrapper.INSTRUMENT_HANDLER,
      // },
      tracing: lambda.Tracing.ACTIVE,
    });
    // A tracing Policy gets auto-created as a child of the PythonFunction construct, separate from
    // the invokeRole we created and configured cdk-nag for above:
    NagSuppressions.addResourceSuppressions(
      langchainInvokeFn,
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "No resource restriction possible for xray:PutTelemetryRecords & PutTraceSegments",
        },
      ],
      true,
    );
    if (props.tags) {
      props.tags.forEach((tag) => cdk.Tags.of(langchainInvokeFn).add(tag.key, tag.value));
    }

    new cdk.CfnOutput(this, "LangchainInvokeFn", {
      value: langchainInvokeFn.functionName,
    });
  }
}
