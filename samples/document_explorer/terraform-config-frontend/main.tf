module "serverless-streamlit-app" {
  source = "aws-ia/serverless-streamlit-app/aws"
  version = "1.1.0"
  path_to_app_dir = "../client_app/"
  app_name    = "streamlit-app"
  environment = "dev"
  app_version = "v0.0.1" 
}

# Update existing Cognito User Pool Client
resource "aws_cognito_user_pool_client" "update_client" {
  user_pool_id  = var.user_pool_id  
  name          = var.client_name
  callback_urls = ["${module.serverless-streamlit-app.streamlit_cloudfront_distribution_url}/", "http://localhost:8501/"]
  logout_urls   = ["${module.serverless-streamlit-app.streamlit_cloudfront_distribution_url}/", "http://localhost:8501/"]
  allowed_oauth_flows_user_pool_client = true
  refresh_token_validity = 1
  access_token_validity = 60
  id_token_validity        = 60
  token_validity_units {
    refresh_token = "days"
    access_token = "minutes"
    id_token = "minutes"
  }
  explicit_auth_flows = ["ALLOW_CUSTOM_AUTH", "ALLOW_USER_PASSWORD_AUTH", "ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
}

resource "aws_cognito_identity_pool" "update_pool" {
  identity_pool_name = var.client_name
  allow_classic_flow = true
  cognito_identity_providers {
    client_id               = var.client_id
    provider_name           = "cognito-idp.${var.region}.amazonaws.com/${var.user_pool_id}"
    server_side_token_check = false
  }
}