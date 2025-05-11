import json
import os
import boto3
import logging
import traceback
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Set to DEBUG for even more detailed logs

def lambda_handler(event, context):
    """
    Chat processor Lambda handler that interacts with Amazon Bedrock.
    Enhanced with comprehensive logging for better debugging.
    """
    # Log the incoming event with a timestamp
    request_id = context.aws_request_id
    logger.info(f"Chat processor request {request_id} started at {datetime.now().isoformat()}")
    logger.info(f"Incoming event structure: {json.dumps({k: type(v).__name__ for k, v in event.items()})}")
    
    try:
        # Log environment variables (excluding secrets)
        model_id = os.environ.get('MODEL_ID')
        logger.info(f"Environment variables: MODEL_ID={model_id or 'NOT_SET'}")
        
        # FIXED: Check if event is already the correct format
        # The event should already contain message, logs, etc. directly
        # if coming from the fixed proxy
        
        # Extract fields directly from the event
        user_message = event.get('message')
        logs = event.get('logs', [])
        model = event.get('model')
        bucket = event.get('bucket')
        
        # Log received data
        logger.info(f"Direct message field: {user_message is not None}")
        logger.info(f"Direct logs field: {len(logs)} entries")
        logger.info(f"Model: {model}")
        logger.info(f"Bucket: {bucket}")
        
        # If direct fields are not found, try to extract from body as fallback
        # This maintains backward compatibility with the old structure
        if user_message is None:
            body = event.get('body')
            
            if not body:
                error_msg = "No message or body found in the request"
                logger.error(error_msg)
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': error_msg
                    })
                }
            
            # Parse body if it's a string
            if isinstance(body, str):
                try:
                    logger.info("Parsing string body as JSON")
                    body = json.loads(body)
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse body as JSON: {str(e)}"
                    logger.error(error_msg)
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'error': error_msg
                        })
                    }
            
            # Extract from body
            user_message = body.get('message')
            logs = body.get('logs', [])
            model = body.get('model')
            bucket = body.get('bucket')
        
        # Validate user message
        if not user_message:
            error_msg = "No 'message' field found in request"
            logger.error(error_msg)
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': error_msg
                })
            }
        
        logger.info(f"User message: {user_message[:100]}..." if len(user_message) > 100 else f"User message: {user_message}")
        logger.info(f"Received {len(logs)} log entries")
        
        # Initialize Bedrock Runtime client
        try:
            logger.info("Initializing Bedrock Runtime client")
            bedrock_runtime = boto3.client('bedrock-runtime')
            logger.info("Bedrock Runtime client initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize Bedrock Runtime client: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Error details: {traceback.format_exc()}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': error_msg
                })
            }
        
        # Get model ID from environment or use default
        if not model_id:
            model_id = "anthropic.claude-3-sonnet-20240229-v1:0"  # Default model
            logger.warning(f"MODEL_ID not set, using default: {model_id}")
        
        # Prepare system message with instructions on how to use the logs
        system_message = """
        You are a helpful AI assistant for a personal life logging application. 
        Users will share their daily logs with you and may ask questions about patterns, insights, or summaries.
        Be supportive, thoughtful, and provide psychological insights when appropriate.
        
        When analyzing logs, look for:
        - Patterns in mood, activities, or behaviors
        - Potential areas for improvement or growth
        - Positive trends to encourage
        - Connections between different aspects of the user's life
        
        Keep responses concise, supportive, and focused on helping the user gain insight from their logs.
        """
        
        # Prepare a better prompt that includes context from the logs
        user_prompt = user_message
        
        # Include some context from the logs if available
        if logs:
            # Add up to 5 most recent logs as context
            recent_logs = logs[:5]
            logs_context = "\n\nHere are my most recent logs:\n"
            
            for idx, log in enumerate(recent_logs):
                date_str = log.get('date', 'Unknown date')
                try:
                    # Format the date if it's ISO format
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    formatted_date = date_obj.strftime('%Y-%m-%d %H:%M')
                except:
                    formatted_date = date_str
                
                log_text = log.get('text', 'No content')
                logs_context += f"Log {idx+1} ({formatted_date}): {log_text}\n\n"
            
            user_prompt = f"{user_message}\n\n{logs_context}"
        
        # Prepare request payload for Claude
        try:
            request_payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            }
                        ]
                    }
                ]
            }
            
            logger.info(f"Request payload prepared for model {model_id}")
            
            # Invoke Bedrock model
            logger.info(f"Invoking Bedrock model: {model_id}")
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(request_payload)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read().decode())
            logger.info("Successfully received response from Bedrock")
            
            # Extract AI message from response
            ai_message = response_body['content'][0]['text']
            logger.info(f"AI response (first 100 chars): {ai_message[:100]}...")
            
            # Return success response with both 'message' and 'response' keys for backward compatibility
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': ai_message,
                    'response': ai_message  # Include both keys for compatibility
                })
            }
            
        except KeyError as e:
            error_msg = f"Missing key in response: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Response structure: {json.dumps(response_body) if 'response_body' in locals() else 'No response body'}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': error_msg
                })
            }
            
        except boto3.exceptions.ClientError as e:
            error_msg = f"Bedrock invoke error: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Error details: {traceback.format_exc()}")
            
            # Check if it's a model-specific error (helpful for debugging)
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
            if error_code == 'ModelTimeoutException':
                error_msg = "The model timed out. Please try again with a shorter message."
            elif error_code == 'ModelStreamErrorException':
                error_msg = "There was an error streaming the model response."
            elif error_code == 'ValidationException':
                error_msg = "Invalid request format to Bedrock."
            elif error_code == 'AccessDeniedException':
                error_msg = "No permission to access the Bedrock model."
            
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': error_msg
                })
            }
            
    except Exception as e:
        # Log detailed traceback for unexpected errors
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': error_msg
            })
        }
    finally:
        logger.info(f"Chat processor request {request_id} completed at {datetime.now().isoformat()}")