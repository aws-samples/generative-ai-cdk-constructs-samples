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
            docker_image_asset_directory=path.dirname(__file__) + path.sep + ".." + path.sep + "docker",
            # memory_limit_mib=1024,
            container_logging_level="DEBUG",
        )
