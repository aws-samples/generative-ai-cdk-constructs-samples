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