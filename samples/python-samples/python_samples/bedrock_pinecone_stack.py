from aws_cdk import (
    # Duration,
    Stack,
    aws_s3 as s3,

    # aws_sqs as sqs,
)
from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import (
    bedrock,
    pinecone
)

class BedrockPineconeStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

    #---------------------------------------------------------------------------
    # Bedrock knowledge base with Pinecone
    #---------------------------------------------------------------------------
    

        pineconevs = pinecone.PineconeVectorStore(
            connection_string='https://your-index-1234567.svc.gcp-starter.pinecone.io',
            credentials_secret_arn='arn:aws:secretsmanager:your-region:123456789876:secret:your-key-name',
        )

        kb = bedrock.KnowledgeBase(self, 'KnowledgeBase-pinecone', 
                    vector_store= pineconevs,
                    embeddings_model= bedrock.BedrockFoundationModel.COHERE_EMBED_ENGLISH_V3,
                    instruction=  'Use this knowledge base to answer questions about books. ' +
            'It contains the full text of novels.'                     
                )

        docBucket = s3.Bucket(self, 'DockBucket-pinecone')

        bedrock.S3DataSource(self, 'DataSource-pinecone',
            bucket= docBucket,
            knowledge_base=kb,
            data_source_name='books',
            chunking_strategy= bedrock.ChunkingStrategy.FIXED_SIZE,
            max_tokens=500,
            overlap_percentage=20   
        )