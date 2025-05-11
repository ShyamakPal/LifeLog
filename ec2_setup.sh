#!/bin/bash
set -e

# Configuration variables
EC2_INSTANCE_NAME="bowlinux"
S3_BUCKET="lifelog-uci"
REGION=$(aws configure get region)
if [ -z "$REGION" ]; then
    REGION="us-west-1" # Default region if not configured
fi

echo "==============================================="
echo "EC2 Instance Configuration for Life Log Chatbot"
echo "==============================================="
echo "This script will configure your EC2 instance to serve the Life Log website and proxy API requests."
echo "Region: $REGION"
echo "S3 Bucket: $S3_BUCKET"
echo "EC2 Instance: $EC2_INSTANCE_NAME"
echo "==============================================="

# Get API Gateway URL from CloudFormation stack
API_URL=$(aws cloudformation describe-stacks \
    --stack-name lifelog-chatbot \
    --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
    --output text)

echo "API Gateway URL: $API_URL"

# Create nginx configuration file
cat > nginx_config.conf << EOF
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://$S3_BUCKET.s3-website-$REGION.amazonaws.com/;
        proxy_set_header Host $S3_BUCKET.s3-website-$REGION.amazonaws.com;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /api/chat {
        proxy_pass $API_URL;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Copy nginx configuration to EC2 instance
echo "Copying nginx configuration to EC2 instance..."
aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=$EC2_INSTANCE_NAME" \
    --query "Reservations[0].Instances[0].PublicDnsName" \
    --output text > ec2_dns.txt

EC2_DNS=$(cat ec2_dns.txt)
if [ -z "$EC2_DNS" ]; then
    echo "Error: Could not find EC2 instance with name $EC2_INSTANCE_NAME"
    exit 1
fi

echo "EC2 DNS: $EC2_DNS"

# Get SSH key name from EC2 instance
SSH_KEY_NAME=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=$EC2_INSTANCE_NAME" \
    --query "Reservations[0].Instances[0].KeyName" \
    --output text)

echo "SSH Key Name: $SSH_KEY_NAME"
echo "Please enter the path to your SSH key file for the EC2 instance:"
read SSH_KEY_PATH

# Copy files to EC2 instance
echo "Copying configuration files to EC2 instance..."
scp -i "$SSH_KEY_PATH" nginx_config.conf ec2-user@$EC2_DNS:/tmp/

# Configure nginx on EC2 instance
echo "Configuring nginx on EC2 instance..."
ssh -i "$SSH_KEY_PATH" ec2-user@$EC2_DNS << 'ENDSSH'
    # Install nginx if not already installed
    if ! command -v nginx &> /dev/null; then
        echo "Installing nginx..."
        sudo amazon-linux-extras install -y nginx1
    fi
    
    # Copy nginx configuration
    sudo cp /tmp/nginx_config.conf /etc/nginx/conf.d/lifelog.conf
    
    # Restart nginx
    sudo systemctl restart nginx
    
    # Enable nginx to start on boot
    sudo systemctl enable nginx
    
    echo "Nginx configuration complete."
ENDSSH

# Clean up
rm -f nginx_config.conf ec2_dns.txt

echo "==============================================="
echo "EC2 Configuration Complete!"
echo "==============================================="
echo "Your EC2 instance has been configured to serve the Life Log website and proxy API requests."
echo "You can access the website at: http://$EC2_DNS"
echo "==============================================="