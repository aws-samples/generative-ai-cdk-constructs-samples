import os
from pathlib import Path

from aws_cdk import Aws, BundlingOptions, BundlingOutput, DockerImage, RemovalPolicy
from aws_cdk import aws_lambda as _lambda
from aws_cdk.aws_s3_assets import Asset
from constructs import Construct

AWS_LAMBDA_POWERTOOL_LAYER_VERSION_ARN = "arn:aws:lambda:{region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:45"

class GraphQLLambdaLayers(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._architecture = _lambda.Architecture.X86_64
        self._build_image_version = "latest"
        self._runtime = _lambda.Runtime.PYTHON_3_13

        # AWS Lambda PowerTools
        self.aws_lambda_powertools_layer = _lambda.LayerVersion.from_layer_version_arn(
            self,
            f"{construct_id}-lambda-powertools-layer",
            layer_version_arn=AWS_LAMBDA_POWERTOOL_LAYER_VERSION_ARN.format(region=Aws.REGION),
        )

        #  requests auth
        root_path = Path(__file__).parent.parent.parent
        self.requests_auth_layer = self._create_layer_from_asset(
            layer_name=f"{construct_id}-requests-auth-layer",
            path_to_layer_assets=os.path.join(root_path, "assets/lambda/layers/requests_auth"),
            description="Lambda layer that contains libraries for requests and authentification from s3 files",
        )


    def _create_layer_from_asset(
        self, layer_name: str, path_to_layer_assets: str, description: str
    ) -> _lambda.LayerVersion:
        """Create a layer from an S3 asset

        This is a valid option if the layer only requires to install Python packages on top of base Lambda Python images

        Parameters
        ----------
        layer_name : str
            Name of the layer
        path_to_layer_assets : str
            the disk location of the asset that contains a `requirements.txt` file and, `*.whl` files if needed
        description : str
            describe what the purpose of the layer

        Returns
        -------
        _lambda.LayerVersion
            Lambda layer
        """
        ecr = self._runtime.bundling_image.image + f":{self._build_image_version}-{self._architecture.to_string()}"
        bundling_option = BundlingOptions(
            image=DockerImage(ecr),
            command=[
                "bash",
                "-c",
                "pip --no-cache-dir install -r requirements.txt -t /asset-output/python",
            ],
            output_type=BundlingOutput.AUTO_DISCOVER,
            platform=self._architecture.docker_platform,
            network="host",
        )
        layer_asset = Asset(self, f"{layer_name}-BundledAsset", path=path_to_layer_assets, bundling=bundling_option)

        return _lambda.LayerVersion(
            self,
            layer_name,
            code=_lambda.Code.from_bucket(layer_asset.bucket, layer_asset.s3_object_key),
            compatible_runtimes=[self._runtime],
            compatible_architectures=[self._architecture],
            removal_policy=RemovalPolicy.DESTROY,
            layer_version_name=layer_name,
            description=description,
        )
