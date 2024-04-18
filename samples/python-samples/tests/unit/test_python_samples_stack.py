import aws_cdk as core
import aws_cdk.assertions as assertions

from python_samples.python_samples_stack import PythonSamplesStack

# example tests. To run these tests, uncomment this file along with the example
# resource in python_samples/python_samples_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = PythonSamplesStack(app, "python-samples")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
