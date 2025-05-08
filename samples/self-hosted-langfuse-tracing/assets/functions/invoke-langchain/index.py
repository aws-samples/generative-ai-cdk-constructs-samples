# Python Built-Ins:
from dataclasses import dataclass
import json
import os
from urllib3.util import Retry

# External Dependencies:
from langchain.schema import StrOutputParser
from langchain_aws import ChatBedrock as BedrockChat
from langfuse.callback import CallbackHandler
from requests import Session
from requests.adapters import HTTPAdapter

try:
    LANGFUSE_HOST = os.environ["LANGFUSE_HOST"]
    LANGFUSE_SECRET_ID = os.environ["LANGFUSE_SECRET_ID"]
except KeyError as ke:
    raise RuntimeError(f"Missing required environment variable: {ke}") from ke

BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
)
BEDROCK_GUARDRAIL_ID = os.environ.get("BEDROCK_GUARDRAIL_ID")
BEDROCK_GUARDRAIL_VERSION = os.environ.get("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
SECRETS_EXT_PORT = os.environ.get("PARAMETERS_SECRETS_EXTENSION_HTTP_PORT", "2773")

llm = BedrockChat(model_id=BEDROCK_MODEL_ID)


@dataclass
class EventData:
    input_text: str

    @classmethod
    def parse(cls, raw: dict) -> "EventData":
        try:
            input_text = raw["inputText"]
        except KeyError as ke:
            raise ValueError(f"Input event missing required field {ke}") from ke
        return cls(input_text=input_text)


def get_langfuse_keys() -> dict:
    """Fetch Langfuse {public_key, secret_key} from Lambda Secrets Manager extension
    
    See: https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets_lambda.html

    This needs to be at invoke time, because trying to call it at init will yield an error response
    'not ready to serve traffic, please wait'.
    """
    print("Fetching Langfuse secret from Secrets Manager")
    retries = Retry(
        total=4,
        backoff_factor=0.1,
        status_forcelist=[400, 502, 503, 504],
        allowed_methods={"GET"},
    )
    with Session() as reqsess:
        reqsess.mount("http://", HTTPAdapter(max_retries=retries))
        lf_secret_resp = reqsess.get(
            f"http://localhost:{SECRETS_EXT_PORT}/secretsmanager/get?secretId={LANGFUSE_SECRET_ID}",
            headers={"X-Aws-Parameters-Secrets-Token": os.environ["AWS_SESSION_TOKEN"]},
        )
        if lf_secret_resp.status_code >= 300:
            raise RuntimeError(
                "Failed to retrieve Langfuse secret from Secrets Manager: HTTP %s %s"
                % (lf_secret_resp.status_code, lf_secret_resp.text)
            )
        lf_secret_raw = lf_secret_resp.json()
        try:
            lf_secret = json.loads(lf_secret_raw["SecretString"])
            lf_public_key = lf_secret["public_key"]
            lf_secret_key = lf_secret["secret_key"]
        except Exception as err:
            raise RuntimeError(
                "Langfuse secret from Secrets Manager did not have expected structure "
                "{public_key, secret_key} in 'SecretString'"
            ) from err
        if not lf_public_key.startswith("pk-lf-"):
            raise RuntimeError(
                "Retrieved Langfuse public key '%s' does not start with 'pk-lf-'"
                % lf_public_key
            )
        if not lf_secret_key.startswith("sk-lf-"):
            raise RuntimeError(
                "Retrieved Langfuse secret key '%s' does not start with 'sk-lf-'"
                % lf_secret_key
            )
        return {"public_key": lf_public_key, "secret_key": lf_secret_key}


def handler(event: dict, context):
    evt = EventData.parse(event)

    chain = llm | StrOutputParser()
    langfuse_handler = CallbackHandler(
        host=LANGFUSE_HOST,
        **get_langfuse_keys(),
    )
    reply = chain.invoke(evt.input_text, config={"callbacks": [langfuse_handler]})

    return {
        "statusCode": 200,
        "body": reply,
        "headers": {
            "Content-Type": "text/plain",
        },
    }
