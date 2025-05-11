#!/bin/bash
set -e

# Configuration variables
STACK_NAME="lifelog-chatbot"
S3_BUCKET="lifelog-uci"
EC2_INSTANCE="bowlinux"
REGION=$(aws configure get region)
if [ -z "$REGION" ]; then
    REGION="us-west-1" # Default region if not configured
fi

echo "==============================================="
echo "Life Log AI Chatbot Setup"
echo "==============================================="
echo "This script will set up the AI chatbot components for your Life Log application."
echo "Region: $REGION"
echo "S3 Bucket: $S3_BUCKET"
echo "EC2 Instance: $EC2_INSTANCE"
echo "==============================================="

# Ask for Gemini API key
read -p "Enter your Google Gemini API key (press Enter to skip Gemini support): " GEMINI_API_KEY

# Create temporary directories
echo "Creating temporary directories..."
mkdir -p ./tmp/lambda_chat_processor
mkdir -p ./tmp/lambda_proxy

# Save Lambda function code to the temporary directories
echo "Preparing Lambda functions..."
cp lambda_function.py ./tmp/lambda_chat_processor/
cp proxy_lambda.py ./tmp/lambda_proxy/lambda_function.py

# Install Python dependencies for the Lambda functions
echo "Installing Python dependencies for Lambda functions..."
pip install google-generativeai -t ./tmp/lambda_chat_processor/

# Create ZIP files for Lambda functions
echo "Creating Lambda function packages..."
(cd ./tmp/lambda_chat_processor && zip -r ../../chat_processor.zip .)
(cd ./tmp/lambda_proxy && zip -r ../../proxy_lambda.zip .)

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file template.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        GeminiApiKey=$GEMINI_API_KEY \
        S3BucketName=$S3_BUCKET \
        ApiStageName=prod \
    --capabilities CAPABILITY_IAM

# Update Lambda functions with actual code
echo "Updating Lambda functions with actual code..."
aws lambda update-function-code \
    --function-name lifelog-chat-processor \
    --zip-file fileb://chat_processor.zip

aws lambda update-function-code \
    --function-name lifelog-api-proxy \
    --zip-file fileb://proxy_lambda.zip

# Get API Gateway URL
API_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
    --output text)

echo "API Gateway URL: $API_URL"

# Update HTML file with correct API endpoint
echo "Updating HTML file with API endpoint..."
sed -i "s|fetch('/api/chat'|fetch('$API_URL'|g" index.html

# Upload website files to S3
echo "Uploading website files to S3..."
aws s3 cp index.html s3://$S3_BUCKET/
aws s3 cp css/styles.css s3://$S3_BUCKET/css/

# Clean up temporary files
echo "Cleaning up temporary files..."
rm -rf ./tmp
rm -f chat_processor.zip proxy_lambda.zip

echo "==============================================="
echo "Setup Complete!"
echo "==============================================="
echo "The chatbot has been successfully deployed."
echo "Website URL: http://$S3_BUCKET.s3-website-$REGION.amazonaws.com"
echo "API Endpoint: $API_URL"
echo ""
echo "Next steps:"
echo "1. Visit your website URL to start using the chatbot"
echo "2. Add log entries and ask the chatbot questions about your logs"
echo "==============================================="