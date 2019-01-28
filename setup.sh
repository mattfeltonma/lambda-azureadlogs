#!/bin/bash

## User variables
##
REGION="us-east-1" #Region resources should be pushed
BUCKET="mybucket" #Add S3 Bucket here where logs will go

# Role or user that will have permission over new AWS KMS CMK
PRINCIPALARN="arn:aws:iam::<ACCNT>:<ROLE/USER>"

TENANTNAME="mytenant.com" #Enter Azure AD tenant name
CLIENTID="11111111-1111-1111-1111-111111111111" #Azure AD Client ID
CLIENTSECRET="XXXXXXXXXXXXXXX" #Azure AD Client Secret

## Permanent variables
##
SIGNIN="signinlogs.py"
AUDIT="auditlogs.py"

## Setup build directory
##
mkdir build
cd build
pip install adal --target .

## Create package
##
zip -r9 ../lambda-signin.zip .
cd ../
cp lambda-signin.zip lambda-audit.zip
zip -g lambda-signin.zip $SIGNIN
zip -g lambda-audit.zip $AUDIT

## Execute CloudFormation
##
aws cloudformation create-stack --stack-name azureadlogs \
--template-body file://cf-templates/cf-resources.yaml \
--capabilities CAPABILITY_NAMED_IAM \
--parameters ParameterKey=LogBucket,ParameterValue=$BUCKET \
ParameterKey=KMSAdminArn,ParameterValue=$PRINCIPALARN \
ParameterKey=TenantName,ParameterValue=$TENANTNAME --region $REGION

echo "Waiting for stack to complete.."
aws cloudformation wait stack-create-complete --stack-name azureadlogs --region $REGION
## Get role ARN
##

RESULT=`aws iam get-role --role-name Custom-Lambda-AzureADLogs --query Role.Arn`
ROLE=`echo $RESULT | sed 's/"//g'`

## Create Lambda function
##

aws lambda create-function --function-name azureadsiginlogs \
--role $ROLE --handler signinlogs.lambda_handler \
--runtime python3.6 --timeout 300 --zip-file fileb://lambda-signin.zip --region $REGION

aws lambda create-function --function-name azureadauditlogs \
--role $ROLE --handler auditlogs.lambda_handler \
--runtime python3.6 --timeout 300 --zip-file fileb://lambda-audit.zip --region $REGION

## Create secure parameters
##

aws ssm put-parameter --name AzureGraphAPIClientID \
--description "Azure AD Client ID used for Azure AD Log Lambdas" \
--type "SecureString" --value $CLIENTID \
--key-id "alias/azureadlogs" --region $REGION

aws ssm put-parameter --name AzureGraphAPIClientSecret \
--description "Azure AD Client Secret used for Azure AD Log Lambdas" \
--type "SecureString" --value $CLIENTSECRET \
--key-id "alias/azureadlogs" --region $REGION
