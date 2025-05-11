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
        
        # Extract body from the event
        body = event.get('body')
        
        if not body:
            error_msg = "No body found in the request"
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
        
        # Log the body type and content safely
        logger.info(f"Body type: {type(body).__name__}")
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
        
        # Extract and validate user message
        user_message = body.get('message')
        if not user_message:
            error_msg = "No 'message' field found in request body"
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
        
        # Prepare request payload for Claude
        try:
            request_payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_message
                            }
                        ]
                    }
                ]
            }
            
            logger.info(f"Request payload prepared for model {model_id}")
            logger.info(f"Payload: {json.dumps(request_payload)}")
            
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
            
            # Return success response
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': ai_message
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