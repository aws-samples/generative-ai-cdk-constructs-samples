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
# Standard library imports
import sys
import logging
# Third party imports 
import requests

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

class GraphQLMutationClient:
    """Client for making GraphQL mutation requests."""
    
    def __init__(self, endpoint, id_token):
        """Initialize the GraphQL client.
        
        Args:
            endpoint (str): The URL of the GraphQL endpoint.
            id_token (str): The auth token to use in the Authorization header.
        """
        self.graphql_endpoint = endpoint
        self.headers = {
            "Content-type": "application/json",
            "Accept": "application/json", 
            "Authorization": id_token
        }

    def execute(self, query, operation_name, variables=None):
        """Execute a GraphQL query/mutation.
        
        Args:
            query (str): The GraphQL query/mutation string.
            operation_name (str): The operation name.
            variables (dict, optional): Variables for the GraphQL query.
            
        Returns:
            str: The JSON response body.
        """
        
        data = {
            "query": query,
            "operationName": operation_name, 
            "variables": variables if variables else {}
        }
        
        try:
            response = requests.post(self.graphql_endpoint, json=data, headers=self.headers)
            response.raise_for_status()
            
        except requests.exceptions.RequestException as error:
            logging.error("Error making GraphQL request: %s", error)
            raise
        
        return response.text