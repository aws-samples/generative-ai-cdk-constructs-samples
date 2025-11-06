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

# tools/kb_retrieve_factory.py
import os
from typing import Optional
import boto3
from strands import tool

def make_kb_retrieve_tool(
    kb_id: str,
    law_id: str,
    *,
    region: str = os.getenv("AWS_REGION", "us-east-1"),
    default_k: int = 12,
):
    rt = boto3.client("bedrock-agent-runtime", region_name=region)

    @tool(
        name=f"kb_retrieve_{law_id}",
        description=f"Retrieve passages for law_id={law_id} from Knowledge Base {kb_id}. "
                    "Args: query (str), k (int, optional), section_prefix (str, optional)."
    )
    def kb_retrieve(
        query: str,
        k: int = default_k,
        section_prefix: Optional[str] = None,
    ):
        print(f"KB TOOL CALLED: query='{query[:100]}...', k={k}, law_id={law_id}")
        
        flt = {"equals": {"key": "law_id", "value": law_id}}
        if section_prefix:
            flt = {"andAll": [flt, {"startsWith": {"key": "section_path", "value": section_prefix}}]}

        print(f"KB FILTER: {flt}")

        try:
            resp = rt.retrieve(
                knowledgeBaseId=kb_id,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "filter": flt,
                        "numberOfResults": k,
                        "overrideSearchType": "HYBRID",
                    }
                },
            )
            print(f"KB RESPONSE: Found {len(resp.get('retrievalResults', []))} results")
        except Exception as e:
            print(f"KB TOOL ERROR: {e}")
            return {"status": "error", "message": str(e)}

        hits = []
        for r in resp.get("retrievalResults", []):
            hits.append({
                "text": r.get("content", {}).get("text", ""),
                "score": r.get("score"),
                "meta": r.get("metadata", {}),
                "loc": r.get("location", {}),
            })
        
        if hits:
            print(f"KB TOOL SUCCESS: {len(hits)} results, first result: {hits[0]['text'][:200]}...")
        else:
            print("KB TOOL WARNING: No results found")

        return {"status": "success", "content": [{"json": {"results": hits}}]}

    return kb_retrieve
