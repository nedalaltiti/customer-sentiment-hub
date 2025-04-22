# Customer Sentiment Hub Deployment Guide

## Docker Image

The application is containerized and follows best practices:
- Multi-stage build for smaller image size
- Non-root user for security
- AWS Secrets Manager integration

## AWS IAM Requirements

The container needs IAM permissions for:
- `secretsmanager:GetSecretValue` for the secret: `genai-gemini-vertex-prod-api`

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| AWS_REGION | AWS region for Secrets Manager | Yes | us-west-1 |
| AWS_SECRET_NAME | Name of the Gemini credentials secret | Yes | genai-gemini-vertex-prod-api |
| ENVIRONMENT | Deployment environment | yes | deployment |
| LOG_LEVEL | Logging verbosity | No | INFO |
| GEMINI_MODEL_NAME | Gemini model to use | No | gemini-2.0-flash-001 |
| GEMINI_TEMPERATURE | Model temperature parameter | No | 0 |
| GEMINI_MAX_OUTPUT_TOKENS | Max tokens in model response | No | 1024 |
| PROCESSING_BATCH_SIZE | Batch size for review processing | No | 5 |

## Kubernetes Deployment

1. Create the necessary namespace:

kubectl create namespace downstream-tasks

2. Create the Kubernetes service account with proper IAM role:

AWS EKS specific - use IAM roles for service accounts
eksctl create iamserviceaccount 
--name sentiment-hub-service-account 
--namespace downstream-tasks
--cluster your-cluster-name 
--attach-policy-arn arn:aws:iam::123456789012/SentimentHubSecretAccess 
--approve

3. Deploy the application:
## Monitoring and Scaling

kubectl apply -f k8s.yaml

- The application exposes a health check endpoint at `/health`
- CPU/memory metrics should be monitored for scaling decisions
- Consider setting up auto-scaling based on CPU utilization:

kubectl autoscale deployment customer-sentiment-hub 
--min=2 --max=10 --cpu-percent=70 -n downstream-tasks

## AI Performance Considerations

- First requests may be slower due to model initialization
- The Gemini API has rate limits - check with Shahd for QPS limits
- Monitor response times from the Gemini API endpoint

