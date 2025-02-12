from aws_cdk import (
    Stack,
    CfnOutput,
    aws_apigateway as apigw
)
from constructs import Construct
from aws_solutions_constructs.aws_apigateway_lambda import ApiGatewayToLambda
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

        # Create API Gateway integrations for each Lambda function
        blueprint_api = ApiGatewayToLambda(self, 'CreateBlueprintApi',
            existing_lambda_obj=bda.blueprint_lambda_function,
            api_gateway_props=apigw.RestApiProps(
                rest_api_name='createBluePrintPython'
            )    
        )

        invoke_api = ApiGatewayToLambda(self, 'InvokeApi',
            existing_lambda_obj=bda.bda_invocation_lambda_function,
             api_gateway_props=apigw.RestApiProps(
                rest_api_name='createBluePrintPython'
            ) 
        )

        project_api = ApiGatewayToLambda(self, 'bdaProjectApi',
            existing_lambda_obj=bda.bda_project_lambda_function,
             api_gateway_props=apigw.RestApiProps(
                rest_api_name='createBDAprojectPython'
            ) 
        )

        result_status_api = ApiGatewayToLambda(self, 'bdaResultApi',
            existing_lambda_obj=bda.bda_result_statu_lambda_function,
             api_gateway_props=apigw.RestApiProps(
                rest_api_name='bdaResultStatusPython'
            ) 
        )
