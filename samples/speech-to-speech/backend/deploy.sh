#!/bin/bash

# Nova Sonic Solution Deployment Script
# Complete one-step deployment for both frontend and backend

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if a command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed. Please install $1 first."
        if [ "$1" == "gradle" ] && [ "$2" == "optional" ]; then
            print_warning "Gradle is optional but recommended for Java backend builds."
            return 0
        fi
        exit 1
    fi
    print_success "$1 is installed"
}

# Function to build frontend
build_frontend() {
    print_status "Building frontend application..."
    
    # Navigate to frontend directory
    FRONTEND_DIR="../frontend"
    
    if [ ! -d "$FRONTEND_DIR" ]; then
        print_error "Frontend directory not found at $FRONTEND_DIR"
        exit 1
    fi
    
    cd "$FRONTEND_DIR"
    
    # Check if package.json exists
    if [ ! -f "package.json" ]; then
        print_error "package.json not found in frontend directory"
        exit 1
    fi
    
    # Install dependencies
    print_status "Installing frontend dependencies..."
    npm install
    
    # Build the frontend
    print_status "Building frontend (this may take a few minutes)..."
    npm run build
    
    # Verify build output exists
    if [ ! -d "dist" ]; then
        print_error "Frontend build failed - dist directory not created"
        exit 1
    fi
    
    print_success "Frontend build completed successfully!"
    
    # Return to backend directory
    cd ../backend
}

echo "================================================"
echo "   Nova Sonic Solution - Complete Deployment   "
echo "================================================"
echo ""

# Step 1: Check prerequisites
echo "================================================"
echo "Step 1: Checking Prerequisites"
echo "================================================"

check_command python3
check_command npm
check_command node
check_command aws
check_command docker

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    print_warning "AWS CDK is not installed. Installing now..."
    npm install -g aws-cdk
    print_success "AWS CDK installed successfully"
else
    print_success "AWS CDK is installed"
fi

# Step 2: Build Frontend
echo ""
echo "================================================"
echo "Step 2: Building Frontend Application"
echo "================================================"

build_frontend

# Step 3: Select deployment configuration
echo ""
echo "================================================"
echo "Step 3: Select Deployment Configuration"
echo "================================================"
echo ""
echo "Please select your deployment option:"
echo "1) ECS Fargate (Default - Simpler, Lower Cost for Single App)"
echo "2) EKS Fargate (Kubernetes - More Flexible, Better for Multiple Apps)"
echo ""
read -p "Enter your choice (1 or 2): " deploy_choice

echo ""
echo "Please select your backend language:"
echo "1) Java (Default)"
echo "2) Python"
echo ""
read -p "Enter your choice (1 or 2): " lang_choice

# Set backend language context
if [ "$lang_choice" == "2" ]; then
    BACKEND_CONTEXT="--context custom:backendLanguage=python"
    print_status "Selected: Python backend"
else
    BACKEND_CONTEXT=""
    print_status "Selected: Java backend"
    # Check for Gradle if Java is selected
    check_command gradle optional
fi

# Step 4: Setup Python environment
echo ""
echo "================================================"
echo "Step 4: Setting Up Python Environment"
echo "================================================"

# Use existing sonic environment if it exists, otherwise create .venv
if [ -d "sonic" ]; then
    print_status "Using existing 'sonic' virtual environment..."
    source sonic/bin/activate
elif [ -d ".venv" ]; then
    print_status "Using existing '.venv' virtual environment..."
    source .venv/bin/activate
else
    print_status "Creating new Python virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
fi

# Install dependencies
print_status "Installing Python dependencies for CDK..."
python3 -m pip install --upgrade pip --quiet
python3 -m pip install -r requirements.txt --quiet
print_success "Python dependencies installed"

# Step 5: Bootstrap CDK
echo ""
echo "================================================"
echo "Step 5: Checking CDK Bootstrap Status"
echo "================================================"

REGION=$(aws configure get region)
if [ -z "$REGION" ]; then
    print_error "AWS region not configured. Please run 'aws configure' first."
    exit 1
fi

print_status "Checking CDK bootstrap status in region: $REGION"
if ! aws cloudformation describe-stacks --stack-name CDKToolkit --region $REGION >/dev/null 2>&1; then
    print_status "Bootstrapping CDK (this is a one-time setup)..."
    cdk bootstrap
    print_success "CDK bootstrap completed"
else
    print_success "CDK already bootstrapped in region $REGION"
fi

# Step 6: Deploy the selected stack
echo ""
echo "================================================"
echo "Step 6: Deploying Infrastructure"
echo "================================================"

case $deploy_choice in
    1)
        print_status "Deploying ECS Fargate stack..."
        echo ""
        echo "This will:"
        echo "  • Build the backend container image"
        echo "  • Create VPC and networking resources"
        echo "  • Deploy ECS Fargate service"
        echo "  • Set up Cognito authentication"
        echo "  • Create CloudFront distribution"
        echo "  • Deploy frontend to S3"
        echo ""
        echo "Estimated time: 10-15 minutes"
        echo ""
        
        # Deploy ECS stack
        print_status "Starting deployment of NovaSonicSolutionBackendStack (ECS Fargate)..."
        cdk deploy NovaSonicSolutionBackendStack $BACKEND_CONTEXT --require-approval=never
        
        print_success "ECS Fargate deployment complete!"
        
        echo ""
        echo "================================================"
        echo "✅ Deployment Successful!"
        echo "================================================"
        echo ""
        echo "📋 Next Steps:"
        echo ""
        echo "1. Get the CloudFront URL:"
        echo "   ${GREEN}aws cloudformation describe-stacks --stack-name NovaSonicSolutionBackendStack --query 'Stacks[0].Outputs[?OutputKey==\`CloudFrontDistributionDomainName\`].OutputValue' --output text${NC}"
        echo ""
        echo "2. Access your application at the CloudFront URL"
        echo ""
        echo "3. Monitor logs in CloudWatch"
        ;;
        
    2)
        print_status "Deploying EKS Fargate stack..."
        
        # Check if kubectl is installed
        if ! command -v kubectl &> /dev/null; then
            print_warning "kubectl is not installed. You won't be able to manage the cluster."
            echo "Install kubectl from: https://kubernetes.io/docs/tasks/tools/"
            read -p "Continue anyway? (y/n): " continue_choice
            if [ "$continue_choice" != "y" ]; then
                exit 1
            fi
        else
            print_success "kubectl is installed"
        fi
        
        echo ""
        echo "This will:"
        echo "  • Build the backend container image"
        echo "  • Create VPC and networking resources"
        echo "  • Create EKS cluster with Fargate"
        echo "  • Deploy Kubernetes resources"
        echo "  • Set up Load Balancer"
        echo "  • Configure auto-scaling"
        echo ""
        echo "⏱️  Estimated time: 15-20 minutes (EKS cluster creation takes time)"
        echo ""
        
        # Deploy EKS stack
        print_status "Starting deployment of NovaSonicSolutionEKSBackendStack (EKS Fargate)..."
        cdk deploy NovaSonicSolutionEKSBackendStack --app "python app_eks.py" $BACKEND_CONTEXT --require-approval=never
        
        print_success "EKS Fargate deployment complete!"
        
        # Get cluster name from the stack
        CLUSTER_NAME="nova-sonic-eks-NovaSonicSolutionEKSBackendStack"
        
        echo ""
        echo "================================================"
        echo "✅ Deployment Successful!"
        echo "================================================"
        echo ""
        echo "📋 Next Steps:"
        echo ""
        echo "1. Configure kubectl to access your cluster:"
        echo "   ${GREEN}aws eks update-kubeconfig --name $CLUSTER_NAME --region $REGION${NC}"
        echo ""
        echo "2. Wait for Load Balancer to be ready (3-5 minutes), then check status:"
        echo "   ${GREEN}kubectl get pods -n websocket-app${NC}"
        echo ""
        echo "3. Get the Load Balancer URL:"
        echo "   ${GREEN}kubectl get service websocket-service -n websocket-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'${NC}"
        echo ""
        echo "4. The WebSocket endpoint will be available at:"
        echo "   ${GREEN}ws://<LOAD_BALANCER_URL>/${NC}"
        echo ""
        echo "📊 Useful monitoring commands:"
        echo "   • View logs: kubectl logs -n websocket-app -l app=websocket-server -f"
        echo "   • Check HPA: kubectl get hpa -n websocket-app"
        echo "   • Scale manually: kubectl scale deployment websocket-server -n websocket-app --replicas=5"
        ;;
        
    *)
        print_error "Invalid choice. Please run the script again and select 1 or 2."
        exit 1
        ;;
esac

echo ""
echo "================================================"
echo "📝 Important Information"
echo "================================================"
echo ""
echo "• Stack Name: $([ "$deploy_choice" == "1" ] && echo "NovaSonicSolutionBackendStack" || echo "NovaSonicSolutionEKSBackendStack")"
echo "• Region: $REGION"
echo "• Backend Language: $([ "$lang_choice" == "2" ] && echo "Python" || echo "Java")"
echo "• Virtual environment is still activated"
echo ""
echo "To clean up resources and avoid charges:"
echo "  ${YELLOW}cdk destroy $([ "$deploy_choice" == "1" ] && echo "NovaSonicSolutionBackendStack" || echo "NovaSonicSolutionEKSBackendStack --app \"python app_eks.py\"")${NC}"
echo ""
echo "To deactivate the Python virtual environment:"
echo "  ${YELLOW}deactivate${NC}"
echo ""
print_success "Deployment script completed successfully! 🎉"
