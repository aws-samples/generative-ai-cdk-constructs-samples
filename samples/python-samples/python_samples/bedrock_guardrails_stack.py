from aws_cdk import (
    # Duration,
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    CfnOutput,
    Duration as Duration
    # aws_sqs as sqs,
)
from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import (
    bedrock
)

class BedrockGuardrailsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        guardrail = bedrock.Guardrail(self, 'myGuardrails',
            name='my-BedrockGuardrails',
            description= "Legal ethical guardrails."
        )
        
        # Optional - Add Sensitive information filters
        guardrail.add_pii_filter(
            type= bedrock.pii_type.General.ADDRESS,
            action= bedrock.GuardrailAction.ANONYMIZE,
        )

        guardrail.add_regex_filter(
            name= "TestRegexFilter",
            description= "This is a test regex filter",
            pattern= "/^[A-Z]{2}d{6}$/",
            action= bedrock.GuardrailAction.ANONYMIZE,
        )

        # Optional - Add contextual grounding
        guardrail.add_contextual_grounding_filter(
            type= bedrock.ContextualGroundingFilterType.GROUNDING,
            threshold= 0.95,
        )

        guardrail.add_contextual_grounding_filter(
            type= bedrock.ContextualGroundingFilterType.RELEVANCE,
            threshold= 0.95,
        )

        # Optional - Add Denied topics . You can use default Topic or create your custom Topic with createTopic function. The default Topics can also be overwritten.
        guardrail.add_denied_topic_filter(bedrock.Topic.FINANCIAL_ADVICE)

        guardrail.add_denied_topic_filter(
        bedrock.Topic.custom(
            name= "Legal_Advice",
            definition=
                "Offering guidance or suggestions on legal matters, legal actions, interpretation of laws, or legal rights and responsibilities.",
            examples= [
                "Can I sue someone for this?",
                "What are my legal rights in this situation?",
                "Is this action against the law?",
                "What should I do to file a legal complaint?",
                "Can you explain this law to me?",
            ]
        )
        )

        # Optional - Add Word filters. You can upload words from a file with addWordFilterFromFile function.
        guardrail.add_word_filter("drugs")
        guardrail.add_managed_word_list_filter(bedrock.ManagedWordFilterType.PROFANITY)
        #guardrail.add_word_filter_from_file("./scripts/wordsPolicy.csv")

        # versioning - if you change any guardrail configuration, a new version will be created
        guardrail.create_version("testversion")

        guardrail.add_denied_topic_filter(bedrock.Topic.FINANCIAL_ADVICE);

        # Create a custom topic
        guardrail.add_denied_topic_filter(
            bedrock.Topic.custom(
                name='Legal_Advice',
                definition='Offering guidance or suggestions on legal matters, legal actions, interpretation of laws, or legal rights and responsibilities.',
                examples=[
                'Can I sue someone for this?',
                'What are my legal rights in this situation?',
                'Is this action against the law?',
                'What should I do to file a legal complaint?',
                'Can you explain this law to me?',
            ],
        )
        );