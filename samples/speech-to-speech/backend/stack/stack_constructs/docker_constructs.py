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

from aws_cdk import (
    aws_ecs as ecs,
    aws_ecr_assets as ecr_assets,
)
from constructs import Construct

class DockerImageAssetConstruct(Construct):
    """
    A construct that creates a Docker container image from a local Dockerfile.
    
    This construct builds a Docker image from a local directory and makes it
    available for use in both ECS tasks and EKS deployments.
    
    Parameters:
    - scope (Construct): The scope in which this construct is defined.
    - construct_id (str): The unique identifier for this construct.
    - directory (str): The directory containing the Dockerfile and application code.
    - file (str): The name of the Dockerfile (default: 'Dockerfile').
    - platform (ecr_assets.Platform): The platform to use for the Docker image (default: ecr_assets.Platform.LINUX_ARM64).
    """
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        directory: str,
        file: str = "Dockerfile",
        platform: ecr_assets.Platform = ecr_assets.Platform.LINUX_ARM64,
    ):
        super().__init__(scope, construct_id)
        
        # Create Docker image asset
        self.asset = ecr_assets.DockerImageAsset(
            self,
            "DockerAsset",
            directory=directory,
            file=file,
            platform=platform,
        )
        
        # For backward compatibility with ECS
        self.image = ecs.ContainerImage.from_docker_image_asset(self.asset)
