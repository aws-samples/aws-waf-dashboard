from __future__ import print_function
from crhelper import CfnResource
import logging
import boto3
import os
import time

logger = logging.getLogger(__name__)
# Initialise the helper, all inputs are optional, this example shows the defaults
helper = CfnResource(json_logging=False, log_level='DEBUG', boto_level='CRITICAL')

es = boto3.client('es')

try:
    ## Init code goes here
    pass
except Exception as e:
    helper.init_failure(e)


@helper.create
def create(event, context):
    logger.info("Got Create!")
    
    stackName = event['ResourceProperties']['StackName'];
    userPoolId = event['ResourceProperties']['UserPoolId']; 
    identityPoolId = event['ResourceProperties']['IdentityPoolId'];
    roleArn = event['ResourceProperties']['RoleArn'];
    domainName = event['ResourceProperties']['DomainName'];
    
    logger.info("User Pool ID: " + userPoolId)
    logger.info("Identity Pool ID: " + identityPoolId)
    logger.info("Role ARN: " + roleArn)
    
    logger.info("Updating ES with Cognito Config!")
    es.update_elasticsearch_domain_config(
        DomainName = domainName,
        CognitoOptions={
            'Enabled': True,
            'UserPoolId': userPoolId,
            'IdentityPoolId': identityPoolId,
            'RoleArn': roleArn
        }
    )
    logger.info("Waiting for ES be is active state")
    
    time.sleep(10)
    
    limit = 0;
    
    processing = True;
    while (processing):
        limit = limit + 1;
        
        processing = es.describe_elasticsearch_domain(
            DomainName = domainName
        )['DomainStatus']['Processing']
        
        logger.info("Waiting... ES is still processing (" + str(limit) + ")");
        
        time.sleep(30)
        
        if (limit > 20):
            processing = False;
    
    logger.info("Done!")
    
    return "MyResourceId"


@helper.update
def update(event, context):
    logger.info("Got Update")


@helper.delete
def delete(event, context):
    logger.info("Got Delete")
    

@helper.poll_create
def poll_create(event, context):
    logger.info("Got create poll")
    return True


def handler(event, context):
    helper(event, context)
