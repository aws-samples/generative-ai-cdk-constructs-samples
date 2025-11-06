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

from agents import AgentArchitecture
from agents.single_agent import SingleAgentArchitecture
from agents.graph_agent import GraphAgentArchitecture
from schema import AgentArchitecture as AgentArchitectureType


class AgentFactory:
    """Factory for creating different agent architectures"""

    @staticmethod
    def create_agent_architecture(architecture_type: AgentArchitectureType) -> AgentArchitecture:
        """Create agent architecture based on type"""
        if architecture_type == "Single":
            return SingleAgentArchitecture()
        elif architecture_type == "Graph":
            return GraphAgentArchitecture()
        else:
            raise ValueError(f"Unknown agent architecture: {architecture_type}")
