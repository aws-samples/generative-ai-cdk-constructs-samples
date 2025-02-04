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
from os import (
    path,
)

from aws_cdk import (
    Stack,
)
from constructs import (
    Construct,
)

from cdklabs.generative_ai_cdk_constructs import ( 
    LlamaIndexDataLoaderProps, 
    LlamaIndexDataLoader,
)

class LlamaindexBasicDataLoaderStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        data_loader = LlamaIndexDataLoader(
            self, "LlamaIndexDataLoader",
            # Uncomment the next line to change from the default docker image
            # docker_image_asset_directory=path.dirname(__file__) + path.sep + ".." + path.sep + "docker",
            container_logging_level="DEBUG",
        )

        self.template_options.description= "Description: (uksb-1tupboc43) (tag: llamaindex data loader sample)",