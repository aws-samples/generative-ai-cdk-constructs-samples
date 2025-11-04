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

from strands import Agent
from strands.agent import AgentResult
from strands.multiagent import GraphBuilder, GraphResult
from strands.types.content import ContentBlock

from agents import AgentArchitecture
from schema import CheckLegislationRequest
from model import Clause, LegislationCheck


def get_graph_result(result: GraphResult) -> str | None:
    last_node = result.execution_order[-1]

    node = result.results.get(last_node.node_id)
    if not node or not getattr(node, "result", None):
        return None
    if isinstance(node.result, AgentResult):
        # TODO: this code does not support the case where the last node of the graph is a MultiAgent...
        content = node.result.message.get("content", [])
        return "".join(part.get("text", "") for part in content if isinstance(part, dict))
    else:
        return None


class GraphAgentArchitecture(AgentArchitecture):  # type: ignore[misc]
    """Graph agent architecture with structured analysis flow"""

    def analyze_clause(self, request: CheckLegislationRequest, clause: Clause) -> LegislationCheck:
        raise NotImplementedError("This is a work in progress")
        # # chunk document in smaller sizes to fit prompt cache and model input context window
        #
        #
        # # Document analyzer agent
        # doc_analyzer = Agent(
        #     model=self.bedrock_model,
        #     system_prompt="You are an expert document analyzer. Your task is to extract a list of legislation requirements that are related to the contract clause under analysis. Output the list of clauses, including reference for how to find them, your results will be used by a lawyer to check for violations.",
        # )
        #
        # # Clause evaluator agent
        # clause_evaluator = Agent(
        #     model=self.bedrock_model,
        #     system_prompt="You are a Lawyer specialized in finding violations. You will receive a list of possible legislation sections that are related to the clause under analysis. Compare the contract clause under analysis against each individual legislation section given as input and identify violations. If you are unsure, take a proactive stance and flag as a violation. The outputs will be reviewed by a human expert who can make the final judgement call.",
        # )
        #
        # # Final assessor agent
        # report_writer = Agent(
        #     model=self.bedrock_model,
        #     system_prompt="You are a final legal assessor. Synthesize analysis results into final violation/non-violation determination. For each analysis make sure to provide a 'compliant' or 'non-compliant' response and a synthesized analysis. If there are any violations, make sure to indicate in the end that the clause under analysis is 'non-compliant'",
        # )
        #
        # # Parser, so we get structured output, since graph does not support outputing structured output
        # parser = Agent(
        #     model=self.bedrock_model,
        #     system_prompt="Convert the input into a valid LegislationCheck JSON only."
        # )
        #
        # builder = GraphBuilder()
        # builder.add_node(doc_analyzer, "analyze")
        # builder.add_node(clause_evaluator, "evaluate")
        # builder.add_node(report_writer, "assess")
        #
        # builder.add_edge("analyze", "evaluate")
        # builder.add_edge("evaluate", "analyze")
        # builder.set_entry_point("analyze")
        #
        # graph = builder.build()
        #
        # prompt: list[ContentBlock] = [
        #     {
        #         "document": {
        #             "name": "legislation_document",
        #             "format": "pdf",
        #             "source": {  # type: ignore[typeddict-item, typeddict-unknown-key]
        #                 "s3Location": {
        #                     "uri": request.legislation_s3_uri
        #                 }
        #             }
        #         }
        #     },
        #     {
        #         "text": f"Please analyze the following contract clause for any violations against the legislation document provided:\n\nClause Text: {clause.text}\n\nProvide a detailed analysis of compliance and identify any specific violations or concerns.\n\nAlways respond in {request.language}. You have only one shot! Make your best effort, and return a response."
        #     },
        #     {
        #         "cachePoint": {
        #             "type": "default"
        #         }
        #     }
        # ]
        #
        # result = graph(prompt)
        # unstructured_text = get_graph_result(result)
        #
        # response = parser.structured_output(LegislationCheck, unstructured_text)
        #
        # return response
