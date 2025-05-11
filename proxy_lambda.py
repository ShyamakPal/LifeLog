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
    API Gateway proxy Lambda handler that routes requests to the chat processor Lambda.
    Enhanced with detailed logging for easier debugging.
    """
    # Log the incoming event with a timestamp
    request_id = context.aws_request_id
    logger.info(f"Request {request_id} started at {datetime.now().isoformat()}")
    
    # Log a safe version of the event (without potentially large body contents)
    safe_event = {k: v for k, v in event.items() if k != 'body'}
    if 'body' in event:
        safe_event['body'] = '*** body content present but not logged ***'
    logger.info(f"Incoming event structure: {json.dumps(safe_event)}")
    
    try:
        # Log environment variables (be careful not to log secrets)
        processor_lambda_name = os.environ.get('PROCESSOR_LAMBDA_NAME')
        logger.info(f"Environment variables: PROCESSOR_LAMBDA_NAME={processor_lambda_name or 'NOT_SET'}")
        
        # Log if the processor Lambda name is missing
        if not processor_lambda_name:
            error_msg = "PROCESSOR_LAMBDA_NAME environment variable not set"
            logger.error(error_msg)
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'  # For CORS support
                },
                'body': json.dumps({
                    'error': error_msg
                })
            }
        
        # Initialize Lambda client
        logger.info(f"Initializing Lambda client to invoke {processor_lambda_name}")
        lambda_client = boto3.client('lambda')
        
        # Extract request body
        body = None
        if 'body' in event:
            logger.info("Found 'body' in event")
            body = event['body']
            
            # Handle string body from API Gateway
            if isinstance(body, str):
                try:
                    logger.info("Parsing string body as JSON")
                    body = json.loads(body)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse body as JSON: {str(e)}")
                    # Continue with string body
            
            logger.info(f"Body content type: {type(body).__name__}")
            # Log a summary of the body content
            if isinstance(body, dict):
                keys = list(body.keys())
                logger.info(f"Body contains keys: {keys}")
                if 'message' in body:
                    msg = body['message']
                    logger.info(f"User message (truncated): {msg[:50]}..." if len(msg) > 50 else f"User message: {msg}")
                if 'logs' in body:
                    logger.info(f"Body contains {len(body['logs'])} logs")
        else:
            logger.warning("No 'body' found in event")
        
        # IMPORTANT FIX: Pass the body directly without nesting it
        # This ensures the processor lambda receives the JSON object directly 
        # as its event, not nested inside a 'body' key
        payload = body
            
        # Include important headers and request context if needed in a way
        # that doesn't interfere with the main payload
        if payload and isinstance(payload, dict):
            # Only add these if they don't conflict with existing keys
            if 'headers' not in payload and 'headers' in event:
                payload['_request_headers'] = event['headers']
            
            if 'requestContext' not in payload and 'requestContext' in event:
                payload['_request_context'] = event['requestContext']
        
        logger.info(f"Invoking Lambda function: {processor_lambda_name}")
        
        # Invoke the chat processor Lambda
        try:
            response = lambda_client.invoke(
                FunctionName=processor_lambda_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Log the response metadata
            logger.info(f"Lambda invoke response metadata: {response['ResponseMetadata']}")
            
            # Check for function errors
            if 'FunctionError' in response:
                logger.error(f"Function error: {response.get('FunctionError')}")
                error_payload = json.loads(response['Payload'].read().decode())
                logger.error(f"Error payload: {json.dumps(error_payload)}")
                
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Error in processor lambda',
                        'details': error_payload
                    })
                }
            
            # Parse the response payload
            response_payload = json.loads(response['Payload'].read().decode())
            
            # Log a summary of the response
            if isinstance(response_payload, dict):
                status = response_payload.get('statusCode', 'unknown')
                logger.info(f"Processor Lambda response status: {status}")
                
                # Log body structure if present
                if 'body' in response_payload:
                    try:
                        body_content = json.loads(response_payload['body']) if isinstance(response_payload['body'], str) else response_payload['body']
                        logger.info(f"Response body keys: {list(body_content.keys())}")
                    except:
                        logger.info("Could not parse response body as JSON")
            
            # Return the response from the processor Lambda
            return response_payload
            
        except boto3.exceptions.ClientError as e:
            error_msg = f"Error invoking Lambda: {str(e)}"
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
        logger.info(f"Request {request_id} completed at {datetime.now().isoformat()}")