import json
import time
import datetime
import boto3
import requests
import re
from adal import AuthenticationContext

print('Loading function')


def obtain_accesstoken(tenantname,clientid,clientsecret):
    auth_context = AuthenticationContext('https://login.microsoftonline.com/' +
        tenantname)
    token = auth_context.acquire_token_with_client_credentials(
        resource="https://graph.microsoft.com",client_id=clientid,
        client_secret=clientsecret)
    return token
    
def makeapirequest(endpoint,token,q_param=None):
    ## Create a valid header using the provided access token
    ##
        
    headers = {'Content-Type':'application/json', \
    'Authorization':'Bearer {0}'.format(token['accessToken'])}
           
    ## This section handles a bug with the Python requests module which
    ## encodes blank spaces to plus signs instead of %20.  This will cause
    ## issues with OData filters
    
    if q_param != None:
        response = requests.get(endpoint,headers=headers,params=q_param)
        print('Request made to ' + response.url)
    else:
        response = requests.get(endpoint,headers=headers)
        print('Request made to ' + response.url)
    if response.status_code == 200:
        json_data = json.loads(response.text)
            
        ## This section handles paged results and combines the results 
        ## into a single JSON response.  This may need to be modified
        ## if results are too large

        if '@odata.nextLink' in json_data.keys():
            
            print('Received paged response...')
            record = makeapirequest(json_data['@odata.nextLink'],token)
            entries = len(record['value'])
            count = 0
            while count < entries:
                json_data['value'].append(record['value'][count])
                count += 1
        return(json_data)
    else:
        raise Exception('Request failed with ',response.status_code,' - ',
            response.text)

    
def lambda_handler(event, context):

    try:
        print('Attempting to contact Parameter Store...')
        
        ## Get encrypted parameters from parameter store
        ##
        client = boto3.client('ssm')
        response = client.get_parameters(
            Names=[
                "AzureGraphAPIClientID",
                "AzureGraphAPIClientSecret"
            ],
            WithDecryption=True
        )
        
        for parameter in response['Parameters']:
            if parameter['Name'] == "AzureGraphAPIClientID":
                clientid = parameter['Value']
            elif parameter['Name'] == "AzureGraphAPIClientSecret":
                clientsecret = parameter['Value']
        
        ## Get unencrypted parameters from parameter store
        ##
        client = boto3.client('ssm')
        response = client.get_parameters(
            Names=[
                "AzureGraphAPITenantName",
                "AzureGraphAPIAuditLogsEndpoint",
                "AzureGraphAPIBucket",
                "AzureGraphAPIAuditLogDays"
            ],
            WithDecryption=False
        )
        
        for parameter in response['Parameters']:
            if parameter['Name'] == "AzureGraphAPITenantName":
                tenantname = parameter['Value']
            elif parameter['Name'] == "AzureGraphAPIAuditLogsEndpoint":
                endpoint = parameter['Value']
            elif parameter['Name'] == "AzureGraphAPIBucket":
                bucket = parameter['Value']
            elif parameter['Name'] == "AzureGraphAPIAuditLogDays":
                logdays = parameter['Value']
    
        ## Obtain current date and create OData filter
        ##
    
        todaydate = (datetime.datetime.now()).strftime("%Y-%m-%d")
        yesterdaydate = (datetime.datetime.today() - datetime.timedelta(days=int(logdays))).strftime("%Y-%m-%d")
        filter = "activityDateTime gt " + yesterdaydate + " and activityDateTime lt " + todaydate
        params = { "$filter":filter}
    
        print('Attempting to obtain an access token...')
    
        ## Obtain bearer token from Azure AD
        ##
    
        token = obtain_accesstoken(tenantname,clientid,clientsecret)

        ## Submit request to Graph API
        ##
    
        data = makeapirequest(endpoint,token,q_param=params)
        
        if '@odata.context' in data.keys():
            del data['@odata.context']
        elif '@odata.nextLink' in data.keys():
            del data['@odata.nextLink']
        ## Cleanup the sign in logs
        ##
    
        for record in data['value']:
            record['activityDateTime'] = re.sub('[TZ]',' ', record['activityDateTime'])
    
        ## Encode string
        ##
        string = json.dumps(data)
        encoded_string = string.encode("utf-8")

        print("Writing file to s3...")
        s3_path = "aadauditlogs/" + todaydate + "-" + yesterdaydate + ".json"
        s3 = boto3.resource('s3')
        s3.Bucket(bucket).put_object(Key=s3_path, Body=encoded_string)
    except Exception as e:
        print("Expection thrown: {}".format(e))