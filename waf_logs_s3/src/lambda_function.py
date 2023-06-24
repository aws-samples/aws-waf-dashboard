import urllib.parse
import boto3
import io
import gzip
import os
import math


s3 = boto3.client('s3')
firehose = boto3.client('firehose')
firehose_stream_name = os.environ.get('FIREHOSE_STREAM_NAME')


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
            lines =  fh.readlines()
            for l in lines:
                putRecordToKinesisStream(firehose_stream_name, l.strip(), firehose, 1, 2) 
 
    except Exception as e:
        print(e)
        raise e
