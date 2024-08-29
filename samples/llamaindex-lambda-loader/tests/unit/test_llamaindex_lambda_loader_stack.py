import aws_cdk as core
import aws_cdk.assertions as assertions

from llamaindex_lambda_loader.llamaindex_lambda_loader_stack import LlamaindexLambdaLoaderStack

# example tests. To run these tests, uncomment this file along with the example
# resource in llamaindex_lambda_loader/llamaindex_lambda_loader_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = LlamaindexLambdaLoaderStack(app, "llamaindex-lambda-loader")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
