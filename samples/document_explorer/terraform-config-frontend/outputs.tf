output "streamlit_ecr_repo_image_uri" {
  value = module.serverless-streamlit-app.streamlit_ecr_repo_image_uri
}
output "streamlit_alb_dns_name" {
  value = module.serverless-streamlit-app.streamlit_alb_dns_name
}
output "streamlit_cloudfront_distribution_url" {
  value = "${module.serverless-streamlit-app.streamlit_cloudfront_distribution_url}/"
}
output "azs" {
  value = module.serverless-streamlit-app.azs

}
