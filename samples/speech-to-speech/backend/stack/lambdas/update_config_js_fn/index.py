import json
from typing import Dict, Any
import boto3

def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:

    # Extract values from event ResourceProperties
    region_name = event["ResourceProperties"]["REGION_NAME"]
    cognito_user_pool_id = event["ResourceProperties"]["COGNITO_USER_POOL_ID"]
    cognito_user_pool_client_id = event["ResourceProperties"]["COGNITO_USER_POOL_CLIENT_ID"]
    cognito_identity_pool_id = event["ResourceProperties"]["COGNITO_IDENTITY_POOL_ID"]
    load_balancer_dns = event["ResourceProperties"]["LOAD_BALANCER_DNS"]
    s3_bucket_name = event["ResourceProperties"]["S3_BUCKET_NAME"]

    body = f"""window.APP_CONFIG = {{
        "VITE_REGION_NAME": "{region_name}",
        "VITE_COGNITO_USER_POOL_ID": "{cognito_user_pool_id}",
        "VITE_COGNITO_USER_POOL_CLIENT_ID": "{cognito_user_pool_client_id}",
        "VITE_COGNITO_IDENTITY_POOL_ID": "{cognito_identity_pool_id}",
        "VITE_LOAD_BALANCER_DNS": "{load_balancer_dns}",
        "VITE_APP_NAME": "Bedrock Nova Sonic Solution",
        "VITE_DEPLOYMENT_TYPE": "remote"
    }};"""

    try:
        s3 = boto3.client('s3')
        s3.put_object(
            Bucket=s3_bucket_name,
            Key='config.js',
            Body=body,
            ContentType='application/javascript'
        )

        return {
            'statusCode': 200,
            'body': json.dumps('Config.js updated successfully')
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': json.dumps('Error updating Config.js')
        }