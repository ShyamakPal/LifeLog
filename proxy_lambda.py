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
    logger.info(f"Incoming event: {json.dumps(event)}")
    
    try:
        # Log environment variables (be careful not to log secrets)
        logger.info(f"Environment variables: PROCESSOR_LAMBDA_NAME={os.environ.get('PROCESSOR_LAMBDA_NAME', 'NOT_SET')}")
        
        # Get the Lambda function name from environment variable
        processor_lambda_name = os.environ.get('PROCESSOR_LAMBDA_NAME')
        
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
            # Log body content safely (truncate if too long)
            body_str = str(body)
            if len(body_str) > 1000:
                logger.info(f"Body (truncated): {body_str[:1000]}...")
            else:
                logger.info(f"Body: {body_str}")
        else:
            logger.warning("No 'body' found in event")
            
        # Prepare the payload for the processor Lambda
        payload = {
            'body': body,
            'headers': event.get('headers', {}),
            'requestContext': event.get('requestContext', {})
        }
        
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
            
            # Parse the response payload
            response_payload = json.loads(response['Payload'].read().decode())
            logger.info(f"Processor Lambda response: {json.dumps(response_payload)}")
            
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