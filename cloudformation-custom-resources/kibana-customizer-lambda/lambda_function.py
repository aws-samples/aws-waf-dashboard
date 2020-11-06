from __future__ import print_function
from crhelper import CfnResource
from requests_aws4auth import AWS4Auth
import logging
import boto3
import os
import requests

logger = logging.getLogger(__name__)
# Initialise the helper, all inputs are optional, this example shows the defaults
helper = CfnResource(json_logging=False, log_level='DEBUG', boto_level='CRITICAL')

waf = boto3.client('waf');
wafRegional = boto3.client('waf-regional')
wafv2_cloudfront = boto3.client('wafv2', region_name='us-east-1')
wafv2_regional = boto3.client('wafv2')
accountId = "TO_REPLACE"

try:
    ## Init code goes here
    pass
except Exception as e:
    helper.init_failure(e)


@helper.create
def create(event, context):
    logger.info("Got Create!")

    region = event['ResourceProperties']['Region'];
    host = event['ResourceProperties']['Host'];
    accountId = event['ResourceProperties']['AccountID'];
    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    import_index_template(host, awsauth)

    update_all(host, awsauth);

    return "MyResourceId"


@helper.update
def update(event, context):
    logger.info("Got Update. Creating enyway.")
    create(event, context);

@helper.delete
def delete(event, context):
    logger.info("Got Delete")

@helper.poll_create
def poll_create(event, context):
    logger.info("Got create poll")
    return True

def handler(event, context):
    helper(event, context)


def import_index_template(host, awsauth):

    url = 'https://' + host + '/_template/awswaf-logs';
    headers = { "Content-Type": "application/json" }

    with open("custom/template.json") as f:
        template = f.read()

    requests.put(url, auth=awsauth, headers=headers, data=template)


def import_kibana_object(host, awsauth, type, name):
    url = 'https://' + host + '/_plugin/kibana/api/saved_objects/' + type + '/' + name;
    headers = { "Content-Type": "application/json", 'kbn-xsrf': 'true' }

    with open("custom/" + name + ".json") as f:
        template = f.read()

    res = requests.post(url, auth=awsauth, headers=headers, data=template)

    print(res.text);

def delete_kibana_object(host, awsauth, type, name):
    url = 'https://' + host + '/_plugin/kibana/api/saved_objects/' + type + '/' + name;
    headers = { 'kbn-xsrf': 'true' }
    response = requests.delete(url, auth=awsauth, headers=headers)
    print(response.text);


def import_kibana_index_pattern(host, awsauth, type, name):
    url = 'https://' + host + '/_plugin/kibana/api/saved_objects/' + type + '/' + name;
    headers = { "Content-Type": "application/json", 'kbn-xsrf': 'true' }

    with open("custom/" + name + ".json") as f:
        template = f.read()

    webacls_mapping = generate_wafacls_mapping();
    template = template.replace("WEBACL_CUSTOM_MAPPINGS", webacls_mapping);

    rules_mapping = generate_rules_mapping();
    template = template.replace("RULE_CUSTOM_MAPPINGS", rules_mapping);

    response = requests.post(url, auth=awsauth, headers=headers, data=template)

def generate_rules_mapping():

    mappings = "";

    rules = wafRegional.list_rules()["Rules"];
    for rule in rules:
        mapping = "if (rule == \\\\\\\"" + rule["RuleId"] + "\\\\\\\") { return \\\\\\\"" + rule["Name"] + "\\\\\\\";}\\\\n"
        mappings = mappings + mapping;

    rules = waf.list_rules()["Rules"];
    for rule in rules:
        mapping = "if (rule == \\\\\\\"" + rule["RuleId"] + "\\\\\\\") { return \\\\\\\"" + rule["Name"] + "\\\\\\\";}\\\\n"
        mappings = mappings + mapping;

    return mappings;


def update_all(host, awsauth):
    delete_kibana_object(host, awsauth, "index-pattern", "awswaf")
    import_kibana_index_pattern(host, awsauth, "index-pattern", "awswaf")

    import_kibana_object(host, awsauth, "visualization", "allcountries")
    import_kibana_object(host, awsauth, "visualization", "executedrules")
    import_kibana_object(host, awsauth, "visualization", "filters")
    import_kibana_object(host, awsauth, "visualization", "numberofallrequests")
    import_kibana_object(host, awsauth, "visualization", "numberofblockedrequests")
    import_kibana_object(host, awsauth, "visualization", "allvsblockedrequests")
    import_kibana_object(host, awsauth, "visualization", "top10countries")
    import_kibana_object(host, awsauth, "visualization", "top10useragents")
    import_kibana_object(host, awsauth, "visualization", "top10uris")
    import_kibana_object(host, awsauth, "visualization", "top10rules")
    import_kibana_object(host, awsauth, "visualization", "top10ip")
    import_kibana_object(host, awsauth, "visualization", "top10hosts")
    import_kibana_object(host, awsauth, "visualization", "httpmethods")
    import_kibana_object(host, awsauth, "visualization", "httpversions")
    import_kibana_object(host, awsauth, "visualization", "uniqueipcount")
    import_kibana_object(host, awsauth, "visualization", "requestcount")
    import_kibana_object(host, awsauth, "visualization", "top10webacl")

    import_kibana_object(host, awsauth, "dashboard", "dashboard")


def generate_wafacls_mapping():

    mappings = "";

    webacls = wafRegional.list_web_acls()["WebACLs"];
    for webacl in webacls:
        mapping = "if (webacl == \\\\\\\"" + webacl["WebACLId"] + "\\\\\\\") { return \\\\\\\"" + webacl["Name"] + "\\\\\\\";}\\\\n"
        mappings = mappings + mapping;

    webacls = waf.list_web_acls()["WebACLs"];
    for webacl in webacls:
        mapping = "if (webacl == \\\\\\\"" + webacl["WebACLId"] + "\\\\\\\") { return \\\\\\\"" + webacl["Name"] + "\\\\\\\";}\\\\n"
        mappings = mappings + mapping;

    webacls = wafv2_cloudfront.list_web_acls(Scope='CLOUDFRONT')['WebACLs']
    for webacl in webacls:
        logWebACLId = "arn:aws:wafv2:us-east-1:" + os.environ['ACCOUNT_ID'] + ":global/webacl/" + webacl["Name"] + "/" + webacl["Id"];
        mapping = "if (webacl == \\\\\\\"" + logWebACLId + "\\\\\\\") { return \\\\\\\"" + webacl["Name"] + "\\\\\\\";}\\\\n"
        mappings = mappings + mapping;

    webacls = wafv2_regional.list_web_acls(Scope='REGIONAL')['WebACLs']
    for webacl in webacls:
        logWebACLId = "arn:aws:wafv2:" + os.environ['REGION'] + ":" + os.environ['ACCOUNT_ID'] + ":regional/webacl/" + webacl["Name"] + "/" + webacl["Id"];
        mapping = "if (webacl == \\\\\\\"" + logWebACLId + "\\\\\\\") { return \\\\\\\"" + webacl["Name"] + "\\\\\\\";}\\\\n"
        mappings = mappings + mapping;

    return mappings;



def update_kibana(event, context):

    region = os.environ['REGION']
    host = os.environ['ES_ENDPOINT']
    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    delete_kibana_object(host, awsauth, "index-pattern", "awswaf")
    import_kibana_index_pattern(host, awsauth, "index-pattern", "awswaf")

    #update_all(host, awsauth);
