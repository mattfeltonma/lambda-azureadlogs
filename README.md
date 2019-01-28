# Azure AD Logs Lambda Download
This lambda function uses the [Microsoft Azure Active Directory reporting API](https://docs.microsoft.com/en-us/azure/active-directory/reports-monitoring/concept-reporting-api) to retrieve the raw Azure Active Directory Sign-In and Audit Logs and stores them in an S3 bucket.  It is written in Python 3.6.

## What problem does this solve?
Microsoft rotates the logs every 30 days or less depending on the [license](https://docs.microsoft.com/en-us/azure/active-directory/reports-monitoring/reference-reports-data-retention) assigned to the Azure AD tenant.  These logs provide critical security related data for Microsoft Office 365, Microsoft Azure, and applications integrated with Azure Active Directory.  This function provides an affordable and simple solution to preserving the logs.

## Requirements
### Microsoft

The function uses [Microsoft's Azure Active Directory Authentication Library (ADAL)](https://docs.microsoft.com/en-us/azure/active-directory/develop/active-directory-authentication-libraries) to obtain an OAuth bearer access token from Azure Active Director for use with the API.

The function (or Client in OAuth 2.0 terminology) must be registered with Azure Active Directory and granted the appropriate scopes of access.  This [link](https://docs.microsoft.com/en-us/azure/active-directory/reports-monitoring/howto-configure-prerequisites-for-reporting-api) provides more detail.

### Amazon Web Services
The function uses AWS services below.  It also requires the AWS CLI.

The [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-paramstore.html) to store parameters for the Lambda.  The Azure Active Directory Client ID and Client Secret are stored as encrypted parameters.
 
[AWS Key Management Service](https://docs.aws.amazon.com/kms/latest/developerguide/overview.html) to provide the keys for encrypted parameters.

[AWS CloudFormation](https://aws.amazon.com/cloudformation/resources/) to provision the infrastructure as code.

[AWS IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html) to provide identity and access management services to AWS.

[AWS Simple Storage Service](https://aws.amazon.com/s3/developer-resources/?nc=sn&loc=4&dn=2) to provide object storage for the logs.

[AWS Lambda](https://aws.amazon.com/lambda/resources/) to provide a serverless architecture to run the Python code.

### Setup
Clone the repository.

Prior to setting up the Lambdas you will need to create the Azure Active Directory identity the Lambda functions will use.  Follow the instructions in this Microsoft [link](https://docs.microsoft.com/en-us/azure/active-directory/reports-monitoring/howto-configure-prerequisites-for-reporting-api).  After you obtain the client ID and client secret, you will need to enter those values into the setup.sh Bash script along with the other required variables.

The Bash script will create the Lambda packages, provision the KMS CMK, the CMK resource policy, the Lambda IAM role, and the non-encrypted parameters.  The AWS CLI is then used to create the Lambda functions and the secure parameters using the KMS CMK created by the CloudFormation template.

The Lambdas write the log files to separate prefixes in the S3 bucket you designate during setup.  By default the Lambdas download one day of logs but that can be adjusted by changing the AzureGraphAPIAuditLogDays and AzureGraphAPISignInDays parameters.

You can then automate the Lambdas with your tool of choice.  I personally use a CloudWatch Event that runs once a day to download the day of logs.
