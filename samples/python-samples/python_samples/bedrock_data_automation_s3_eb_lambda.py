import json
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_s3 as s3,
    RemovalPolicy,
    aws_events as events,
    aws_events_targets as targets,
   
    

)
from constructs import Construct

from aws_solutions_constructs.aws_eventbridge_lambda import EventbridgeToLambda 
from cdklabs.generative_ai_cdk_constructs import BedrockDataAutomation
from cdklabs.generative_ai_cdk_constructs import BedrockDataAutomation

class BedrockDataAutomationStackEB(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create BedrockDataAutomation construct
        bedrock_data_automation = BedrockDataAutomation(self, 'cb',
            is_custom_bda_blueprint_required=False,
            is_bda_project_required=False,
            is_bda_invocation_required=True,
            is_status_required=False
        )

        
        # Get the input bucket and Lambda function
        bda_input_bucket = bedrock_data_automation.input_bucket
         # Enable EventBridge notification for the bucket
        bda_input_bucket.enable_event_bridge_notification()
        
       
         # Create CloudFormation outputs
        CfnOutput(self, 'inputbucketname',
            value=bedrock_data_automation.input_bucket.bucket_name
        )
        
    
        
        blueprint_arn =  "arn:aws:bedrock:us-west-2:551246883740:blueprint/a55789f6bd81"
        
        # Create EventBridge to Lambda with input transformation
        invoke_bda_event = EventbridgeToLambda(self, 'invokeBda',
            existing_lambda_obj=bedrock_data_automation.bda_invocation_lambda_function,
            event_rule_props={
                "event_pattern": {
                    "source": ["aws.s3"],
                    "detail_type": ["Object Created"],
                    "detail": {
                        "bucket": {
                            "name": [bedrock_data_automation.input_bucket.bucket_name]
                        },
                        "object": {
                            "key": [{
                                "suffix": ".pdf"
                            }]
                        }
                    }
                }
            }
        )

        # Get the rule from the construct
        rule = invoke_bda_event.events_rule

        # Add target with input transformation
        rule.add_target(targets.LambdaFunction(
            bedrock_data_automation.bda_invocation_lambda_function,
            event=events.RuleTargetInput.from_object({
                "source": "custom.bedrock.blueprint",
                "detail_type": "Bedrock Invoke Request",
                "detail": json.dumps({
                    "input_filename": events.EventField.from_path('$.detail.object.key'),
                    "output_filename": events.EventField.from_path('$.detail.object.key').replace('.pdf', '_2.csv'),
                    "blueprints": [{
                        "blueprint_arn": blueprint_arn,
                        "stage": "LIVE"
                    }]
                })
            })
        ))
    
        CfnOutput(self, 'outputbucketname', 
            value=bedrock_data_automation.output_bucket.bucket_name
        )




