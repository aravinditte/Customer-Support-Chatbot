# CloudFlow Analytics API Documentation

This documentation covers the CloudFlow Analytics REST API, available on the Professional and Enterprise plans.

## Authentication

All API requests require authentication using an API key.

GET /api/v1/dashboards
Authorization: Bearer YOUR_API_KEY

text

You can generate and manage API keys in your account settings.

## Rate Limits

- Starter: Not available
- Professional: 100 requests per minute
- Enterprise: 1000 requests per minute

## Core Endpoints

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

### Data Sources

GET /api/v1/datasources

text
Returns a list of all data sources you have access to.

GET /api/v1/datasources/{id}

text
Returns details for a specific data source.

POST /api/v1/datasources

text
Creates a new data source connection.

### Query Data

POST /api/v1/query

text
Execute a query against a data source.

Request body:
{
"datasource_id": "ds-123456",
"query": "SELECT * FROM sales WHERE date >= '2023-01-01'",
"limit": 1000
}

text

## Webhook Integration

Set up webhooks to receive notifications when:
- Dashboards are updated
- Scheduled queries complete
- Anomalies are detected

Configure webhooks in your account settings.