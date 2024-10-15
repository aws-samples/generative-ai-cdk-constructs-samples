#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

import aws_cdk as core
import aws_cdk.assertions as assertions

from bin.llamaindex_basic_data_loader_stack import LlamaindexBasicDataLoaderStack

def test_basic_created():
    app = core.App()
    stack = LlamaindexBasicDataLoaderStack(app, "llamaindex-basic-data-loader")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::SNS::Topic", 1)
    template.resource_count_is("AWS::SNS::Subscription", 1)
    template.resource_count_is("AWS::SSM::Parameter", 1)
    template.resource_count_is("AWS::ECS::Cluster", 1)
    template.resource_count_is("AWS::ECS::Service", 1)
    template.resource_count_is("AWS::ApplicationAutoScaling::ScalableTarget", 1)
    template.resource_count_is("AWS::ApplicationAutoScaling::ScalingPolicy", 3)
    template.resource_count_is("AWS::CloudWatch::Alarm", 2)
    template.resource_count_is("AWS::ECS::TaskDefinition", 1)
    template.resource_count_is("AWS::SNS::Topic", 1)
    template.resource_count_is("AWS::SQS::Queue", 2)
    template.resource_count_is("AWS::S3::Bucket", 3)

    template.has_resource_properties("AWS::SNS::Subscription", {
        "Protocol": "sqs",
    })

    template.resource_properties_count_is("AWS::SQS::Queue", {
        "RedrivePolicy": assertions.Match.object_like({
            "deadLetterTargetArn": assertions.Match.any_value(),
        })
    }, 1)

    template.resource_properties_count_is("AWS::SQS::Queue", {
        "RedrivePolicy": assertions.Match.absent(),
    }, 1)


