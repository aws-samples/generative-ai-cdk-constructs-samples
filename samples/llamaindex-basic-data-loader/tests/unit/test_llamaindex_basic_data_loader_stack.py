import aws_cdk as core
import aws_cdk.assertions as assertions

from bin.llamaindex_basic_data_loader_stack import LlamaindexBasicDataLoaderStack

# example tests. To run these tests, uncomment this file along with the example
# resource in bin/llamaindex_basic_data_loader_stack.py
def test_basic_created():
    app = core.App()
    stack = LlamaindexBasicDataLoaderStack(app, "llamaindex-basic-data-loader")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
