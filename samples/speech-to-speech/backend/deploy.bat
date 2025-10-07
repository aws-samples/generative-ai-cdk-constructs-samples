@echo off
setlocal enabledelayedexpansion

REM Nova Sonic Solution Deployment Script for Windows
REM Complete one-step deployment for both frontend and backend

echo ================================================
echo    Nova Sonic Solution - Complete Deployment   
echo ================================================
echo.

REM Step 1: Check prerequisites
echo ================================================
echo Step 1: Checking Prerequisites
echo ================================================

REM Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed. Please install Python 3.12 or higher.
    exit /b 1
)
echo [SUCCESS] Python is installed

REM Check npm
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] npm is not installed. Please install Node.js and npm.
    exit /b 1
)
echo [SUCCESS] npm is installed

REM Check node
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed. Please install Node.js.
    exit /b 1
)
echo [SUCCESS] Node.js is installed

REM Check AWS CLI
where aws >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] AWS CLI is not installed. Please install AWS CLI.
    exit /b 1
)
echo [SUCCESS] AWS CLI is installed

REM Check Docker
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop.
    exit /b 1
)
echo [SUCCESS] Docker is installed

REM Check CDK
where cdk >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] AWS CDK is not installed. Installing now...
    call npm install -g aws-cdk
    echo [SUCCESS] AWS CDK installed successfully
) else (
    echo [SUCCESS] AWS CDK is installed
)

REM Step 2: Build Frontend
echo.
echo ================================================
echo Step 2: Building Frontend Application
echo ================================================

echo [INFO] Building frontend application...

REM Navigate to frontend directory
set FRONTEND_DIR=..\frontend

if not exist "%FRONTEND_DIR%" (
    echo [ERROR] Frontend directory not found at %FRONTEND_DIR%
    exit /b 1
)

cd %FRONTEND_DIR%

REM Check if package.json exists
if not exist "package.json" (
    echo [ERROR] package.json not found in frontend directory
    exit /b 1
)

REM Install dependencies
echo [INFO] Installing frontend dependencies...
call npm install

REM Build the frontend
echo [INFO] Building frontend ^(this may take a few minutes^)...
call npm run build

REM Verify build output exists
if not exist "dist" (
    echo [ERROR] Frontend build failed - dist directory not created
    exit /b 1
)

echo [SUCCESS] Frontend build completed successfully!

REM Return to backend directory
cd ..\backend

REM Step 3: Select deployment configuration
echo.
echo ================================================
echo Step 3: Select Deployment Configuration
echo ================================================
echo.
echo Please select your deployment option:
echo 1^) ECS Fargate ^(Default - Simpler, Lower Cost for Single App^)
echo 2^) EKS Fargate ^(Kubernetes - More Flexible, Better for Multiple Apps^)
echo.
set /p deploy_choice="Enter your choice (1 or 2): "

echo.
echo Please select your backend language:
echo 1^) Java ^(Default^)
echo 2^) Python
echo.
set /p lang_choice="Enter your choice (1 or 2): "

REM Set backend language context
if "%lang_choice%"=="2" (
    set BACKEND_CONTEXT=--context custom:backendLanguage=python
    echo [INFO] Selected: Python backend
) else (
    set BACKEND_CONTEXT=
    echo [INFO] Selected: Java backend
    REM Check for Gradle if Java is selected
    where gradle >nul 2>nul
    if !errorlevel! neq 0 (
        echo [WARNING] Gradle is not installed. Java build may fail.
        echo Please install Gradle 7.x or higher: https://gradle.org/install/
        set /p continue_choice="Continue anyway? (y/n): "
        if /i not "!continue_choice!"=="y" exit /b 1
    )
)

REM Step 4: Setup Python environment
echo.
echo ================================================
echo Step 4: Setting Up Python Environment
echo ================================================

REM Check for existing virtual environments
if exist "sonic" (
    echo [INFO] Using existing 'sonic' virtual environment...
    call sonic\Scripts\activate.bat
) else if exist ".venv" (
    echo [INFO] Using existing '.venv' virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [INFO] Creating new Python virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
)

REM Install dependencies
echo [INFO] Installing Python dependencies for CDK...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt >nul 2>&1
echo [SUCCESS] Python dependencies installed

REM Step 5: Bootstrap CDK
echo.
echo ================================================
echo Step 5: Checking CDK Bootstrap Status
echo ================================================

REM Get AWS region
for /f "tokens=*" %%i in ('aws configure get region') do set REGION=%%i
if "%REGION%"=="" (
    echo [ERROR] AWS region not configured. Please run 'aws configure' first.
    exit /b 1
)

echo [INFO] Checking CDK bootstrap status in region: %REGION%
aws cloudformation describe-stacks --stack-name CDKToolkit --region %REGION% >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Bootstrapping CDK ^(this is a one-time setup^)...
    call cdk bootstrap
    echo [SUCCESS] CDK bootstrap completed
) else (
    echo [SUCCESS] CDK already bootstrapped in region %REGION%
)

REM Step 6: Deploy the selected stack
echo.
echo ================================================
echo Step 6: Deploying Infrastructure
echo ================================================

if "%deploy_choice%"=="1" (
    echo [INFO] Deploying ECS Fargate stack...
    echo.
    echo This will:
    echo   - Build the backend container image
    echo   - Create VPC and networking resources
    echo   - Deploy ECS Fargate service
    echo   - Set up Cognito authentication
    echo   - Create CloudFront distribution
    echo   - Deploy frontend to S3
    echo.
    echo Estimated time: 10-15 minutes
    echo.
    
    REM Deploy ECS stack
    echo [INFO] Starting deployment of NovaSonicSolutionBackendStack ^(ECS Fargate^)...
    call cdk deploy NovaSonicSolutionBackendStack %BACKEND_CONTEXT% --require-approval=never
    
    echo [SUCCESS] ECS Fargate deployment complete!
    
    echo.
    echo ================================================
    echo Deployment Successful!
    echo ================================================
    echo.
    echo Next Steps:
    echo.
    echo 1. Get the CloudFront URL:
    echo    aws cloudformation describe-stacks --stack-name NovaSonicSolutionBackendStack --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDistributionDomainName'].OutputValue" --output text
    echo.
    echo 2. Access your application at the CloudFront URL
    echo.
    echo 3. Monitor logs in CloudWatch
    
) else if "%deploy_choice%"=="2" (
    echo [INFO] Deploying EKS Fargate stack...
    
    REM Check if kubectl is installed
    where kubectl >nul 2>nul
    if !errorlevel! neq 0 (
        echo [WARNING] kubectl is not installed. You won't be able to manage the cluster.
        echo Install kubectl from: https://kubernetes.io/docs/tasks/tools/
        set /p continue_choice="Continue anyway? (y/n): "
        if /i not "!continue_choice!"=="y" exit /b 1
    ) else (
        echo [SUCCESS] kubectl is installed
    )
    
    echo.
    echo This will:
    echo   - Build the backend container image
    echo   - Create VPC and networking resources
    echo   - Create EKS cluster with Fargate
    echo   - Deploy Kubernetes resources
    echo   - Set up Load Balancer
    echo   - Configure auto-scaling
    echo.
    echo Estimated time: 15-20 minutes ^(EKS cluster creation takes time^)
    echo.
    
    REM Deploy EKS stack
    echo [INFO] Starting deployment of NovaSonicSolutionEKSBackendStack ^(EKS Fargate^)...
    call cdk deploy NovaSonicSolutionEKSBackendStack --app "python app_eks.py" %BACKEND_CONTEXT% --require-approval=never
    
    echo [SUCCESS] EKS Fargate deployment complete!
    
    REM Set cluster name
    set CLUSTER_NAME=nova-sonic-eks-NovaSonicSolutionEKSBackendStack
    
    echo.
    echo ================================================
    echo Deployment Successful!
    echo ================================================
    echo.
    echo Next Steps:
    echo.
    echo 1. Configure kubectl to access your cluster:
    echo    aws eks update-kubeconfig --name %CLUSTER_NAME% --region %REGION%
    echo.
    echo 2. Wait for Load Balancer to be ready ^(3-5 minutes^), then check status:
    echo    kubectl get pods -n websocket-app
    echo.
    echo 3. Get the Load Balancer URL:
    echo    kubectl get service websocket-service -n websocket-app -o jsonpath="{.status.loadBalancer.ingress[0].hostname}"
    echo.
    echo 4. The WebSocket endpoint will be available at:
    echo    ws://^<LOAD_BALANCER_URL^>/
    echo.
    echo Useful monitoring commands:
    echo   - View logs: kubectl logs -n websocket-app -l app=websocket-server -f
    echo   - Check HPA: kubectl get hpa -n websocket-app
    echo   - Scale manually: kubectl scale deployment websocket-server -n websocket-app --replicas=5
    
) else (
    echo [ERROR] Invalid choice. Please run the script again and select 1 or 2.
    exit /b 1
)

echo.
echo ================================================
echo Important Information
echo ================================================
echo.
if "%deploy_choice%"=="1" (
    echo - Stack Name: NovaSonicSolutionBackendStack
) else (
    echo - Stack Name: NovaSonicSolutionEKSBackendStack
)
echo - Region: %REGION%
if "%lang_choice%"=="2" (
    echo - Backend Language: Python
) else (
    echo - Backend Language: Java
)
echo - Virtual environment is still activated
echo.
echo To clean up resources and avoid charges:
if "%deploy_choice%"=="1" (
    echo   cdk destroy NovaSonicSolutionBackendStack
) else (
    echo   cdk destroy NovaSonicSolutionEKSBackendStack --app "python app_eks.py"
)
echo.
echo To deactivate the Python virtual environment:
echo   deactivate
echo.
echo [SUCCESS] Deployment script completed successfully!

endlocal
