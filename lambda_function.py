import json
import boto3
import os
import google.generativeai as genai
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS Bedrock client
bedrock_runtime = boto3.client('bedrock-runtime')

# Initialize Google Gemini API (will be configured from environment variables)
try:
    genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
except Exception as e:
    logger.error(f"Error configuring Gemini API: {str(e)}")

def lambda_handler(event, context):
    """
    Main Lambda handler that processes requests from the chatbot.
    """
    try:
        # Parse the request body
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event
            
        user_message = body.get('message', '')
        logs = body.get('logs', [])
        model = body.get('model', 'bedrock')  # Default to Bedrock if not specified
        
        # Process logs to create context for the AI
        log_context = process_logs(logs)
        
        # Get response from selected AI model
        if model == 'gemini':
            response_text = query_gemini(user_message, log_context)
        else:  # Default to Bedrock
            response_text = query_bedrock(user_message, log_context)
        
        # Return the AI response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'  # For CORS support
            },
            'body': json.dumps({
                'response': response_text
            })
        }
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'  # For CORS support
            },
            'body': json.dumps({
                'error': f"An error occurred: {str(e)}"
            })
        }

def process_logs(logs):
    """
    Process and analyze the logs to create context for the AI.
    """
    if not logs:
        return "No log entries found."
    
    # Extract text and dates from logs
    processed_logs = []
    for log in logs:
        try:
            # Convert ISO string to datetime object
            log_date = datetime.fromisoformat(log['date'].replace('Z', '+00:00'))
            formatted_date = log_date.strftime('%Y-%m-%d %H:%M:%S')
            
            processed_logs.append({
                'date': formatted_date,
                'text': log['text']
            })
        except Exception as e:
            logger.warning(f"Error processing log entry: {str(e)}")
    
    # Create a string representation of the logs
    log_text = "\n\n".join([f"Date: {log['date']}\nEntry: {log['text']}" for log in processed_logs])
    
    return log_text

def query_bedrock(user_message, log_context):
    """
    Query Amazon Bedrock for AI response using Claude model.
    """
    try:
        # Prepare prompt for Claude
        prompt = f"""
        You are a helpful Life Log Assistant that analyzes personal log entries to provide insights, summaries, and answer questions.
        
        Here are the user's log entries:
        
        {log_context}
        
        Based on these log entries, please answer the following question or request:
        
        {user_message}
        
        Please be specific and reference the log data in your answer. If the logs don't contain enough information to answer confidently, 
        mention that in your response.
        """
        
        # Update to use Claude 3.7 Sonnet
        model_params = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.5,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        # Try to use Claude 3.7 Sonnet first
        try:
            response = bedrock_runtime.invoke_model(
                modelId="anthropic.claude-3-7-sonnet-20250219-v1:0",
                body=json.dumps(model_params)
            )
        except Exception as model_error:
            logger.warning(f"Failed to use Claude 3.7 Sonnet: {str(model_error)}. Trying Claude 3.5 Haiku...")
            
            # Fallback to Claude 3.5 Haiku
            try:
                response = bedrock_runtime.invoke_model(
                    modelId="anthropic.claude-3-5-haiku-20240307-v1:0",
                    body=json.dumps(model_params)
                )
            except Exception as haiku_error:
                logger.warning(f"Failed to use Claude 3.5 Haiku: {str(haiku_error)}. Trying Claude 3 Sonnet...")
                
                # Ultimate fallback to Claude 3 Sonnet
                response = bedrock_runtime.invoke_model(
                    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                    body=json.dumps(model_params)
                )
        
        # Parse response
        response_body = json.loads(response.get('body').read())
        return response_body.get('content')[0].get('text')
        
    except Exception as e:
        logger.error(f"Error querying Bedrock: {str(e)}")
        return f"I'm sorry, I encountered an error when processing your request. The AI service might be temporarily unavailable. Please try again in a few moments."

def query_gemini(user_message, log_context):
    """
    Query Google Gemini for AI response.
    """
    try:
        # Create a prompt for Gemini
        prompt = f"""
        You are a helpful Life Log Assistant that analyzes personal log entries to provide insights, summaries, and answer questions.
        
        Here are the user's log entries:
        
        {log_context}
        
        Based on these log entries, please answer the following question or request:
        
        {user_message}
        
        Please be specific and reference the log data in your answer. If the logs don't contain enough information to answer confidently, 
        mention that in your response.
        """
        
        # Configure Gemini model
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Generate response
        response = model.generate_content(prompt)
        
        return response.text
        
    except Exception as e:
        logger.error(f"Error querying Gemini: {str(e)}")
        return f"I'm sorry, I encountered an error when processing your request: {str(e)}"