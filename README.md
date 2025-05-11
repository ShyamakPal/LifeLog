# LifeLog

LifeLog is a personal journaling web application that allows users to record daily logs and gain AI-powered insights about their habits, patterns, and behaviors based on their entries.

## Features

- **Daily Logging**: Simple interface to add and save daily journal entries
- **AI-Powered Insights**: Ask questions about your logs and get intelligent analysis
- **Log Management**: View, edit, export, and delete your log entries
- **Local Storage**: All logs are stored in your browser's local storage for privacy
- **Responsive Design**: Works on desktop and mobile devices


## Technologies Used

- **Frontend**:
  - HTML5
  - CSS3
  - JavaScript (ES6+)
  - Bootstrap (for responsive design elements)
  - LocalStorage API (for client-side data storage)

- **Backend**:
  - AWS Lambda (for serverless functions)
  - Amazon Bedrock (for AI capabilities)
  - API Gateway (for RESTful API endpoints)
  - S3 (for data storage)

## Setup Instructions

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/ShyamakPal/LifeLog.git
   cd LifeLog
   ```

2. Open the project in your code editor.

3. For local testing, you can use a local server. If you have Python installed:
   ```bash
   # For Python 3.x
   python -m http.server
   
   # For Python 2.x
   python -m SimpleHTTPServer
   ```
   
4. Open your browser and navigate to `http://localhost:8000`

### Backend Setup (Optional)

The application uses an AWS backend for AI functionality. To set up your own backend:

1. Create an AWS account if you don't have one
2. Set up an S3 bucket for log storage
3. Create a Lambda function to process chat requests
4. Configure API Gateway to connect to your Lambda function
5. Update the fetch URL in `index.html` to point to your own API Gateway endpoint

Detailed AWS setup instructions can be found in the [backend/README.md](backend/README.md) file.

## Project Structure

```
LifeLog/
├── index.html           # Main application file
├── styles.css           # Styling for the application
├── lambda_function.py   # Python code for the Lambda function
├── proxy_lambda.py      # Python code for the Lambda function
├── ec2_setup.sh         # File to setup the ec2
├── setup.sh             # Script that sets up certain features
├── template.yaml        # Defines reusable configuration elements
└── README.md            # This file, includes backend setup in at the bottom
```

## Team Members and Contributions

### - Shyamak Pal
### - Daniel Pulikkottil

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The [Amazon Bedrock](https://aws.amazon.com/bedrock/) team for AI capabilities
- All contributors who have helped with code, ideas, and feedback
---------------------------------------------------------------------------------------------------------------------------------------------
# LifeLog Backend Setup

This document provides detailed instructions for setting up the backend infrastructure for the LifeLog application using AWS services.

## Architecture Overview

The LifeLog backend uses the following AWS services:
- **Amazon S3**: Stores log data
- **AWS Lambda**: Processes requests and interacts with the AI model
- **Amazon Bedrock**: Provides AI capabilities for analyzing logs
- **Amazon API Gateway**: Creates RESTful API endpoints for the frontend to communicate with Lambda

## Prerequisites

1. An AWS account with administrative access
2. AWS CLI installed and configured on your local machine
3. Basic knowledge of AWS services

## Setup Instructions

### Step 1: Create an S3 Bucket

1. Go to the [S3 Console](https://console.aws.amazon.com/s3)
2. Click "Create bucket"
3. Name your bucket (e.g., "lifelog-uci-2" or a unique name of your choice)
4. Select your preferred region
5. Keep the default settings and click "Create bucket"
6. Note your bucket name for later use

### Step 2: Set Up the Lambda Function

1. Go to the [Lambda Console](https://console.aws.amazon.com/lambda)
2. Click "Create function"
3. Select "Author from scratch"
4. Name your function (e.g., "LifeLogChatFunction")
5. Select Python 3.9 or higher as the runtime
6. Create a new role with basic Lambda permissions
7. Click "Create function"

8. In the function code editor, replace the default code with the contents of the `lambda_function.py` file from this repository

9. Add required environment variables:
   - `BUCKET_NAME`: The name of your S3 bucket (created in Step 1)
   - `BEDROCK_MODEL_ID`: `anthropic.claude-v2` or your preferred Bedrock model

10. Update the Lambda function timeout (under "Configuration" > "General configuration"):
    - Set timeout to 30 seconds (or more if needed)

11. Add permissions to your Lambda function:
    - Go to "Configuration" > "Permissions"
    - Click on the execution role to go to the IAM console
    - Add the following policies:
      - `AmazonS3FullAccess` (or a more restricted policy for your specific bucket)
      - `AmazonBedrockFullAccess` (or a more restricted policy for Bedrock)

### Step 3: Configure Amazon Bedrock

1. Go to the [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Go to "Model access" in the left navigation
3. Request access to the Claude model (Anthropic Claude)
4. Wait for access approval (usually instant, but may take time)

### Step 4: Create API Gateway

1. Go to the [API Gateway Console](https://console.aws.amazon.com/apigateway)
2. Click "Create API"
3. Select "REST API" and click "Build"
4. Set the API name as "LifeLogAPI" and click "Create API"

5. Create a resource:
   - Click "Create Resource"
   - Resource name: "chat"
   - Enable CORS
   - Click "Create Resource"

6. Create a method:
   - Select the "/chat" resource
   - Click "Create Method"
   - Select "POST" from the dropdown
   - Click the checkmark

7. Configure the POST method:
   - Integration type: Lambda Function
   - Lambda Function: Select your region and enter the function name created in Step 2
   - Click "Save"
   - When prompted to add permissions, click "OK"

8. Deploy the API:
   - Click "Deploy API"
   - Deployment stage: [New Stage]
   - Stage name: "prod"
   - Click "Deploy"

9. Note your API endpoint URL:
   - It will be displayed as "Invoke URL" at the top of the stage editor
   - Your endpoint will be this URL followed by "/chat"

### Step 5: Update Frontend Configuration

1. Open the `index.html` file in the root directory of the project
2. Find the `sendChatMessage` function
3. Update the fetch URL to your API Gateway endpoint:
   ```javascript
   fetch('YOUR_API_GATEWAY_URL/chat', {
       // rest of the code
   })
   ```
4. Update the bucket parameter to match your bucket name:
   ```javascript
   body: JSON.stringify({
       message: message,
       logs: logs,
       model: selectedModel,
       bucket: "YOUR_BUCKET_NAME" // Update this value
   })
   ```

## Testing the Backend

To test that your backend is working properly:

1. Deploy the updated frontend
2. Open the application in a browser
3. Add a few log entries
4. Try sending a message to the chatbot like "What have I been logging about?"
5. You should get a response from the AI based on your logs

## Troubleshooting

### Common Issues:

1. **CORS Errors**: If you see CORS errors in the browser console:
   - Go back to API Gateway
   - Select your API and go to the "/chat" resource
   - Click "Enable CORS" and deploy the API again

2. **Lambda Timeouts**: If requests take too long:
   - Increase the Lambda function timeout in the configuration settings
   - Consider optimizing the Lambda code

3. **Permissions Issues**: If you see access denied errors:
   - Check that your Lambda function has the correct permissions for S3 and Bedrock
   - Verify environment variables are set correctly

4. **Bedrock Model Access**: If you see errors related to model access:
   - Ensure you've been granted access to the Claude model in Bedrock
   - Check the model ID is correct in your Lambda environment variables

## Security Considerations

This setup is designed for educational purposes. For a production environment, consider:

1. Implementing proper authentication
2. Using more restrictive IAM policies
3. Setting up CloudWatch Logs for monitoring
4. Adding request validation in API Gateway
5. Implementing rate limiting to prevent abuse

## Cost Management

Be aware that using AWS services incurs costs:
- S3 storage charges for stored logs
- Lambda charges for function invocations
- API Gateway charges for API calls
- Bedrock charges for model usage (this can be substantial)

For development and testing, usage should remain within the AWS Free Tier limits for most services, but monitor your usage regularly.
