import os
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    CfnOutput,
    Duration as Duration
)
from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import (
    bedrock,
    
)
from aws_cdk.aws_lambda_python_alpha import ( BundlingOptions,PythonFunction,PythonLayerVersion)

class BedrockOpensearchStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

    #---------------------------------------------------------------------------
    # Bedrock knowledge base with Opensearch serverless
    #---------------------------------------------------------------------------
        kb = bedrock.KnowledgeBase(self, 'KnowledgeBase-OS', 
            embeddings_model= bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V1,
            instruction=  'Use this knowledge base to answer questions about books. ' +
            'It contains the full text of novels.' ,
            description= 'This knowledge base contains the full text of novels.',                    
        )

        docBucket = s3.Bucket(self, 'DockBucket-OS')

        dataSource = bedrock.S3DataSource(self, 'DataSource-OS',
            bucket= docBucket,
            knowledge_base=kb,
            data_source_name='books',
            chunking_strategy= bedrock.ChunkingStrategy.fixed_size(
                max_tokens=500,
                overlap_percentage=20 
            )
              
        )
   
    ## action group
        action_group_function = PythonFunction(
            self,
            "LambdaFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            entry= os.path.join(os.path.dirname(__file__), '../lambda/action-group/'),
            layers= [_lambda.LayerVersion.from_layer_version_arn(self, 'PowerToolsLayer', f'arn:aws:lambda:{self.region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:60')],
            timeout= Duration.minutes(2),
            bundling = BundlingOptions(build_args={"POETRY_VERSION": "1.7.0"})
        )      
         
        ag = bedrock.AgentActionGroup(
                name='query-library',
                description= 'Use these functions to get information about the books in the library.',
                executor=bedrock.ActionGroupExecutor.fromlambda_function(
                  action_group_function,
                ),
                enabled= True,
                api_schema= bedrock.ApiSchema.from_local_asset("./python_samples/action-group.yaml")
                ) 

        ## agent 
        agent = bedrock.Agent(
            self,
            "Agent",
            foundation_model=bedrock.BedrockFoundationModel.AMAZON_NOVA_MICRO_V1,
            instruction="You are a helpful and friendly agent that answers questions about insurance claims.",
            knowledge_bases=[kb],
            user_input_enabled= True,
            should_prepare_agent=True
            )
       
     ## associate action group  with agent
        agent.add_action_group(ag)   
        
     ## agent alias
        agent_alias= bedrock.AgentAlias(self, 
                                        'AgentAlias',
                                        description='alias for my agent',
                                        agent=agent)
       

        CfnOutput(self, "KnowledgeBaseId", value=kb.knowledge_base_id)
        CfnOutput(self, 'agentid', value= agent.agent_id)
        CfnOutput(self, 'DataSourceId', value= dataSource.data_source_id)
        CfnOutput(self, 'DocumentBucket', value= docBucket.bucket_name)
        CfnOutput(self, 'agent_alias', value= agent_alias.alias_name)
