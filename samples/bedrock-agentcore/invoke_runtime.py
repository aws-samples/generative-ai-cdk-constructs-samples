#!/usr/bin/env python3
"""
Invoke AgentCore Runtime deployed via CDK

This script invokes the Runtime created by CDK L2 constructs,
not the agentcore CLI deployment.

Usage:
    python invoke_runtime.py "your prompt"                    # Uses date-based session
    python invoke_runtime.py "your prompt" my-custom-session  # Uses custom session
"""

import boto3
import json
import sys
import os
from datetime import datetime

def get_runtime_arn_from_cfn():
    """Get Runtime ARN from CloudFormation stack outputs"""
    try:
        cfn = boto3.client('cloudformation', region_name='us-east-1')
        response = cfn.describe_stacks(StackName='AgentCoreDemoStack')
        outputs = response['Stacks'][0]['Outputs']
        
        for output in outputs:
            if output['OutputKey'] == 'RuntimeArn':
                return output['OutputValue']
        return None
    except Exception as e:
        print(f"Error fetching Runtime ARN: {e}", file=sys.stderr)
        return None


def invoke_runtime(runtime_arn, prompt, session_id=None):
    """Invoke the AgentCore Runtime"""
    try:
        client = boto3.client('bedrock-agentcore', region_name='us-east-1')
        
        # Prepare request payload
        request_body = {'prompt': prompt}
        
        params = {
            'agentRuntimeArn': runtime_arn,
            'payload': json.dumps(request_body)
        }
        
        if session_id:
            params['runtimeSessionId'] = session_id
        
        # Invoke
        response = client.invoke_agent_runtime(**params)
        
        # Parse streaming response
        if 'response' in response:
            # Response is a StreamingBody object that needs to be read
            streaming_body = response['response']
            body_bytes = streaming_body.read()
            body_str = body_bytes.decode('utf-8')
            
            try:
                # Parse JSON response
                body_json = json.loads(body_str)
                
                # Extract the agent's actual response text
                if isinstance(body_json, dict):
                    return body_json.get('response') or body_json.get('output') or body_json.get('text') or str(body_json)
                return body_str
            except json.JSONDecodeError:
                # If not JSON, return as-is
                return body_str
        
        # Fallback if no 'response' key
        return str(response)
        
    except Exception as e:
        print(f"Error invoking runtime: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python invoke_runtime.py <prompt> [session_id]")
        print()
        print("Examples:")
        print("  # Use date-based session (new session each day)")
        print("  python invoke_runtime.py \"My name is Alice\"")
        print()
        print("  # Use custom session for specific conversation")
        print("  python invoke_runtime.py \"My name is Bob\" work-project")
        print()
        print("  # Continue yesterday's conversation (if you remember the date)")
        print("  python invoke_runtime.py \"What did we discuss?\" session-2026-01-28")
        sys.exit(1)
    
    prompt = sys.argv[1]
    
    # Use date-based session ID if not provided - ensures daily conversation reset
    # This prevents memory from growing indefinitely while maintaining same-day context
    if len(sys.argv) > 2:
        session_id = sys.argv[2]
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        session_id = f"session-{today}"
    
    print(f"→ Using session ID: {session_id}")
    print(f"→ Prompt: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")
    print()
    
    # Get Runtime ARN
    runtime_arn = get_runtime_arn_from_cfn()
    if not runtime_arn:
        print("ERROR: Could not retrieve Runtime ARN from CloudFormation", file=sys.stderr)
        print("Make sure AgentCoreDemoStack is deployed", file=sys.stderr)
        sys.exit(1)
    
    # Invoke
    response = invoke_runtime(runtime_arn, prompt, session_id)
    if response:
        print(response)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()