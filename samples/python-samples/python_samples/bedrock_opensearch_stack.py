from aws_cdk import (
    # Duration,
    Stack,
    aws_s3 as s3,

    # aws_sqs as sqs,
)
from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import (
    bedrock,
    
)

class BedrockOpensearchStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

    #---------------------------------------------------------------------------
    # Bedrock knowledge base with Opensearch serverless
    #---------------------------------------------------------------------------
        kb = bedrock.KnowledgeBase(self, 'KnowledgeBase-OS', 
            embeddings_model= bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V1,
            instruction=  'Use this knowledge base to answer questions about books. ' +
            'It contains the full text of novels.'                     
        )

        docBucket = s3.Bucket(self, 'DockBucket-OS')

        bedrock.S3DataSource(self, 'DataSource-OS',
            bucket= docBucket,
            knowledge_base=kb,
            data_source_name='books',
            chunking_strategy= bedrock.ChunkingStrategy.FIXED_SIZE,
            max_tokens=500,
            overlap_percentage=20   
        )

