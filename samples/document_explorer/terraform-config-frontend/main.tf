module "serverless-streamlit-app" {
  source = "aws-ia/serverless-streamlit-app/aws" 
  path_to_app_dir = "../client_app/"
  app_name    = "streamlit-app"
  environment = "prod"
  app_version = "v0.0.1" # used as one of the tags for Docker image. Update this when you wish to push new changes to ECR.
}

# Update existing Cognito User Pool Client
resource "aws_cognito_user_pool_client" "update_client" {
  user_pool_id = var.user_pool_id  
  name         = var.client_name
  callback_urls = ["${module.serverless-streamlit-app.streamlit_cloudfront_distribution_url}", "http://localhost:8501/"]
  logout_urls = ["${module.serverless-streamlit-app.streamlit_cloudfront_distribution_url}", "http://localhost:8501/"]
}
