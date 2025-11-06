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

import json
import os

from aws_cdk import (
  Duration,
  Stack,
  CfnOutput,
  Fn,
  aws_apigateway as apigw,
  aws_bedrockagentcore as bedrockagentcore,
  aws_dynamodb as ddb,
  aws_ecr_assets as ecr_assets,
  aws_events as events,
  aws_events_targets as targets,
  aws_iam as iam,
  aws_lambda as lambda_,
  aws_opensearchserverless as opensearchserverless,
  aws_s3 as s3,
  custom_resources as cr,
  RemovalPolicy,
)
from cdklabs.generative_ai_cdk_constructs import bedrock
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression

from check_legislation.sfn import CheckLegislationWorkflow
import stack_constructs

DATA_SOURCE_NAME = "legislations-data-source"
LEGISLATION_VECTOR_INDEX_NAME = "bedrock-knowledge-base-default-index"


class CheckLegislationStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api_gw: stack_constructs.ApiGatewayConstruct,
        clauses_table: ddb.ITable,
        jobs_table: ddb.ITable,
        event_bus: events.IEventBus,
        main_stack_name: str = "MainBackendStack",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Import only the jobs Lambda role to break circular dependency
        jobs_lambda_role = iam.Role.from_role_arn(
            self, "ImportedJobsLambdaRole",
            Fn.import_value(f"{main_stack_name}-JobsLambdaRoleArn")
        )

        # Create logging bucket for legislation bucket access logs
        legislation_logging_bucket = stack_constructs.ServerAccessLogsBucketConstruct(
            self,
            "LegislationLoggingBucket",
        )

        # Create dedicated bucket for legislation files (no lifecycle policy - kept indefinitely)
        self.legislation_bucket = stack_constructs.BucketConstruct(
            self,
            "LegislationBucket",
            server_access_logs_bucket=legislation_logging_bucket,
            lifecycle_rules=[],  # No expiration for legislation files
        )

        CfnOutput(
            self,
            "LegislationBucketName",
            value=self.legislation_bucket.bucket_name,
            export_name=f"{Stack.of(self).stack_name}-LegislationBucketName"
        )

        self._setup_agent(self.legislation_bucket, clauses_table)
        self._setup_legislation_api(api_gw, self.legislation_bucket)

        wf = CheckLegislationWorkflow(
            self,
            "CheckLegislationSfn",
            agent_runtime=self.agent_runtime,
            agent_role=self.agentcore_role,
            clauses_table=clauses_table,
            jobs_table=jobs_table,
            contract_bucket=self.legislation_bucket,
        )

        # Expose state machine for cross-stack permissions
        self.state_machine = wf.state_machine

        rule = events.Rule(
            self,
            "OnPreProcessedContract",
            event_bus=event_bus,
            event_pattern=events.EventPattern(
                source=["contract-analysis"],
                detail_type=["PreProcessedContract"],
                detail={
                    "AdditionalChecks": {
                        "legislationCheck": {"legislationId": [{"exists": True}]}
                    }
                },
            ),
        )

        rule.add_target(
            targets.SfnStateMachine(
                machine=wf.state_machine,
                # Use only the event "detail" (your JobId, ClauseNumbers, AdditionalChecks)
                input=events.RuleTargetInput.from_event_path("$.detail"),
            )
        )

        NagSuppressions.add_resource_suppressions(
            self.agentcore_role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=[
                        "Resource::arn:aws:ecr:<AWS::Region>:<AWS::AccountId>:repository/*",
                        "Resource::arn:aws:logs:<AWS::Region>:<AWS::AccountId>:log-group:/aws/bedrock-agentcore/runtimes/*",
                        "Resource::arn:aws:logs:<AWS::Region>:<AWS::AccountId>:log-group:*",
                        "Resource::arn:aws:logs:<AWS::Region>:<AWS::AccountId>:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*",
                        "Resource::*",
                        "Resource::arn:aws:bedrock-agentcore:<AWS::Region>:<AWS::AccountId>:workload-identity-directory/default/workload-identity/*",
                        "Resource::arn:aws:bedrock:*::foundation-model/*",
                        "Resource::arn:aws:bedrock:<AWS::Region>:<AWS::AccountId>:*",
                        "Resource::<LegislationBucketF182E425.Arn>/*",
                        "Resource::arn:aws:ssm:<AWS::Region>:<AWS::AccountId>:parameter/ContractAnalysis/*",
                    ],
                    reason="Wildcards required for AgentCore runtime operations, S3 object access, Bedrock model access, and SSM parameter access",
                ),
            ],
            apply_to_children=True,
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            "/CheckLegislationStack/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole/Resource",
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    applies_to=[
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
                    ],
                    reason="Construct creates this function which uses the role with managed policy",
                )
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            "/CheckLegislationStack/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole/DefaultPolicy/Resource",
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=["Resource::*"],
                    reason="Construct creates this function which uses the role with managed policy",
                )
            ],
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.legislation_api_fn.role,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    applies_to=[
                        "Action::s3:GetObject*",
                        "Action::s3:GetBucket*",
                        "Action::s3:List*",
                        "Action::s3:DeleteObject*",
                        "Action::s3:Abort*",
                        "Resource::<LegislationBucketF182E425.Arn>/*",
                    ],
                    reason="Grant read on s3 buckets creates some * actions for convenience.",
                )
            ],
            apply_to_children=True,
        )

    def _setup_legislation_api(self, api_gw, legislation_bucket):
        powertools_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            f"arn:aws:lambda:{Stack.of(self).region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-x86_64:21",
        )

        self.legislation_api_fn = stack_constructs.PythonFunctionConstruct(
            self,
            "LegislationApiFunction",
            entry=os.path.join(
                os.path.dirname(__file__), "lambda", "legislation_fn", "src"
            ),
            index="index.py",
            handler="handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(1),
            layers=[powertools_layer],
            environment={
                "AOSS_ENDPOINT": self.kb.vector_store.collection_endpoint,
                "LEGISLATION_KB_VECTOR_DB_INDEX": LEGISLATION_VECTOR_INDEX_NAME,
                "LEGISLATION_KB_ID": self.kb.knowledge_base_id,
                "LEGISLATION_KB_DATA_SOURCE_ID": self.data_source.data_source_id,
                "LEGISLATION_BUCKET_NAME": legislation_bucket.bucket_name,
                "POWERTOOLS_SERVICE_NAME": "legislation_api",
                "POWERTOOLS_LOG_LEVEL": "INFO",
            },
        )

        # Grant Bedrock permissions
        self.legislation_api_fn.role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:IngestKnowledgeBaseDocuments",
                    "bedrock:StartIngestionJob",
                ],
                resources=[self.kb.knowledge_base_arn],
            )
        )
        # Grant S3 permissions
        legislation_bucket.grant_read_write(self.legislation_api_fn.role)
        # Grant OpenSearch Serverless permissions
        self.legislation_api_fn.role.add_to_policy(
            iam.PolicyStatement(
                actions=["aoss:APIAccessAll"],
                resources=[self.kb.vector_store.collection_arn],
            )
        )

        # Note: We manually create the API Gateway resource here instead of using api_gw.add_lambda_method()
        # to avoid a circular dependency. Using that helper would create a dependency from CheckLegislationStack
        # to MainBackendStack (to modify the API Gateway), but MainBackendStack already depends on
        # CheckLegislationStack (to get the Lambda ARN). By importing the RestApi and creating resources
        # directly, we break this cycle.
        rest_api = apigw.RestApi.from_rest_api_attributes(
            self,
            "RestApi",
            rest_api_id=api_gw.rest_api.rest_api_id,
            root_resource_id=api_gw.rest_api.rest_api_root_resource_id,
        )
        
        resource = rest_api.root
        legislation_api = resource.add_resource(
            "legislations",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=[*apigw.Cors.DEFAULT_HEADERS, "Access-Control-Allow-Origin"],
            ),
        )

        legislation_methods = []
        for method in ["GET", "POST"]:
            legislation_methods.append(legislation_api.add_method(
                http_method=method,
                integration=apigw.LambdaIntegration(self.legislation_api_fn),
                authorizer=api_gw.cognito_authorizer,
                authorization_type=apigw.AuthorizationType.COGNITO,
                request_validator=api_gw.request_body_params_validator,
            ))

        # Trigger API Gateway deployment to include the new /legislations endpoint
        # This is necessary because we're adding resources to an imported API Gateway
        # from a different stack, which doesn't automatically trigger a new deployment
        self.trigger_deployment = cr.AwsCustomResource(
            self,
            "TriggerApiDeployment",
            install_latest_aws_sdk=False,
            on_create=cr.AwsSdkCall(
                service="APIGateway",
                action="createDeployment",
                parameters={
                    "restApiId": api_gw.rest_api.rest_api_id,
                    "stageName": "api",
                    "description": "Deployment triggered by CheckLegislationStack to include /legislations endpoint"
                },
                physical_resource_id=cr.PhysicalResourceId.of(f"legislation-api-deployment-{Stack.of(self).stack_name}")
            ),
            on_update=cr.AwsSdkCall(
                service="APIGateway",
                action="createDeployment",
                parameters={
                    "restApiId": api_gw.rest_api.rest_api_id,
                    "stageName": "api",
                    "description": "Deployment triggered by CheckLegislationStack update"
                },
                physical_resource_id=cr.PhysicalResourceId.of(f"legislation-api-deployment-{Stack.of(self).stack_name}")
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=["apigateway:POST"],
                    resources=[
                        f"arn:aws:apigateway:{Stack.of(self).region}::/restapis/{api_gw.rest_api.rest_api_id}/deployments"
                    ]
                )
            ])
        )
        
        # Ensure deployment happens after all API Gateway resources are fully configured.
        # Without these dependencies, CloudFormation might create the deployment before methods
        # are fully configured (authorizer, integration), resulting in a deployment snapshot with
        # incomplete configuration. These dependencies force CloudFormation to wait until the
        # resource, Lambda function, and methods are complete before triggering the deployment.
        self.trigger_deployment.node.add_dependency(legislation_api)
        self.trigger_deployment.node.add_dependency(self.legislation_api_fn)
        for method in legislation_methods:
            self.trigger_deployment.node.add_dependency(method)

        # Create data access policy for OpenSearch Serverless
        opensearchserverless.CfnAccessPolicy(
            self,
            "LegislationDataAccessPolicy",
            name="legislation-data-access-policy",
            type="data",
            policy=json.dumps(
                [
                    {
                        "Rules": [
                            {
                                "Resource": [
                                    f"index/{self.kb.vector_store.collection_name}/*"
                                ],
                                "Permission": ["aoss:*"],
                                "ResourceType": "index",
                            }
                        ],
                        "Principal": [
                            self.legislation_api_fn.role.role_arn,  # for the lambda function to be able to list the metadata in AOSS
                            f"arn:aws:sts::{Stack.of(self).account}:assumed-role/Admin/*",
                            self.kb.role.role_arn,
                        ],
                    }
                ]
            ),
        )

    def _setup_agent(self, legislation_bucket: s3.IBucket, clauses_table: ddb.ITable):
        region = Stack.of(self).region
        account_id = Stack.of(self).account

        self.kb = bedrock.VectorKnowledgeBase(
            self,
            "KnowledgeBase",
            embeddings_model=bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_1024,
        )

        self.data_source = self.kb.add_custom_data_source(
            data_source_name=DATA_SOURCE_NAME,
            chunking_strategy=bedrock.ChunkingStrategy.FIXED_SIZE,
        )

        legislation_bucket.grant_read(self.kb.role)

        self.agentcore_role = iam.Role(
            self,
            f"AgentCoreRole",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            inline_policies={
                "BedrockAgentCoreRuntimePolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
                            resources=[
                                f"arn:aws:ecr:{region}:{account_id}:repository/*"
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=["logs:DescribeLogStreams", "logs:CreateLogGroup"],
                            resources=[
                                f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=["logs:DescribeLogGroups"],
                            resources=[
                                f"arn:aws:logs:{region}:{account_id}:log-group:*"
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                            resources=[
                                f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=["ecr:GetAuthorizationToken"], resources=["*"]
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "xray:PutTraceSegments",
                                "xray:PutTelemetryRecords",
                                "xray:GetSamplingRules",
                                "xray:GetSamplingTargets",
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            actions=["cloudwatch:PutMetricData"],
                            resources=["*"],
                            conditions={
                                "StringEquals": {
                                    "cloudwatch:namespace": "bedrock-agentcore"
                                }
                            },
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "bedrock-agentcore:GetWorkloadAccessToken",
                                "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                                "bedrock-agentcore:GetWorkloadAccessTokenForUserId",
                            ],
                            resources=[
                                f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default",
                                f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default/workload-identity/*",
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream",
                            ],
                            resources=[
                                "arn:aws:bedrock:*::foundation-model/*",
                                f"arn:aws:bedrock:{region}:{account_id}:*",
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=["ssm:GetParameter"],
                            resources=[
                                f"arn:aws:ssm:{region}:{account_id}:parameter/ContractAnalysis/*"
                            ],
                        ),
                    ]
                )
            },
        )

        # Build and push Docker image using CDK Docker Asset
        docker_image = ecr_assets.DockerImageAsset(
          self, "AgentDockerImage",
          directory=os.path.join(os.path.dirname(__file__), "agent"),
          platform=ecr_assets.Platform.LINUX_ARM64
        )

        # Create the AgentCore Runtime
        self.agent_runtime = bedrockagentcore.CfnRuntime(
            self,
            "CheckLegislationAgentRuntime",
            agent_runtime_name="check_legislation_agent_runtime",
            agent_runtime_artifact=bedrockagentcore.CfnRuntime.AgentRuntimeArtifactProperty(
                container_configuration=bedrockagentcore.CfnRuntime.ContainerConfigurationProperty(
                    container_uri=docker_image.image_uri
                )
            ),
            network_configuration=bedrockagentcore.CfnRuntime.NetworkConfigurationProperty(
                network_mode="PUBLIC"
            ),
            role_arn=self.agentcore_role.role_arn,
            description="Check Legislation Agent",
            environment_variables={
                "KNOWLEDGE_BASE_ID": self.kb.knowledge_base_id,
                "CLAUSES_TABLE_NAME": clauses_table.table_name,
                "AWS_REGION": region,
            },
        )

        # Ensure the runtime waits for the role and its policies to be created
        self.agent_runtime.node.add_dependency(self.agentcore_role)

        self.kb.grant_retrieve(self.agentcore_role)
        self.kb.grant_query(self.agentcore_role)
        self.kb.grant_retrieve_and_generate(self.agentcore_role)

        CfnOutput(
            self,
            "CheckLegislationAgentKnowledgeBaseId",
            value=self.kb.knowledge_base_id,
            export_name="CheckLegislationAgentKnowledgeBaseId",
            description="This is the KB ID you will use it to ingest legislations using the CLI.",
        )

        CfnOutput(
            self,
            "CheckLegislationAgentDataSourceId",
            value=self.data_source.data_source_id,
            export_name="CheckLegislationAgentDataSourceId",
            description="This is the Data Source ID you will use it to ingest legislations using the CLI",
        )

        CfnOutput(
            self,
            "CheckLegislationAOSSEndpointURL",
            value=self.kb.vector_store.collection_endpoint,
            export_name="CheckLegislationAOSSEndpointURL",
            description="This is the endpoint URL for the OpenSearch vector store supporting the Knowledge Base. You will use it to ingest legislations using the CLI.",
        )
