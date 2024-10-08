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


