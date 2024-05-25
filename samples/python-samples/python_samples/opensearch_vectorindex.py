from aws_cdk import (
    # Duration,
    Stack,
    aws_s3 as s3,

    # aws_sqs as sqs,
)
from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import (
    opensearchserverless,
    opensearch_vectorindex,
)

class OpensearchVectorIndex(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vectorCollection = opensearchserverless.VectorCollection(self, "VectorCollection",
            collection_name='pythonsamples'
        )

        vectorIndex = opensearch_vectorindex.VectorIndex(self, "VectorIndex",
            vector_dimensions= 1536,
            collection=vectorCollection,
            index_name='myindex',
            vector_field='vectorfieldname',
            mappings= [
                opensearch_vectorindex.MetadataManagementFieldProps(
                    mapping_field='AMAZON_BEDROCK_TEXT_CHUNK',
                    data_type='text',
                    filterable=True
                ),
                opensearch_vectorindex.MetadataManagementFieldProps(
                    mapping_field='AMAZON_BEDROCK_METADATA',
                    data_type='text',
                    filterable=False
                )
            ],
        )
