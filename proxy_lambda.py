import json
import boto3
import os

def lambda_handler(event, context):
    """
    API Gateway proxy Lambda handler that routes requests to the chat processor Lambda.
    """
    try:
        # Get the Lambda function name from environment variable
        processor_lambda_name = os.environ.get('PROCESSOR_LAMBDA_NAME')
        
        if not processor_lambda_name:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'  # For CORS support
                },
                'body': json.dumps({
                    'error': 'PROCESSOR_LAMBDA_NAME environment variable not set'
                })
            }
        
        # Initialize Lambda client
        lambda_client = boto3.client('lambda')
        
        # Extract request body
        if 'body' in event:
            body = event['body']
            if isinstance(body, str):
                body = json.loads(body)
        else:
            body = {}
        
        # Invoke the processor Lambda function
        response = lambda_client.invoke(
            FunctionName=processor_lambda_name,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'message': body.get('message', ''),
                'logs': body.get('logs', []),
                'model': body.get('model', 'bedrock')
            })
        )
        
        # Parse the response from the processor Lambda
        response_payload = json.loads(response['Payload'].read().decode('utf-8'))
        
        # If there's a body in the response, it's likely a string that needs to be parsed
        if 'body' in response_payload and isinstance(response_payload['body'], str):
            response_payload['body'] = json.loads(response_payload['body'])
        
        # Return the response
        return {
            'statusCode': response_payload.get('statusCode', 200),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'  # For CORS support
            },
            'body': json.dumps(response_payload.get('body', {}))
        }
        
    except Exception as e:
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

def handle_options_request():
    """
    Handle OPTIONS requests for CORS preflight.
    """
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
            'Access-Control-Max-Age': '86400'  # 24 hours
        },
        'body': '{}'
    }