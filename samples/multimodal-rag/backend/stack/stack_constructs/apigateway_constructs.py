#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import builtins
import typing
from aws_cdk import (
    Stack,
    aws_apigateway as apigateway,
    aws_cognito as cognito,
    aws_logs as logs,
    aws_lambda,
    aws_wafv2 as waf,
)
from aws_cdk.aws_apigateway import Integration, MethodResponse
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression


class ApiGatewayConstruct(Construct):
    """
    A CDK construct that creates an API Gateway with Cognito authentication and WAF protection.

    This construct sets up a REST API with:
    - Cognito user pool authorization
    - CloudWatch logging
    - CORS configuration
    - WAF rules and associations
    - Request validators for different validation scenarios

    Attributes:
        cognito_authorizer: The Cognito user pool authorizer
        log_group: CloudWatch log group for API access logs
        rest_api: The main REST API instance
        request_body_validator: Validator for request body
        request_params_validator: Validator for request parameters
        request_body_params_validator: Validator for both body and parameters
        web_acl: WAF web ACL for API protection
    """

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            region: str,
            user_pool: cognito.UserPool,
            **kwargs,
    ):
        """
        Initialize the ApiGatewayConstruct.

        Args:
            scope: The scope in which to define this construct
            construct_id: The scoped construct ID
            region: AWS region where the API Gateway will be deployed
            user_pool: Cognito user pool for authentication
            **kwargs: Additional keyword arguments
        """
        super().__init__(scope, construct_id, **kwargs)

        self.cognito_authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self,
            "CognitoUserPoolAuthorizer",
            cognito_user_pools=[user_pool],
        )

        self.log_group = logs.LogGroup(self, "LogGroup")

        self.rest_api = apigateway.RestApi(
            self,
            "RestApi",
            cloud_watch_role=True,
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=[*apigateway.Cors.DEFAULT_HEADERS, 'Access-Control-Allow-Origin'],
            ),
            deploy_options=apigateway.StageOptions(
                logging_level=apigateway.MethodLoggingLevel.INFO,
                access_log_destination=apigateway.LogGroupLogDestination(self.log_group),
                access_log_format=apigateway.AccessLogFormat.clf(),
                tracing_enabled=True,
                data_trace_enabled=False,
                stage_name="api",
            ),
            endpoint_export_name=f"{Stack.of(self).stack_name}{construct_id}RestApiEndpoint",
        )

        self.request_body_validator = apigateway.RequestValidator(
            self,
            "RequestBodyValidator",
            rest_api=self.rest_api,
            request_validator_name="Validate body",
            validate_request_body=True,
            validate_request_parameters=False,
        )

        # Choose a validator based on your needs

        self.request_params_validator = apigateway.RequestValidator(
            self,
            "RequestParametersValidator",
            rest_api=self.rest_api,
            request_validator_name="Validate query string parameters",
            validate_request_body=False,
            validate_request_parameters=True,
        )

        self.request_body_params_validator = apigateway.RequestValidator(
            self,
            "RequestBodyParametersValidator",
            rest_api=self.rest_api,
            request_validator_name="Validate body and query string parameters",
            validate_request_body=True,
            validate_request_parameters=True,
        )

        self.web_acl = waf.CfnWebACL(
            self,
            "WebACL",
            scope="REGIONAL",
            default_action=waf.CfnWebACL.DefaultActionProperty(
                allow=waf.CfnWebACL.AllowActionProperty(),
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                sampled_requests_enabled=True,
                metric_name=construct_id + "-WebACL",
            ),
            rules=[
                waf.CfnWebACL.RuleProperty(
                    name="AWSManagedRules",
                    priority=0,
                    statement=waf.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesCommonRuleSet",
                            excluded_rules=[],
                        )
                    ),
                    override_action=waf.CfnWebACL.OverrideActionProperty(
                        count={},
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        sampled_requests_enabled=True,
                        metric_name=construct_id + "-WebACL-AWSManagedRules",
                    ),
                )
            ],
        )

        self.web_acl_assoc = waf.CfnWebACLAssociation(
            self,
            "WebACLAssociation",
            web_acl_arn=self.web_acl.attr_arn,
            resource_arn="arn:aws:apigateway:{}::/restapis/{}/stages/{}".format(
                region,
                self.rest_api.rest_api_id,
                self.rest_api.deployment_stage.stage_name,
            ),
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.rest_api,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="AmazonAPIGatewayPushToCloudWatchLogs",
                    applies_to=[
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
                    ],
                ),
            ],
            apply_to_children=True,
        )

    def add_method(
            self,
            resource_path: str,
            http_method: str,
            request_validator: apigateway.RequestValidator,
            request_parameters: typing.Optional[typing.Mapping[str, bool]] = None,
            integration: typing.Optional[Integration] = None,
            method_responses: typing.Optional[
                typing.Sequence[typing.Union["MethodResponse", typing.Dict[builtins.str, typing.Any]]]] = None,
    ):
        """
        Add a method to the API Gateway with the specified configuration.

        This method creates the resource path if it doesn't exist and configures the method with
        Cognito authorization (except for OPTIONS methods which are left open for CORS).

        Args:
            resource_path: The resource path for the API endpoint (e.g., '/users/profile')
            http_method: The HTTP method (GET, POST, PUT, DELETE, etc.)
            request_validator: The request validator to use for this method
            request_parameters: Optional mapping of request parameters to their required status
            integration: Optional integration configuration
            method_responses: Optional list of method responses
        """
        path_parts = list(filter(bool, resource_path.split("/")))
        resource = self.rest_api.root
        for path_part in path_parts:
            child_resource = resource.get_resource(path_part)
            if not child_resource:
                child_resource = resource.add_resource(path_part)
            resource = child_resource

        resource.add_method(
            http_method=http_method,
            integration=integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            request_parameters=request_parameters,
            request_validator=request_validator,
            method_responses=method_responses,
        )

        # Add Cognito auth to all methods except OPTIONS to allow for CORS header lookups
        for method in self.rest_api.methods:
            resource = method.node.find_child("Resource")
            if method.http_method == "OPTIONS":
                resource.add_property_override("AuthorizationType", apigateway.AuthorizationType.NONE)
                NagSuppressions.add_resource_suppressions(
                    construct=resource,
                    suppressions=[
                        NagPackSuppression(
                            id="AwsSolutions-COG4",
                            reason="OPTIONS method for CORS pre-flight should not use authorization",
                        ),
                        NagPackSuppression(
                            id="AwsSolutions-APIG4",
                            reason="OPTIONS method for CORS pre-flight should not use authorization",
                        ),
                    ],
                )
            else:
                resource.add_property_override("AuthorizationType", apigateway.AuthorizationType.COGNITO)
                resource.add_property_override("AuthorizerId", self.cognito_authorizer.authorizer_id)

    def add_lambda_method(
            self,
            resource_path: str,
            http_method: str,
            lambda_function: aws_lambda.Function,
            request_validator: apigateway.RequestValidator,
            request_parameters: typing.Optional[typing.Dict[str, bool]] = None
    ):
        """
        Add a Lambda integration method to the API Gateway.
        
        Args:
            resource_path: Path of the API resource
            http_method: HTTP method (GET, POST, etc.)
            lambda_function: Lambda function to integrate
            request_validator: Request validator to use
            request_parameters: Optional dictionary of request parameters and their required status
        """
        self.add_method(
            resource_path=resource_path,
            http_method=http_method,
            request_validator=request_validator,
            request_parameters=request_parameters,
            integration=apigateway.LambdaIntegration(lambda_function),
        )

    def add_s3_method(
            self,
            resource_path: str,
            http_method: str,
            request_validator: apigateway.RequestValidator,
            execution_role: any,
            bucket_name: str,
            bucket_folder: str = None,
    ):
        """
        Add an S3 integration method to the API Gateway.

        This method creates an integration that allows direct access to S3 objects through the API Gateway.
        It sets up the necessary request/response mappings and CORS headers.

        Args:
            resource_path: The resource path for the API endpoint
            http_method: The HTTP method to use
            request_validator: The request validator to use
            execution_role: IAM role for executing the S3 integration
            bucket_name: Name of the S3 bucket to integrate with
            bucket_folder: Optional folder path within the bucket
        """
        path = f"{bucket_name}/{bucket_folder}/{{key}}" if bucket_folder else f"{bucket_name}/{{key}}"

        s3_apigw_integration = apigateway.AwsIntegration(
            service="s3",
            integration_http_method=http_method,
            path=path,
            options={
                "credentials_role": execution_role,
                "integration_responses": [
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_parameters={
                            "method.response.header.Content-Type": "integration.response.header.Content-Type",
                            "method.response.header.Access-Control-Allow-Origin": "'*'",
                        },
                    )
                ],
                "request_parameters": {
                    "integration.request.path.key": "method.request.path.key",
                },
            },
        )

        self.add_method(
            resource_path=resource_path,
            http_method=http_method,
            request_validator=request_validator,
            integration=s3_apigw_integration,
            request_parameters={
                "method.request.path.key": True,
                "method.request.header.Content-Type": True,
            },
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Content-Type": True,
                        "method.response.header.Access-Control-Allow-Origin": True,
                    },
                )
            ]
        )