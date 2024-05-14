import aws_cdk as core
import aws_cdk.assertions as assertions
from aws_cdk.assertions import Match


from python_samples.bedrock_pinecone_stack import BedrockPineconeStack

app = core.App()
stack = BedrockPineconeStack(app, "BedrockPineconeStack")

# Test knowledge base created
def test_knowledgebase_created():
    template = assertions.Template.from_stack(stack)
    template.resource_count_is("AWS::Bedrock::KnowledgeBase", 1)

    template.has_resource_properties('AWS::Bedrock::KnowledgeBase', {
        'Description': 'Pinecone knowledge base.',
        'Name': Match.string_like_regexp('^KBBedrockPineasepinecone'),
        
      })


# Test datasource is created
def test_datasource_created():
   
    template = assertions.Template.from_stack(stack)
    template.resource_count_is("AWS::Bedrock::DataSource", 1)



# Test agent is created
def test_agent_created():
    template = assertions.Template.from_stack(stack)
    template.resource_count_is("AWS::Bedrock::Agent", 1)

   
     

# Test agent alias is created
def test_agent_alias_created():
    template = assertions.Template.from_stack(stack)
    template.resource_count_is("AWS::Bedrock::AgentAlias", 1)


