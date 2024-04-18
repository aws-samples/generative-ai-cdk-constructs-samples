from aws_cdk import (
    # Duration,
    Stack,
    aws_s3 as s3,

    # aws_sqs as sqs,
)
from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import (
    bedrock,
    amazonaurora
)

class BedrockAuroraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

    #---------------------------------------------------------------------------
    # Bedrock knowledge base with Amazon RDS Aurora PostgreSQL
    #---------------------------------------------------------------------------
    

        aurora = amazonaurora.AmazonAuroraVectorStore(
            credentials_secret_arn='arn:aws:secretsmanager:your-region:123456789876:secret:your-key-name',
            database_name='bedrock_vector_db',
            metadata_field='metadata',
            primary_key_field='id',
            resource_arn='arn:aws:rds:your-region:123456789876:cluster:aurora-cluster-manual',
            table_name='bedrock_integration.bedrock_kb',
            text_field='chunks',
            vector_field='embedding',
)

        kb = bedrock.KnowledgeBase(self, 'KnowledgeBase-Aurora', 
                    vector_store= aurora,
                    embeddings_model= bedrock.BedrockFoundationModel.COHERE_EMBED_ENGLISH_V3,
                    instruction=  'Use this knowledge base to answer questions about books. ' +
            'It contains the full text of novels.'                     
                )

        docBucket = s3.Bucket(self, 'DockBucket-Aurora')

        bedrock.S3DataSource(self, 'DataSource-Aurora',
            bucket= docBucket,
            knowledge_base=kb,
            data_source_name='books',
            chunking_strategy= bedrock.ChunkingStrategy.FIXED_SIZE,
            max_tokens=500,
            overlap_percentage=20   
        )

   