from __future__ import print_function
from crhelper import CfnResource
import logging
import boto3
import os

logger = logging.getLogger(__name__)
helper = CfnResource(json_logging=False, log_level='DEBUG', boto_level='CRITICAL')

client = boto3.client('cognito-idp')

try:
    ## Init code goes here
    pass
except Exception as e:
    helper.init_failure(e)


@helper.create
def create(event, context):
    logger.info("Creating Resource")
    
    stackName = event['ResourceProperties']['StackName'];
    userPoolId =  event['ResourceProperties']['UserPoolId']; 
    domain = stackName.lower() + '-' + userPoolId.replace("_","-").lower();
    domain = domain.replace("aws", "company");
    logger.info("Setting UserPool domain (" + domain + ")")
     
    client.create_user_pool_domain(
        Domain = domain,
        UserPoolId = userPoolId,
    )
    
    return "MyResourceId"


@helper.update
def update(event, context):
    logger.info("Got Update")


@helper.delete
def delete(event, context):
    logger.info("Deleting Resource")

    stackName = event['ResourceProperties']['StackName'];
    userPoolId =  event['ResourceProperties']['UserPoolId']; 
    domain = stackName.lower() + '-' + userPoolId.replace("_","-").lower();
    domain = domain.replace("aws", "company");
    stackName = event['ResourceProperties']['StackName'];
    
    
    
    client.delete_user_pool_domain(
        Domain = domain,
        UserPoolId = userPoolId
    )
    

@helper.poll_create
def poll_create(event, context):
    logger.info("Got create poll")
    return True


def handler(event, context):
    helper(event, context)
