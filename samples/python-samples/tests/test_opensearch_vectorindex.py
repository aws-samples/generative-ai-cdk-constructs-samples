import aws_cdk as core
import aws_cdk.assertions as assertions
from aws_cdk.assertions import Match


from python_samples.opensearch_vectorindex import OpensearchVectorIndex

app = core.App()
stack = OpensearchVectorIndex(app, "OpensearchVectorIndex")

# Test opensearch collection  created
def test_opensearch_collection_created():
    template = assertions.Template.from_stack(stack)
    template.resource_count_is("AWS::OpenSearchServerless::Collection", 1)


