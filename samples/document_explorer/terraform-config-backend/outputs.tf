output "cognito_user_client_secret" {
  description = "ARN of the AWS Secrets Manager secret for Cognito client secret key"
  value       = module.genai_doc_ingestion.cognito_user_client_secret
}

output "cognito_domain" {
  description = "The Cognito domain."
  value       = module.genai_doc_ingestion.cognito_domain
}

output "region" {
  description = "The AWS region."
  value       = module.genai_doc_ingestion.region
}

output "user_pool_id" {
  description = "The Cognito user pool ID."
  value       = module.genai_doc_ingestion.user_pool_id
}

output "client_id" {
  description = "The Cognito client ID."
  value       = module.genai_doc_ingestion.client_id
}

output "identity_pool_id" {
  description = "The Cognito identity pool ID."
  value       = module.genai_doc_ingestion.identity_pool_id
}

output "authenticated_role_arn" {
  description = "The authenticated role ARN."
  value       = module.genai_doc_ingestion.authenticated_role_arn
}

output "graphql_endpoint" {
  description = "The GraphQL endpoint."
  value       = module.genai_doc_ingestion.graphql_endpoint
} 

output "s3_input_bucket" {
  description = "The S3 input bucket."
  value       = module.genai_doc_ingestion.s3_input_bucket
}

output "s3_processed_bucket" {
  description = "The S3 processed bucket."
  value       = module.genai_doc_ingestion.s3_processed_bucket
}

output "client_name" {
  description = "The Cognito client name."
  value       = module.genai_doc_ingestion.client_name
}