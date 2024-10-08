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

from llama_index.core import Document
from llama_index.core import Settings
from llama_index.core import StorageContext
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.bedrock import BedrockEmbedding
from llama_index.llms.bedrock import Bedrock

def handler(event, context):
    print("Hello from Lambda!")
    print(event)
    print(context)
    
    doc = Document(text='Schreck is the author of the story "Sir Popycock: Adventurousness in a Family" and went to Torrey Pines high school in San Diego California')
    documents = []
    documents.append(doc)
    
    model_name = "amazon.titan-embed-g1-text-02"
    model = "amazon.titan-text-express-v1" 

    embed_model = BedrockEmbedding(
        model_name=model_name
    )
    Settings.llm = Bedrock(model=model)

    storage_context = StorageContext.from_defaults()
    
    index = VectorStoreIndex.from_documents(
        documents=documents,
        show_progress=False,
        transformations=None,
        callback_manager=None,
        embed_model=embed_model,
        storage_context=storage_context,
    )
    
    query_engine = index.as_query_engine()
    
    result1 = query_engine.query('Where did the author go to school?')
    print(result1.response)
    
    return (event)
