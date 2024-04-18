#!/usr/bin/env python3
import os

import aws_cdk as cdk

from python_samples.bedrock_opensearch_stack import BedrockOpensearchStack
from python_samples.bedrock_aurora_stack import BedrockAuroraStack
from python_samples.bedrock_pinecone_stack import BedrockPineconeStack


app = cdk.App()

#---------------------------------------------------------------------------
# Bedrock knowledge base with OpenSearch
#---------------------------------------------------------------------------

BedrockOpensearchStack(app, "BedrockOpensearchStack",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
                        region=os.getenv('CDK_DEFAULT_REGION')),
    )

#---------------------------------------------------------------------------
# Bedrock knowledge base with Amazon RDS Aurora PostgreSQL
#---------------------------------------------------------------------------
    

BedrockAuroraStack(app, "BedrockAuroraStack",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
                        region=os.getenv('CDK_DEFAULT_REGION')),
    )

#---------------------------------------------------------------------------
# Bedrock knowledge base with Pinecone
#---------------------------------------------------------------------------
    


BedrockPineconeStack(app, "BedrockPineconeStack",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
                        region=os.getenv('CDK_DEFAULT_REGION')),
    )

app.synth()
