# Customer Support Chatbot

A conversational AI customer support agent for DataForge AI, a SaaS platform for data analytics and machine learning. This implementation uses the DeepSeek API via OpenRouter to provide context-aware responses based on a comprehensive knowledge base.

![DEMO](demo.png)

## Features

- **Natural Language Understanding**: Interprets user questions about DataForge AI using DeepSeek's large language model
- **Knowledge Base Integration**: Provides accurate responses based on comprehensive product documentation
- **Context-Aware Conversations**: Maintains conversation history for more relevant follow-up responses
- **Fallback Mechanism**: Gracefully handles questions outside its knowledge domain
- **User Feedback Collection**: Thumbs up/down ratings to track response quality
- **Analytics Dashboard**: Track query types, satisfaction rates, and fallback frequency
- **Responsive Design**: Works seamlessly on both desktop and mobile devices

## Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Backend**: Python, Flask, SQLite
- **AI/LLM**: DeepSeek V3 via OpenRouter API
- **Deployment**: Docker, Docker Compose

## Prerequisites

- [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/)
- [OpenRouter API key](https://openrouter.ai/) for accessing DeepSeek V3
- Or simply use OpenAI/DeepSeek API key

## Quick Start

1. **Clone the repository**:
git clone https://github.com/aravinditte/Customer-Support-Chatbot.git
cd Customer-Support-Chatbot


2. **Configure environment variables**:
   Create a `.env` file in the root directory:
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   SECRET_KEY=your_random_secret_key_here


3. **Start the application**:
   docker-compose up

4. **Access the chatbot**:
   Open your browser and navigate to `http://localhost`

## Sample Questions to Ask the Chatbot

   Here are some example questions you can ask the DataForge AI support chatbot:

### About the Product
- "What is DataForge AI?"
- "What features does DataForge AI offer?"
- "How does DataForge AI's AI Model Builder work?"
- "What kind of dashboards can I create with DataForge AI?"
- "How does DataForge AI handle data preparation?"

### Pricing and Plans
- "How much does DataForge AI cost?"
- "What are the different pricing tiers?"
- "What's included in the Enterprise plan?"
- "Is there a free trial available?"
- "Do you offer discounts for annual billing?"

### Technical Questions
- "How many data sources can I connect to?"
- "Does DataForge AI support real-time data?"
- "How secure is my data on DataForge AI?"
- "Can I export data from DataForge AI?"
- "Does DataForge AI have an API?"

### Use Cases
- "How can DataForge AI help with marketing analytics?"
- "What are some sales use cases for DataForge AI?"
- "Can DataForge AI be used for financial forecasting?"
- "How do operations teams use DataForge AI?"
- "What industries use DataForge AI?"

### Getting Started
- "How do I get started with DataForge AI?"
- "How do I connect my data sources?"
- "How can I create my first dashboard?"
- "How do I build an AI model in DataForge AI?"
- "How long does it take to implement DataForge AI?"

### Support and Documentation
- "How can I get support for DataForge AI?"
- "Do you offer training for DataForge AI?"
- "Where can I find documentation?"
- "Is there a community forum for DataForge AI users?"
- "Do you offer implementation services?"

## Configuration Options

### OpenRouter API Configuration

The application uses OpenRouter to access the DeepSeek V3 language model. You can modify the model settings in `app.py`:

   completion = client.chat.completions.create(
   extra_headers={
   "HTTP-Referer": "https://dataforge.ai",
   "X-Title": "DataForge AI Support"
   },
   model="deepseek/deepseek-v3-base:free",
   messages=messages,
   max_tokens=500,
   temperature=0.7
   )

### Knowledge Base Customization

Add or modify Markdown files in the `backend/knowledge_base/` directory to expand the chatbot's knowledge. The system automatically loads all `.md` files in this directory.

## Implementation Details

### Conversation Context Management

The application uses Flask sessions to maintain conversation history between the user and the chatbot. This allows for more natural and contextual interactions:

Add query to conversation history
session['conversation'].append({"type": "user", "content": query})

Limit conversation history to last 10 messages
if len(session['conversation']) > 10:
session['conversation'] = session['conversation'][-10:]


### Analytics Tracking

User interactions and feedback are stored in an SQLite database for performance analysis:

   Track analytics
      conn = get_db_connection()
      cursor = conn.cursor()
      cursor.execute(
      "INSERT INTO chat_analytics (session_id, query, response, category, is_fallback) VALUES (?, ?, ?, ?, ?)",
      (session_id, query, response, category, is_fallback)
      )

## Alternative LLM Providers

This implementation uses DeepSeek V3 via OpenRouter, but you can easily switch to other LLM providers:

- **OpenAI**: Update the base URL and API key to use OpenAI's API directly
- **DeepSeek Direct**: Use DeepSeek's API directly if you have access
- **Other Providers**: The code can be adapted to work with any LLM provider that offers a compatible API

## Troubleshooting

### API Connection Issues

If you encounter problems connecting to the OpenRouter API:

1. Verify your API key is correct in the `.env` file
2. Check if you've reached your API usage limits
3. Look for detailed error messages in the backend logs

### Missing Knowledge Base Content

If the chatbot fails to answer questions about DataForge AI:

1. Ensure the `knowledge_base` directory contains Markdown files
2. Verify the content of these files is relevant to the questions being asked
3. Add more detailed documentation files covering specific topics


This project was created as a demonstration of AI-powered customer support for a fictional SaaS product.