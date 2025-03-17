# Resources Created by the Solution

This document provides a comprehensive list of all AWS resources created by this solution.

## Compute Resources
- **ECS Fargate Cluster**
  - Task Definition
  - Fargate Service
  - Container running Streamlit application
  - CloudWatch Log Group for container logs

## Networking
- **VPC Resources**
  - VPC with 2 Availability Zones
  - Public Subnets
  - Private Subnets
  - NAT Gateway
  - Internet Gateway
  - Route Tables
  - Network ACLs

- **Load Balancer**
  - Application Load Balancer
  - ALB Target Group
  - ALB Listener (Port 80)

- **Security Groups**
  - ALB Security Group
  - ECS Fargate Service Security Group

## Authentication & Authorization
- **Amazon Cognito**
  - User Pool
  - User Pool Client
  - User Pool Domain

## API & GraphQL
- **AWS AppSync**
  - GraphQL API
  - API Schema
  - API Resolvers
  - WebSocket API Endpoint

## Storage & Secrets
- **AWS Secrets Manager**
  - AppSync Endpoint Secret
  - Cognito App Client Secret
  - Cognito Domain Prefix Secret
  - Region Secret
  - Redirect URI Secret
  - Logout URI Secret

## AI/ML
- **Amazon Bedrock**
  - Bedrock Agent
  - Agent Actions
  - Agent Schema

## IAM Resources
- **IAM Roles**
  - ECS Task Role
  - ECS Task Execution Role
  - AppSync Service Role
  - Bedrock Agent Role

- **IAM Policies**
  - Task Role Policies
  - Task Execution Role Policies
  - AppSync Service Role Policies
  - Bedrock Agent Role Policies

## Logging & Monitoring
- **CloudWatch**
  - Container Log Groups
  - ALB Access Logs
  - VPC Flow Logs
  - Metric Alarms (if configured)

## Resource Naming Convention
All resources are prefixed with the stack name and construct ID for easy identification:
- Stack Name: `{stack-name}`
- Construct ID: `{construct-id}`

## Resource Dependencies
- VPC is required for ECS Fargate and ALB deployment
- Cognito User Pool is required for authentication
- AppSync API depends on Cognito for authorization
- Secrets Manager secrets are used by the ECS tasks
- Bedrock Agent depends on the AppSync API for integration

## Clean Up
When destroying this solution through CDK, all resources will be removed except:
1. CloudWatch Log Groups
2. Any manually created resources not part of the CDK stack

## Notes
- Some resources may incur costs even when not actively used
- NAT Gateway is deployed in a single AZ to minimize costs
- ALB is internet-facing and restricted to CloudFront IPs