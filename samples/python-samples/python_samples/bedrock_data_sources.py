from aws_cdk import (
    # Duration,
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    CfnOutput,
    Duration as Duration
    # aws_sqs as sqs,
)
from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import (
    bedrock
)

class BedrockDataSourcesStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a data source
        web_crawler_data_source = bedrock.WebCrawlerDataSource(
            self,
            "MyWebCrawlerDataSource",
            data_source_name="my-web-crawler-data-source",
            description="Data source for company website",
            source_urls=["https://www.example.com"],
            crawling_scope=bedrock.CrawlingScope.SUBDOMAINS,
            crawling_rate=300,
            filters={
                "includePatterns": ["/blog/", "/docs/"],
                "excludePatterns": ["/private/", "/admin/"],
            },
            max_pages=1000,
        )