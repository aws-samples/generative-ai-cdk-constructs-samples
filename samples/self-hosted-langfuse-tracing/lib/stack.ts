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

// External Dependencies:
import * as cdk from "aws-cdk-lib";
import { ILangfuseDeploymentProps, LangfuseDeployment, LangfuseVpcInfra } from "@cdklabs/generative-ai-cdk-constructs";
import { Construct } from "constructs";

// Local Dependencies:
import { DemoInvokers } from "./demo-invokers";

/**
 * Since the Langfuse pattern is quite complex, you may like to wrap it in a nested stack
 * 
 * you could use the LangfuseDeployment construct directly instead, but this can help keep large
 * patterns like these tidy and clearly separated.
 */
class LangfuseStack extends cdk.NestedStack {
  /**
   * Actual LangfuseDeployment construct provided by the library
   */
  public readonly langfuse: LangfuseDeployment;

  constructor(scope: Construct, id: string, props: ILangfuseDeploymentProps) {
    super(scope, id);
    this.langfuse = new LangfuseDeployment(this, "Langfuse", props);
  }
}

export class LangfuseDemoStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const tags = [new cdk.Tag("project", "langfuse-demo")];

    // The library provides a convenience construct for setting up a compatible VPC infrastructure,
    // or you could bring your own VPC instead:
    const vpcInfra = new LangfuseVpcInfra(this, "VpcInfra", { tags });

    // The self-hosted Langfuse deployment itself, which we've put under a nested Stack here but
    // could be included directly if you prefer:
    const langfuseStack = new LangfuseStack(this, "LangfuseStack", {
      tags,
      vpc: vpcInfra.vpc,
    });

    new cdk.CfnOutput(this, "LangfuseUrl", {
      value: langfuseStack.langfuse.url,
    });

    // Example Lambda function(s) for invoking Bedrock and logging traces to Langfuse:
    new DemoInvokers(this, "DemoInvokers", {
      langfuseUrl: langfuseStack.langfuse.url,
      tags,
    });
  }
}
