import urllib.parse
import boto3
import io
import gzip
import os
import math
import json
from requests_aws4auth import AWS4Auth
import requests


s3 = boto3.client('s3')
firehose = boto3.client('firehose')
event_client = boto3.client('events')
firehose_stream_name = os.environ.get('FIREHOSE_STREAM_NAME')
region = os.environ.get('REGION')
os_endpoint = os.environ.get('OS_ENDPOINT')
update_dashboards = False

def getExistingWebACLIDsFromOpenSearch():
    host = os_endpoint
    path = '/_cat/indices?format=json'
    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(service=service, region=region, refreshable_credentials=credentials)
    url = "https://" + host + path
    r = requests.get(url, auth=awsauth)
    indices_json_details = r.json()
    indices_json = [i["index"].strip() for i in indices_json_details if i["index"].startswith('awswaf-') and i["status"] == "open"]
    webaclIdSet = set()
    payload = json.loads('{ "query": { "match_all": {}}, "collapse": { "field": "webaclId.keyword"},"_source": false}')
    for i  in indices_json:
        path = '/' + i.strip() +"/_search"
        url = "https://" + host.strip() + path.strip()
        r = requests.post(url, auth=awsauth, json=payload)
        r_json = r.json()
        for hit in r_json['hits']['hits']:
            webaclIdSet.update(hit['fields']['webaclId.keyword'])

    return webaclIdSet

def sendEventToEventBus():
    event = {
        "eventSource": ["sink.lambda"],
        "eventName": ["CreateWebACL"]
    }
    try:
        response = event_client.put_events(
            Entries=[
                {
                    'Source': 'sink.s3',
                    'DetailType': 'S3 Sink',
                    'Detail': json.dumps(event),
                    'EventBusName': 'default'  
                },
            ]
        ) 
    except Exception as e:
        print(e)
        raise e

def putRecordToKinesisStream(streamName, record, client, attemptsMade, maxAttempts):
    failedRecord = []
    codes = []
    errMsg = ''

    response = None
    try:
        response = client.put_record(
        DeliveryStreamName=streamName,
        Record={
                'Data': record
            })
    except Exception as e:
        print(response)
        failedRecord = record
        errMsg = str(e)

    if failedRecord:
        if attemptsMade + 1 < maxAttempts:
            print('Some record failed while calling PutRecord to Kinesis stream, retrying. %s' % (errMsg))
            putRecordToKinesisStream(streamName, failedRecord, client, attemptsMade + 1, maxAttempts)
        else:
            raise RuntimeError('Could not put record after %s attempts. %s' % (str(maxAttempts), errMsg))

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read()
        fobj=io.BytesIO(content)
        with gzip.open(fobj, mode='rt') as fh:
            for l in fh:
                putRecordToKinesisStream(firehose_stream_name, l.strip(), firehose, 1, 1) 
 
    except Exception as e:
        print(e)
        raise e
