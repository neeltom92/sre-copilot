# SRE Copilot Helm Chart

Deploy SRE Copilot to Kubernetes using Helm.

## Prerequisites

- Kubernetes 1.20+
- Helm 3.0+
- kubectl configured with cluster access

## Quick Deploy

### 1. Create Kubernetes Secret

First, create a secret with your API keys:

```bash
kubectl create namespace sre-copilot

kubectl create secret generic sre-copilot-secrets \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-your-key-here \
  --from-literal=DATADOG_API_KEY=your-datadog-key \
  --from-literal=DATADOG_APP_KEY=your-datadog-app-key \
  --from-literal=PAGERDUTY_API_KEY=your-pagerduty-key \
  -n sre-copilot
```

**Minimum required:** Only `ANTHROPIC_API_KEY` is required. Other keys are optional.

### 2. Install the Helm Chart

```bash
# From the chart directory
helm install sre-copilot . -n sre-copilot

# Or from the repository root
helm install sre-copilot deploy/chart/ -n sre-copilot
```

### 3. Verify Deployment

```bash
# Check pods
kubectl get pods -n sre-copilot

# Check service
kubectl get svc -n sre-copilot

# View logs
kubectl logs -f deployment/sre-copilot -n sre-copilot
```

### 4. Access the Application

**Using port-forward (recommended for testing):**
```bash
kubectl port-forward svc/sre-copilot 8501:80 -n sre-copilot
```

Visit: **http://localhost:8501**

**Using Ingress (for production):**

Enable ingress in `values.yaml`:
```yaml
ingress:
  enabled: true
  hostname: sre-copilot.yourcompany.com
```

Then upgrade:
```bash
helm upgrade sre-copilot . -n sre-copilot
```

Visit: http://sre-copilot.yourcompany.com

## Configuration

### values.yaml Key Settings

#### Required Configuration

```yaml
application:
  image:
    repository: "ghcr.io/neeltom92/sre-copilot"
    tag: "latest"

  env:
    secrets:
      name: "sre-copilot-secrets"
      keys:
        - "ANTHROPIC_API_KEY"  # Required
```

#### Optional Integrations

```yaml
  env:
    secrets:
      keys:
        - "DATADOG_API_KEY"    # Optional - for APM
        - "DATADOG_APP_KEY"    # Optional - for APM
        - "PAGERDUTY_API_KEY"  # Optional - for incidents
```

#### Ingress Configuration

```yaml
ingress:
  enabled: true
  ingressClassName: nginx  # or alb, traefik, etc.
  hostname: sre-copilot.example.com
  tls: false  # Set to true for HTTPS
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
```

#### Resource Limits

```yaml
application:
  resources:
    requests:
      memory: "2Gi"
      cpu: "500m"
    limits:
      memory: "4Gi"
      cpu: "2000m"
```

#### Autoscaling

```yaml
hpa:
  enabled: true
  cpu: "50"  # Target CPU utilization %
  minReplicaCount: "1"
  maxReplicaCount: "4"
```

## Customization

### Override Values

Create a custom `my-values.yaml`:

```yaml
# my-values.yaml
ingress:
  hostname: sre-copilot.mycompany.com
  ingressClassName: alb
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip

application:
  resources:
    requests:
      memory: "4Gi"
      cpu: "1000m"
```

Deploy with custom values:
```bash
helm install sre-copilot . -f my-values.yaml -n sre-copilot
```

### Update Deployment

```bash
# Upgrade with new values
helm upgrade sre-copilot . -f my-values.yaml -n sre-copilot

# Or edit values directly
helm upgrade sre-copilot . --set ingress.hostname=new-host.example.com -n sre-copilot
```

## Kubernetes RBAC for Pod Logs

If using Kubernetes pod log features, the service account needs RBAC permissions:

Create `rbac.yaml`:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: sre-copilot-viewer
rules:
- apiGroups: [""]
  resources: ["namespaces", "pods", "pods/log"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: sre-copilot-viewer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: sre-copilot-viewer
subjects:
- kind: ServiceAccount
  name: sre-copilot
  namespace: sre-copilot
```

Apply:
```bash
kubectl apply -f rbac.yaml
```

## Troubleshooting

### Pods Not Starting

Check pod status:
```bash
kubectl describe pod -l app.kubernetes.io/name=sre-copilot -n sre-copilot
```

Common issues:
- Missing secret: Create `sre-copilot-secrets` with ANTHROPIC_API_KEY
- Image pull error: Check image repository and tag
- Resource limits: Increase memory/CPU in values.yaml

### Check Logs

```bash
kubectl logs -f deployment/sre-copilot -n sre-copilot
```

### Secret Not Found

```bash
# Verify secret exists
kubectl get secret sre-copilot-secrets -n sre-copilot

# Recreate if needed
kubectl delete secret sre-copilot-secrets -n sre-copilot
kubectl create secret generic sre-copilot-secrets \
  --from-literal=ANTHROPIC_API_KEY=your-key \
  -n sre-copilot
```

### Ingress Not Working

```bash
# Check ingress
kubectl get ingress -n sre-copilot
kubectl describe ingress sre-copilot -n sre-copilot

# Test with port-forward
kubectl port-forward svc/sre-copilot 8501:80 -n sre-copilot
```

## Uninstall

```bash
helm uninstall sre-copilot -n sre-copilot

# Clean up namespace
kubectl delete namespace sre-copilot
```

## Production Recommendations

1. **Enable TLS/HTTPS:**
   ```yaml
   ingress:
     tls: true
     annotations:
       cert-manager.io/cluster-issuer: letsencrypt-prod
   ```

2. **Use specific image tag (not latest):**
   ```yaml
   application:
     image:
       tag: "main-abc123"  # Use specific commit
   ```

3. **Set resource limits based on usage:**
   - Monitor actual usage first
   - Adjust requests/limits accordingly

4. **Enable monitoring:**
   - Add Prometheus annotations
   - Configure pod disruption budgets

5. **Configure RBAC:**
   - Apply the RBAC yaml above for K8s pod log access
   - Follow principle of least privilege

## Files in This Chart

```
deploy/chart/
├── Chart.yaml              # Chart metadata
├── values.yaml             # Default configuration values
├── README.md               # This file
└── templates/
    ├── _helpers.tpl        # Template helpers
    ├── namespace.yaml      # Namespace creation
    ├── deployment.yaml     # Application deployment
    ├── service.yaml        # Service
    ├── serviceaccount.yaml # Service account
    ├── ingress.yaml        # Ingress
    ├── hpa.yaml            # Horizontal Pod Autoscaler
    └── secret.yaml         # Secret template (commented)
```

## Support

For issues or questions:
- GitHub: https://github.com/neeltom92/sre-copilot/issues
- Documentation: See main README.md
