from aws_cdk import (
    Stack,
    CfnOutput,
    aws_lambda as lambda_,
)
from constructs import Construct

from aws_solutions_constructs.aws_eventbridge_lambda import EventbridgeToLambda 
from cdklabs.generative_ai_cdk_constructs import BedrockDataAutomation

class BedrockDataAutomationStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create BedrockDataAutomation construct
        bda = BedrockDataAutomation(self, 'cb',
            is_custom_bda_blueprint_required=True,
            is_bda_project_required=True,
            is_bda_invocation_required=True,
            is_status_required=True
        )

        # Create CFN outputs for bucket names
        CfnOutput(self, 'inputbucketname', value=bda.input_bucket.bucket_name)
        CfnOutput(self, 'outputbucketname', value=bda.output_bucket.bucket_name)

        blueprint_api = EventbridgeToLambda(self, 'CreateBlueprintApi',
            existing_lambda_obj=bda.blueprint_lambda_function,
            event_rule_props={
                "event_pattern": {
                    "source": ["custom.bedrock.blueprint"],
                    "detail_type": ["Bedrock Blueprint Request"]
                }
            
            })
        
        invoke_bda_event = EventbridgeToLambda(self, 'invokeBda',
            existing_lambda_obj=bda.bda_invocation_lambda_function,
            event_rule_props={
                "event_pattern": {
                    "source": ["custom.bedrock.blueprint"],
                    "detail_type": ["Bedrock Invoke Request"]
                }
            
            })
        
        create_bda_project = EventbridgeToLambda(self, 'CreateProject',
            existing_lambda_obj=bda.bda_project_lambda_function,
            event_rule_props={
                "event_pattern": {
                    "source": ["custom.bedrock.blueprint"],
                    "detail_type": ["Bedrock Project Request"]
                }
            
            })
        
        result_status = EventbridgeToLambda(self, 'bdaResult',
            existing_lambda_obj=bda.bda_result_statu_lambda_function,
            event_rule_props={
                "event_pattern": {
                    "source": ["custom.bedrock.blueprint"],
                    "detail_type": ["Bedrock Result Status"]
                }
            
            })
        
        
