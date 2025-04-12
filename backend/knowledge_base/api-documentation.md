 API Documentation

DataForge AI provides a comprehensive REST API that allows you to programmatically interact with the platform. This documentation covers the core endpoints and authentication methods.

## Authentication

All API requests require authentication using an API key.

GET /api/v1/datasets
Authorization: Bearer YOUR_API_KEY

text

You can generate and manage API keys in your account settings under the "API Access" section.

## Rate Limits

- Starter Plan: 100 requests per minute
- Professional Plan: 500 requests per minute
- Enterprise Plan: 2000 requests per minute (customizable)

## Core Endpoints

### Datasets

GET /api/v1/datasets

text
Returns a list of all datasets you have access to.

GET /api/v1/datasets/{id}

text
Returns details for a specific dataset.

POST /api/v1/datasets

text
Creates a new dataset.

### Models

GET /api/v1/models

text
Returns a list of all AI models you have access to.

GET /api/v1/models/{id}

text
Returns details for a specific model.

POST /api/v1/models/{id}/predict

text
Makes predictions using a deployed model.

### Dashboards

GET /api/v1/dashboards

text
Returns a list of all dashboards you have access to.

GET /api/v1/dashboards/{id}

text
Returns details for a specific dashboard.

POST /api/v1/dashboards

text
Creates a new dashboard.

### Data Query

POST /api/v1/query

text
Execute a query against a dataset.

Request body:
{
"dataset_id": "ds-123456",
"query": "SELECT * FROM sales WHERE date >= '2023-01-01'",
"limit": 1000
}

text

## Webhook Integration

Set up webhooks to receive notifications when:
- Models complete training
- Scheduled queries complete
- Anomalies are detected
- Reports are generated

Configure webhooks in your account settings under the "Integrations" section.

## SDKs and Client Libraries

We provide official client libraries for:
- Python
- JavaScript
- Java
- Ruby
- Go

Visit our GitHub repository at [github.com/dataforge-ai](https://github.com/dataforge-ai) to access these libraries.

## Example: Prediction API

import requests

api_key = "your_api_key"
model_id = "model-123456"
data = {"features": [1.2, 3.4, 5.6, 7.8]}

response = requests.post(
f"https://api.dataforge.ai/api/v1/models/{model_id}/predict",
headers={"Authorization": f"Bearer {api_key}"},
json=data
)

prediction = response.json()
print(prediction)

text

For detailed API documentation, including request and response schemas, visit our [API Reference](https://api.dataforge.ai/docs).