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
import { ContentPolicyConfig,FiltersConfigType,FiltersConfigStrength } from '@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock/content-policy';
import { PersonalIdentifiableInformation, PiiEntitiesConfigAction, Topic } from '@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock';

export class BedrockGuardrailStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props: cdk.StackProps) {
      super(scope, id, props);

    const guardrails = new bedrock.Guardrail(this,'bedrockGuardrails',{
        blockedInputMessaging:"Sorry, your query voilates our usage policy.",
        blockedOutputsMessaging:"Sorry, I am unable to answer your question because of our usage policy.",
        filtersConfig: [{
            filtersConfigType: FiltersConfigType.HATE,
            inputStrength: FiltersConfigStrength.HIGH,
            outputStrength: FiltersConfigStrength.HIGH
        }],
    });

    guardrails.addSensitiveInformationPolicyConfig([{
      type: PersonalIdentifiableInformation.EMAIL,
      action:   PiiEntitiesConfigAction.BLOCK
    },
    {
        type: PersonalIdentifiableInformation.USERNAME,
        action:   PiiEntitiesConfigAction.BLOCK  
    }],{
        name: "CUSTOMER_ID", 
        description: "customer id",
        pattern: "/^[A-Z]{2}\d{6}$/",
        action: "BLOCK", 
    });
    //   const customerIdRegex = /^[A-Z]{2}\d{6}$/;
    // console.log(customerIdRegex.test('AB123456')); // true
    // console.log(customerIdRegex.test('a123456')); // false

    const topic = new Topic(this,'topic');
    topic.createFinancialAdviceTopic()
    topic.createPoliticalAdviceTopic()
    
    guardrails.addTopicPolicyConfig(topic)

    guardrails.addWordPolicyConfig([{
        text:"Let it be"
    }])
    
}



}
