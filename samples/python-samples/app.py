#!/usr/bin/env python3
import os

import aws_cdk as cdk

from python_samples.bedrock_opensearch_stack import BedrockOpensearchStack
from python_samples.bedrock_aurora_stack import BedrockAuroraStack
from python_samples.bedrock_pinecone_stack import BedrockPineconeStack
from python_samples.opensearch_vectorindex import OpensearchVectorIndex
from python_samples.prompt_management import PromptManagementStack
from python_samples.bedrock_data_automation_stack import BedrockDataAutomationStack
from python_samples.bedrock_data_automation_stack_eb import BedrockDataAutomationStack as BedrockDataAutomationStackEB  
app = cdk.App()
env = cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
                        region=os.getenv('CDK_DEFAULT_REGION'))



BedrockDataAutomationStack(app, "bdaAPI"+os.getenv('SUFFIX',''),
     env=env
     )

BedrockDataAutomationStackEB(app, "bdaEB"+os.getenv('SUFFIX',''),
     env=env
     )

#---------------------------------------------------------------------------
# Bedrock knowledge base with OpenSearch
#---------------------------------------------------------------------------

# BedrockOpensearchStack(app, "BedrockOpensearchStack"+os.getenv('SUFFIX',''),
#     env=env
#     )

#---------------------------------------------------------------------------
# Bedrock knowledge base with Amazon RDS Aurora PostgreSQL
# uncomment this if you want to deploy Amazon RDS Aurora PostgreSQL 
#---------------------------------------------------------------------------
    

# BedrockAuroraStack(app, "BedrockAuroraStack",
#     env=env
#     )


#---------------------------------------------------------------------------
# Bedrock knowledge base with Pinecone
# uncomment this if you want to deploy Pinecone
#---------------------------------------------------------------------------
    

# BedrockPineconeStack(app, "BedrockPineconeStack",
#     env=env
#     )


#---------------------------------------------------------------------------
# Prompt Management stack
#---------------------------------------------------------------------------
# PromptManagementStack(app, "PromptManagementStack"+os.getenv('SUFFIX', ''),
#     env=env
#    )

app.synth()


