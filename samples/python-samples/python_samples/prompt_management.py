from aws_cdk import (
    Stack,
    aws_kms as kms,
)
from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import (
    bedrock
)
from aws_cdk.aws_bedrock import CfnPrompt

class PromptManagementStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create KMS key
        cmk = kms.Key(self, "cmk")

        claude_model = bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V1_0,
        # Create tool specification
        tool_spec = CfnPrompt.ToolSpecificationProperty(
            name="top_song",
            description="Get the most popular song played on a radio station.",
            input_schema=CfnPrompt.ToolInputSchemaProperty(
                json={
                    "type": "object",
                    "properties": {
                        "sign": {
                            "type": "string",
                            "description": "The call sign for the radio station for which you want the most popular song. Example calls signs are WZPZ and WKR."
                        }
                    },
                    "required": ["sign"]
                }
            )
        )

        # Create tool configuration
        tool_config = bedrock.ToolConfiguration(
            tool_choice=bedrock.ToolChoice.AUTO,
            tools=[
                CfnPrompt.ToolProperty(
                    tool_spec=tool_spec
                )
            ]
        )

        # Create chat variant
        variant_chat = bedrock.PromptVariant.chat(
            variant_name="variant1",
            model=bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V1_0,
            messages=[
                bedrock.ChatMessage.user("From now on, you speak Japanese!"),
                bedrock.ChatMessage.assistant("Konnichiwa!"),
                bedrock.ChatMessage.user("From now on, you speak {{language}}!"),
            ],
            system="You are a helpful assistant that only speaks the language you're told.",
            prompt_variables=["language"],
            tool_configuration=tool_config
        )

        # Create prompt
        prompt = bedrock.Prompt(
            self,
            "prompt1",
            prompt_name="prompt-chat",
            description="my first chat prompt",
            default_variant=variant_chat,
            variants=[variant_chat],
            kms_key=cmk
        )
        
        # Create variant2 as a text variant
        variant2 = bedrock.PromptVariant.text(
            variant_name="variant2",
            model=claude_model,
            prompt_variables=["topic"],
            prompt_text="This is my second text prompt. Please summarize our conversation on: {{topic}}.",
            inference_configuration={
                "temperature": 0.5,
                "topP": 0.999,
                "maxTokens": 2000,
            }
        )
        
        self.template_options.description='Description: (uksb-1tupboc43) (tag: python prompt management sample)'

        prompt.add_variant(variant2)

        