# - Cognito -
variable "user_pool_id" {
  description = "The id of the Cognito user pool"
  type        = string
}
variable "client_name" {
  description = "The name of the Cognito user pool client"
  type        = string
}
variable "client_id" {
  description = "The id of the Cognito user pool client"
  type        = string
}
variable "region" {
  description = "The AWS region"
  type        = string
}
