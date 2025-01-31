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

import { BedrockBatchSfn } from "@cdklabs/generative-ai-cdk-constructs";
import { generatePhysicalNameV2 } from "@cdklabs/generative-ai-cdk-constructs/lib/common/helpers/utils";
import {
  ArnFormat,
  aws_iam as iam,
  aws_logs as logs,
  aws_s3 as s3,
  aws_stepfunctions as sfn,
  aws_stepfunctions_tasks as tasks,
  Duration,
  Stack,
} from "aws-cdk-lib";

import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";
import { AnalyzeRepoFunction } from "./analyze-repo-function";
import { ProcessFindingsFunction } from "./process-findings-function";
import { BedrockInferencePolicy } from "../bedrock/inference-policy";

export interface CodeExpertWorkflowProps {
  readonly inputBucket: s3.IBucket;
  readonly outputBucket: s3.IBucket;
  readonly configBucket: s3.IBucket;
  readonly bedrockBatchBucket: s3.IBucket;
  readonly modelId: string;
}

export class CodeExpertWorkflow extends Construct {
  public readonly stateMachine: sfn.StateMachine;

  constructor(scope: Construct, id: string, props: CodeExpertWorkflowProps) {
    super(scope, id);

    const defaultParameters = new sfn.Pass(this, "DefaultParameters", {
      resultPath: "$.inputDefaults",
      parameters: {
        model_id: props.modelId,
        multiple_evaluation: true,
      },
    });

    const applyDefaults = new sfn.Pass(this, "ApplyDefaults", {
      resultPath: "$.withDefaults",
      outputPath: "$.withDefaults.args",
      parameters: {
        args: sfn.JsonPath.jsonMerge(
          sfn.JsonPath.objectAt("$.inputDefaults"),
          sfn.JsonPath.objectAt("$$.Execution.Input"),
        ),
      },
    });

    const analyzeRepoFunction = new AnalyzeRepoFunction(
      this,
      "AnalyzeRepoFunction",
      {
        configBucket: props.configBucket,
        inputBucket: props.inputBucket,
        bedrockBatchBucket: props.bedrockBatchBucket,
        modelId: props.modelId,
      },
    );

    const analyzeRepoTask = new tasks.LambdaInvoke(this, "AnalyzeRepoTask", {
      lambdaFunction: analyzeRepoFunction,
      payloadResponseOnly: true,
      resultPath: "$.analyzeRepo",
    });

    const batchInput = new sfn.Pass(this, "BatchInput", {
      resultPath: "$.batchInput",
      parameters: {
        job_name: sfn.JsonPath.stringAt("$.analyzeRepo.job_name"),
        manifest_keys: sfn.JsonPath.stringAt("$.analyzeRepo.manifests"),
        model_id: sfn.JsonPath.stringAt("$.model_id"),
      },
    });

    const bedrockBatchPolicy =
      BedrockInferencePolicy.getBedrockInferencePolicy(this);

    const batchEvaluate = new BedrockBatchSfn(this, "BatchEvaluate", {
      bedrockBatchInputBucket: props.bedrockBatchBucket,
      bedrockBatchOutputBucket: props.bedrockBatchBucket,
      bedrockBatchPolicy: bedrockBatchPolicy,
      timeout: Duration.days(3),
      inputPath: "$.batchInput",
      resultPath: "$.batchEvaluateMap",
    });

    const processFindingsFunction = new ProcessFindingsFunction(
      this,
      "ProcessFindingsFunction",
      {
        bedrockBatchBucket: props.bedrockBatchBucket,
        outputBucket: props.outputBucket,
        modelId: props.modelId,
      },
    );

    const processFindingsTask = new tasks.LambdaInvoke(
      this,
      "ProcessFindingsTask",
      {
        lambdaFunction: processFindingsFunction,
        payloadResponseOnly: true,
        payload: sfn.TaskInput.fromObject({
          job_name: sfn.JsonPath.stringAt("$.analyzeRepo.job_name"),
          jobs: sfn.JsonPath.listAt("$.batchEvaluateMap"),
          model_id: sfn.JsonPath.stringAt("$.model_id"),
        }),
        resultPath: "$.processFindings",
      },
    );

    const succeed = new sfn.Succeed(this, "Success");
    const chain = defaultParameters
      .next(applyDefaults)
      .next(analyzeRepoTask)
      .next(batchInput)
      .next(batchEvaluate)
      .next(processFindingsTask)
      .next(succeed);

    const logGroupName = generatePhysicalNameV2(
      this,
      "/aws/vendedlogs/states/",
    );
    const workflowLogs = new logs.LogGroup(this, "Logs", {
      retention: logs.RetentionDays.ONE_MONTH,
      logGroupName: logGroupName,
    });

    this.stateMachine = new sfn.StateMachine(this, "Workflow", {
      definitionBody: sfn.DefinitionBody.fromChainable(chain),
      tracingEnabled: true,
      logs: {
        destination: workflowLogs,
        level: sfn.LogLevel.ALL,
      },
    });

    NagSuppressions.addResourceSuppressions(
      this.stateMachine,
      [
        {
          id: "AwsSolutions-IAM5",
          reason:
            "The policy has wildcards to call specific Lambda functions and their aliases ",
        },
      ],
      true,
    );

    const redrivePolicy = new iam.Policy(this, "WorkflowPolicy", {
      statements: [
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: ["states:RedriveExecution"],
          resources: [
            Stack.of(this).formatArn({
              service: "states",
              resource: "execution",
              resourceName: `${this.stateMachine.stateMachineName}/*`,
              arnFormat: ArnFormat.COLON_RESOURCE_NAME,
            }),
          ],
        }),
      ],
    });
    this.stateMachine.role.attachInlinePolicy(redrivePolicy);
    NagSuppressions.addResourceSuppressions(
      redrivePolicy,
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "The policy has wildcards to redrive SFN executions.",
        },
      ],
      false,
    );
  }
}
