import boto3
import json
import re
from retrying import retry
from botocore.config import Config
from botocore.exceptions import ClientError

CLAUDE_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

bedrock = boto3.client('bedrock')

bedrock_runtime = boto3.client('bedrock-runtime', config=Config(
    connect_timeout=120,
    read_timeout=120,
    retries={
        "max_attempts": 10,
        "mode": "adaptive",
    },
))


class BedrockRetryableError(Exception):
    pass


@retry(wait_fixed=10000, stop_max_attempt_number=None,
       retry_on_exception=lambda ex: isinstance(ex, BedrockRetryableError))
def invoke_llm(prompt, model_id, temperature=0.5, top_k=100, top_p=0.8, max_new_tokens=4096, verbose=False):
    model_id = (model_id or CLAUDE_MODEL_ID)

    if verbose:
        print(f">>> ModelId: {model_id}")
        print(f">>> Prompt:\n{prompt}")

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }],
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
            "max_tokens": max_new_tokens,
        }
    )

    try:
        response = bedrock_runtime.invoke_model(body=body, modelId=model_id)
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'ThrottlingException':
            print("Bedrock throttling. To try again")
            raise BedrockRetryableError(str(exc))
        elif exc.response['Error']['Code'] == 'ModelTimeoutException':
            print("Bedrock ModelTimeoutException. To try again")
            raise BedrockRetryableError(str(exc))
        else:
            raise
    except bedrock_runtime.exceptions.ThrottlingException as throttlingExc:
        print("Bedrock ThrottlingException. To try again")
        raise BedrockRetryableError(str(throttlingExc))
    except bedrock_runtime.exceptions.ModelTimeoutException as timeoutExc:
        print("Bedrock ModelTimeoutException. To try again")
        raise BedrockRetryableError(str(timeoutExc))

    response_body = json.loads(response.get('body').read())
    response = response_body['content'][0]['text']

    if verbose:
        print(f"+++++\nModel response: {response}\n+++++\n")

    return response


def extract_items_from_tagged_list(text, tag_name):
    regex = f"<{tag_name}>(.*?)</{tag_name}>"

    items = []
    for match in re.finditer(regex, text, re.IGNORECASE | re.DOTALL):
        items.append(match.group(1).strip())

    return items
