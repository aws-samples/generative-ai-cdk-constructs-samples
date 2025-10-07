# Deployment Guide - Nova Sonic Solution

This guide provides step-by-step instructions for deploying either the ECS or EKS version of the Nova Sonic Solution.

## Quick Start - One-Step Deployment

The easiest way to deploy is using the automated deployment script that handles everything:

```bash
cd samples/speech-to-speech/backend
./deploy.sh  # On Windows: deploy.bat
```

The script will:
1. Check all prerequisites
2. Build the frontend automatically
3. Set up Python environment
4. Bootstrap CDK if needed
5. Deploy your chosen configuration

When prompted:
- Select deployment option (1 for ECS, 2 for EKS)
- Select backend language (1 for Java, 2 for Python)

## Prerequisites

The deployment script will check for these automatically:
- Python 3.12 or higher
- Node.js v18.12.1 or higher
- AWS CLI configured
- Docker Desktop
- AWS CDK (will be installed if missing)
- Gradle 7.x or higher (optional, for Java backend)
- kubectl (optional, for EKS management)

## Manual Deployment Steps

If you prefer manual deployment or need to customize the process:

### Step 1: Build the Frontend

```bash
cd samples/speech-to-speech/frontend
npm install
npm run build
cd ..
```

### Step 2: Set Up Python Environment

```bash
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate.bat

# Install pip if missing (common issue with some Python installations)
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py
rm get-pip.py

# Now upgrade pip and install dependencies
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### Alternative: If pip is still missing

If you're using an existing virtual environment (like 'sonic') and pip is missing:

```bash
# Deactivate current environment
deactivate

# Create a fresh virtual environment
python3 -m venv .venv

# Activate the new environment
source .venv/bin/activate

# Install pip using ensurepip
python3 -m ensurepip --upgrade

# Now install dependencies
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

## Step 3: Bootstrap CDK (First Time Only)

```bash
# Make sure you're in the backend directory with virtual environment activated
cdk bootstrap
```

## Option A: Deploy ECS Fargate Version

### For Java Backend (Default):
```bash
# Make sure you're in the backend directory with virtual environment activated
cdk deploy NovaSonicSolutionBackendStack --require-approval=never
```

### For Python Backend:
```bash
# Make sure you're in the backend directory with virtual environment activated
cdk deploy NovaSonicSolutionBackendStack --context custom:backendLanguage=python --require-approval=never
```

### Get CloudFront URL:
```bash
aws cloudformation describe-stacks \
  --stack-name NovaSonicSolutionBackendStack \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionDomainName`].OutputValue' \
  --output text
```

## Option B: Deploy EKS Fargate Version

### For Java Backend (Default):
```bash
# Make sure you're in the backend directory with virtual environment activated
cdk deploy NovaSonicSolutionEKSBackendStack --app "python3 app_eks.py" --require-approval=never
```

### For Python Backend:
```bash
# Make sure you're in the backend directory with virtual environment activated
cdk deploy NovaSonicSolutionEKSBackendStack --app "python3 app_eks.py" --context custom:backendLanguage=python --require-approval=never
```

**Note**: EKS cluster creation takes 15-20 minutes.

### Post-Deployment Steps for EKS:

1. **Configure kubectl**:
```bash
aws eks update-kubeconfig --name nova-sonic-eks-NovaSonicSolutionEKSBackendStack --region <your-region>
```

2. **Check pod status**:
```bash
kubectl get pods -n websocket-app
```

3. **Get Load Balancer URL** (wait 3-5 minutes after deployment):
```bash
kubectl get service websocket-service -n websocket-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

## Troubleshooting

### Virtual Environment Issues

If you encounter "pip: command not found" errors:

1. Ensure virtual environment is activated:
```bash
# You should see (.venv) in your terminal prompt
which python3
# Should show: /path/to/backend/.venv/bin/python3
```

2. If pip is still not found, use:
```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### CDK Issues

If CDK commands fail:

1. Ensure you're in the `backend` directory
2. Ensure virtual environment is activated
3. Check CDK version:
```bash
cdk --version
```

4. If CDK is not found:
```bash
npm install -g aws-cdk
```

### Path Issues

Always run commands from the `backend` directory:
```bash
cd samples/speech-to-speech/backend
```

### Java Build Issues

For Java backend, if you see Gradle errors:

1. Check Gradle installation:
```bash
gradle --version
```

2. Install Gradle if needed:
- macOS: `brew install gradle`
- Linux: Follow https://gradle.org/install/
- Windows: Download from https://gradle.org/install/

## Clean Up

### Delete ECS Stack:
```bash
cdk destroy NovaSonicSolutionBackendStack
```

### Delete EKS Stack:
```bash
cdk destroy NovaSonicSolutionEKSBackendStack --app "python3 app_eks.py"
```

## Summary of Commands

### Quick Deploy ECS (Java):
```bash
cd samples/speech-to-speech/backend
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
# Bootstrap if needed (skip if already done)
aws cloudformation describe-stacks --stack-name CDKToolkit >/dev/null 2>&1 || cdk bootstrap
cdk deploy NovaSonicSolutionBackendStack --require-approval=never
```

### Quick Deploy EKS (Java):
```bash
cd samples/speech-to-speech/backend

# If you have an existing 'sonic' environment, use it:
source sonic/bin/activate
# OR create a new one:
# python3 -m venv .venv
# source .venv/bin/activate

# Ensure pip is installed
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Bootstrap if needed (skip if already done)
aws cloudformation describe-stacks --stack-name CDKToolkit >/dev/null 2>&1 || cdk bootstrap --app "python3 app_eks.py"

# Deploy EKS stack
cdk deploy NovaSonicSolutionEKSBackendStack --app "python3 app_eks.py" --require-approval=never
```

### Direct EKS Deployment (Simplest):
If you're having issues with the scripts, use this direct approach:

```bash
# From the backend directory with your sonic environment activated
cd samples/speech-to-speech/backend
source sonic/bin/activate

# Install dependencies if not already installed
python3 -m pip install aws-cdk-lib constructs cdk_nag

# Deploy directly (skip bootstrap if already done)
npx cdk deploy NovaSonicSolutionEKSBackendStack --app "python3 app_eks.py" --require-approval=never
```

## Important Notes

- The frontend must be built before deploying the backend
- Python dependencies are always required (CDK is written in Python)
- Java/Gradle is only needed if using Java backend
- kubectl is only needed for managing EKS clusters after deployment
- Always work from the `backend` directory
- Always activate the virtual environment before running CDK commands
