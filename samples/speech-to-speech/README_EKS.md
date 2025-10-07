# Nova Sonic Solution - EKS Deployment

## Overview

This document describes the Amazon EKS (Elastic Kubernetes Service) deployment option for the Nova Sonic Solution. This deployment uses EKS with AWS Fargate for a fully serverless Kubernetes experience, providing an alternative to the ECS Fargate deployment.

## Architecture Comparison

### ECS Fargate (Original)
- Uses Amazon ECS for container orchestration
- Direct integration with AWS services
- Simpler setup and management
- Lower operational overhead

### EKS Fargate (This Implementation)
- Uses Kubernetes for container orchestration
- Serverless pods with AWS Fargate
- Kubernetes ecosystem compatibility
- More flexibility and portability

## Key Features of EKS Implementation

### Pure Fargate Approach
- **No EC2 nodes to manage**: All workloads run on AWS Fargate
- **Automatic scaling**: Pods scale based on demand
- **Pay-per-pod pricing**: Only pay for resources pods actually use
- **Enhanced security**: Each pod runs in its own isolated environment

### Components
1. **EKS Cluster**: Managed Kubernetes control plane
2. **Fargate Profiles**: Define which pods run on Fargate
3. **IRSA**: IAM Roles for Service Accounts for fine-grained permissions
4. **AWS Load Balancer Controller**: Manages NLB for WebSocket traffic
5. **Horizontal Pod Autoscaler**: Automatic pod scaling based on metrics

## Prerequisites

In addition to the prerequisites from the main README, you'll need:

- [kubectl](https://kubernetes.io/docs/tasks/tools/) - Kubernetes command-line tool
- [eksctl](https://eksctl.io/installation/) (optional) - EKS management tool
- [Helm](https://helm.sh/docs/intro/install/) - Package manager for Kubernetes

## Deployment Instructions

### 1. Build the Frontend (if not already done)

```bash
cd frontend
npm install
npm run build
cd ..
```

### 2. Deploy the EKS Stack

```bash
cd backend

# Activate Python virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate.bat

# Install dependencies (if not already done)
pip install -r requirements.txt

# Deploy the EKS stack
cdk deploy NovaSonicSolutionEKSBackendStack --app "python app_eks.py" --require-approval=never
```

**Note**: EKS cluster creation takes approximately 15-20 minutes.

### 3. Configure kubectl

After deployment, configure kubectl to access your cluster:

```bash
# Get the cluster name from CDK outputs
aws eks update-kubeconfig --name nova-sonic-eks-NovaSonicSolutionEKSBackendStack --region <your-region>
```

### 4. Verify Deployment

Check that all pods are running:

```bash
# Check pods in the websocket-app namespace
kubectl get pods -n websocket-app

# Check the service status
kubectl get service -n websocket-app
```

### 5. Get the Load Balancer URL

Wait for the Network Load Balancer to be provisioned (3-5 minutes after deployment):

```bash
# Get the NLB DNS name
kubectl get service websocket-service -n websocket-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### 6. Access the Application

The WebSocket endpoint will be available at:
```
ws://<NLB_DNS_NAME>/
```

## Monitoring and Troubleshooting

### View Pod Logs

```bash
# Get logs from all pods
kubectl logs -n websocket-app -l app=websocket-server

# Get logs from a specific pod
kubectl logs -n websocket-app <pod-name>

# Stream logs in real-time
kubectl logs -n websocket-app -l app=websocket-server -f
```

### Check Pod Status

```bash
# Describe pods for detailed information
kubectl describe pods -n websocket-app

# Get pod events
kubectl get events -n websocket-app --sort-by='.lastTimestamp'
```

### Scale the Deployment

Manual scaling (HPA will automatically adjust based on load):

```bash
kubectl scale deployment websocket-server -n websocket-app --replicas=5
```

### View HPA Status

```bash
kubectl get hpa -n websocket-app
kubectl describe hpa websocket-hpa -n websocket-app
```

## Cost Considerations

### EKS Fargate Pricing
- **EKS Control Plane**: $0.10 per hour
- **Fargate Pods**: Charged per vCPU and memory per second
  - vCPU: $0.04048 per vCPU per hour
  - Memory: $0.004445 per GB per hour

### Comparison with ECS Fargate
- EKS adds the control plane cost ($72/month)
- Pod pricing is similar to ECS task pricing
- EKS is more cost-effective when running multiple applications

## Customization

### Modify Resource Limits

Edit the deployment in `eks_fargate_constructs.py`:

```python
"resources": {
    "requests": {
        "cpu": "0.25",      # Minimum CPU (0.25 vCPU)
        "memory": "512Mi",  # Minimum memory
    },
    "limits": {
        "cpu": "0.5",       # Maximum CPU
        "memory": "1Gi",    # Maximum memory
    },
}
```

### Adjust Autoscaling

Modify HPA settings in `eks_fargate_constructs.py`:

```python
"minReplicas": 2,    # Minimum number of pods
"maxReplicas": 10,   # Maximum number of pods
"metrics": [
    {
        "type": "Resource",
        "resource": {
            "name": "cpu",
            "target": {
                "type": "Utilization",
                "averageUtilization": 70,  # Scale at 70% CPU
            },
        },
    },
]
```

### Add Custom Environment Variables

Add to the ConfigMap in `eks_fargate_constructs.py`:

```python
"data": {
    "COGNITO_USER_POOL_ID": cognito_user_pool_id,
    "AWS_REGION": Stack.of(self).region,
    "YOUR_CUSTOM_VAR": "value",
    # Add more as needed
}
```

## Clean Up

To avoid charges, delete the stack when no longer needed:

```bash
# Delete the EKS stack
cdk destroy NovaSonicSolutionEKSBackendStack --app "python app_eks.py"

# Note: This will delete the EKS cluster and all associated resources
```

## Troubleshooting Common Issues

### Pods Not Starting
- Check pod events: `kubectl describe pod <pod-name> -n websocket-app`
- Verify Fargate profile matches pod labels
- Check IAM permissions for the service account

### Load Balancer Not Created
- Verify AWS Load Balancer Controller is running: `kubectl get pods -n kube-system | grep aws-load`
- Check controller logs: `kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller`

### Connection Issues
- Ensure security groups allow traffic on port 80
- Verify NLB target health: Check in AWS Console under EC2 > Target Groups
- Check pod readiness: `kubectl get pods -n websocket-app`

### High Costs
- Review HPA metrics to optimize scaling thresholds
- Consider using Fargate Spot for non-critical workloads (when available)
- Monitor pod resource usage: `kubectl top pods -n websocket-app`

## Advantages of EKS Deployment

1. **Kubernetes Ecosystem**: Access to vast Kubernetes tooling and patterns
2. **Portability**: Easier to migrate to other Kubernetes platforms
3. **Advanced Networking**: Support for service mesh, network policies
4. **GitOps Ready**: Compatible with ArgoCD, Flux, etc.
5. **Multi-tenancy**: Better isolation for multiple applications
6. **Observability**: Rich ecosystem of monitoring tools (Prometheus, Grafana)

## When to Choose EKS over ECS

- **Multiple Applications**: When running multiple microservices
- **Kubernetes Experience**: Team has Kubernetes expertise
- **Portability Requirements**: Need to avoid vendor lock-in
- **Complex Orchestration**: Advanced deployment patterns needed
- **Ecosystem Integration**: Using Kubernetes-native tools

## Additional Resources

- [Amazon EKS Documentation](https://docs.aws.amazon.com/eks/)
- [EKS with Fargate](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [IRSA Documentation](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
