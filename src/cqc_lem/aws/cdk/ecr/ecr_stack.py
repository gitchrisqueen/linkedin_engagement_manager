import cdk_ecr_deployment as ecrdeploy
from aws_cdk import (
    NestedStack,
    aws_ecr as ecr,
    aws_ecr_assets as ecr_assets,
    Aws
)
from aws_cdk.aws_ecr_assets import DockerImageAsset, Platform
from constructs import Construct

from cqc_lem import compose_dir


class EcrStack(NestedStack):

    def __init__(self, scope: Construct, id: str, **kwargs, ) -> None:
        super().__init__(scope, id, **kwargs)

        # Creat ecr repository that will host the docker image for our services
        Repository = ecr.Repository(self, "Repository", repository_name="cqc-lem")

        docker_dir = compose_dir + '/local/'

        # The docker images were built on a M1 Macbook Pro, you may have to rebuild your images
        docker_asset = DockerImageAsset(self, "dockerAsset",
                                        directory=docker_dir,
                                        build_args={
                                            "API_BASE_URL_BUILD_ARG": "api.cqc-lem.local",
                                            # This argument will be passed to the dockerfile and used as the API_BASE_URL
                                        },
                                        platform=Platform.LINUX_AMD64,
                                        invalidation=ecr_assets.DockerImageAssetInvalidationOptions(
                                            build_args=False
                                        )
                                        )

        # Deploying images to ECR
        ecrdeploy.ECRDeployment(self, "DeployImage",
                                src=ecrdeploy.DockerImageName(docker_asset.image_uri),
                                dest=ecrdeploy.DockerImageName(
                                    f"{Aws.ACCOUNT_ID}.dkr.ecr.{Aws.REGION}.amazonaws.com/cqc-lem:latest")
                                )

        # Exporting values to be used in other stacks
        self.docker_asset = docker_asset
