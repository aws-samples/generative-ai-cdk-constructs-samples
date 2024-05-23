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
import {Construct} from 'constructs';
import { bedrock } from '@cdklabs/generative-ai-cdk-constructs';
import {  General, InformationTechnology, PiiEntitiesConfigAction, Topic } from '@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock';

export class BedrockGuardrailStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props: cdk.StackProps) {
      super(scope, id, props);

    const guardrails = new bedrock.Guardrail(this,'bedrockGuardrails',{
        name: "my-BedrockGuardrails",
        description: "Legal ethical guardrails.",
    });

    guardrails.addSensitiveInformationPolicyConfig([{
      type: General.EMAIL,
      action:   PiiEntitiesConfigAction.BLOCK
    },
    {
        type: InformationTechnology.IP_ADDRESS,
        action:   PiiEntitiesConfigAction.BLOCK  
    }],{
        name: "CUSTOMER_ID", 
        description: "customer id",
        pattern: "/^[A-Z]{2}\d{6}$/",
        action: "BLOCK", 
    });
    // const customerIdRegex = /^[A-Z]{2}\d{6}$/;
    // console.log(customerIdRegex.test('AB123456')); // true
    // console.log(customerIdRegex.test('a123456')); // false

    const topic = new Topic(this,'topic');
    topic.financialAdviceTopic()
    topic.politicalAdviceTopic()
    
    guardrails.addTopicPolicyConfig(topic)

    guardrails.uploadWordPolicyFromFile('./scripts/wordsPolicy.csv')
    
}



}
