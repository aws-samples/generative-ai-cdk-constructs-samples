from aws_cdk import (
    # Duration,
    Stack,
    aws_s3 as s3,
    aws_iam as iam,
    ArnFormat as ArnFormat
    

    # aws_sqs as sqs,
)
from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import (
    opensearchserverless,
    opensearch_vectorindex,
)

from aws_cdk import aws_opensearchserverless as aws_opensearchserverless


class OpensearchVectorIndex(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

       

        # Create IAM Role
        role = iam.Role(
            self, 'Role',
            role_name='mycustomrole',
            assumed_by=iam.ServicePrincipal('bedrock.amazonaws.com', 
                conditions={
                    'StringEquals': {'aws:SourceAccount': Stack.of(self).account},
                    'ArnLike': {
                        'aws:SourceArn': Stack.of(self).format_arn(
                            service='bedrock',
                            resource='knowledge-base',
                            resource_name='*',
                            arn_format=ArnFormat.SLASH_RESOURCE_NAME
                        )
                    }
                }
            )
        )
        
        vector_store = opensearchserverless.VectorCollection(self, "VectorCollection",
            collection_name='pythonsamples'
        )
         
         # Grant data access to the role
        vector_store.grant_data_access(role)

        vector_index = opensearch_vectorindex.VectorIndex(self, "VectorIndex",
            vector_dimensions= 1536,
            collection=vector_store,
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
        
        vector_index.node.add_dependency(vector_store)


