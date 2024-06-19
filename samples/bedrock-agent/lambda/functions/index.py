
import json

def handler(event, context):
    print(f"Received event: {event} ")
    agent = event['agent']
    actionGroup = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])

    # Execute your business logic here. For more information, refer to: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html
    
    resultSet = [
            {
                "name": "chicken",
                "nutrient" :"fat",
                "percentage": 20
            },
             {
                "name": "shrimp",
                "nutrient" :"fat",
                "percentage": 30
            },
             {
                "name": "beef",
                "nutrient" :"fat",
                "percentage": 50
            }
        ]
    
    responseBody =  {
        "TEXT": {
            "body": " chicken has 20 gm of fat per serving. Shrimp has 30 gm of fat per serving. Beef has 50 gm of fat per serving ".format(function)
        }
    }

    action_response = {
        'actionGroup': actionGroup,
        'function': function,
        'functionResponse': {
            'responseBody': responseBody
        }

    }

    dummy_function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
    print("Response: {}".format(dummy_function_response))

    return dummy_function_response
