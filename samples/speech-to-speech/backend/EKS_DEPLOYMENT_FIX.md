# EKS Deployment Fix - AWS Load Balancer Controller Dependency

## Problem Summary
The deployment was failing with the error:
```
failed calling webhook "mservice.elbv2.k8s.aws": 
Post "https://aws-load-balancer-webhook-service.kube-system.svc:443/mutate-v1-service?timeout=10s": 
no endpoints available for service "aws-load-balancer-webhook-service"
```

## Root Cause
The WebSocket Service was trying to create a Network Load Balancer (NLB) before the AWS Load Balancer Controller was fully operational. This created a race condition where:

1. The Service manifest includes AWS-specific annotations (`service.beta.kubernetes.io/aws-load-balancer-type: nlb`)
2. These annotations trigger a webhook from the AWS Load Balancer Controller
3. But the controller's pods weren't ready yet, causing the webhook call to fail

## The Fix
Added explicit dependencies in `eks_fargate_constructs.py` to ensure proper deployment order:

```python
# Line 438-440 (after Load Balancer Controller Helm chart creation)
# CRITICAL FIX: Add dependency so Service waits for AWS Load Balancer Controller
# This prevents the "no endpoints available for service" error
service.node.add_dependency(lb_controller_chart)
hpa.node.add_dependency(lb_controller_chart)  # HPA should also wait
```

## Why This Works
The dependency chain is now:
1. **AWS Load Balancer Controller Helm Chart** is deployed first
2. Controller pods start and webhook service becomes available
3. **WebSocket Service** is created (which needs the controller's webhook)
4. Service successfully creates the NLB using the controller

## Deployment Order (Fixed)
```
EKS Cluster Creation
    ↓
Fargate Profiles & Namespaces
    ↓
Service Accounts & IAM Roles
    ↓
AWS Load Balancer Controller (Helm)
    ↓
Controller Pods Ready ✓
    ↓
WebSocket Deployment
    ↓
WebSocket Service (with NLB annotations) ← Now waits for controller!
    ↓
HorizontalPodAutoscaler
```

## Key Learnings
1. **Helm Chart Deployment != Pods Ready**: The CDK deployment of a Helm chart only ensures the chart is installed, not that the pods are running
2. **Webhook Dependencies**: Services using AWS Load Balancer Controller annotations require the controller's webhook to be available
3. **Explicit Dependencies**: Always add explicit dependencies when one Kubernetes resource requires another to be operational

## Testing the Fix
After deployment:
1. Check if the AWS Load Balancer Controller is running:
   ```bash
   kubectl get pods -n kube-system | grep aws-load-balancer-controller
   ```

2. Verify the webhook service has endpoints:
   ```bash
   kubectl get endpoints -n kube-system aws-load-balancer-webhook-service
   ```

3. Check if the NLB was created successfully:
   ```bash
   kubectl get service websocket-service -n websocket-app
   ```

## Prevention
For future EKS deployments with AWS Load Balancer Controller:
- Always add dependencies between the controller and any Services using AWS annotations
- Consider using a two-phase deployment approach for complex setups
- Test dependency chains in development environments first
