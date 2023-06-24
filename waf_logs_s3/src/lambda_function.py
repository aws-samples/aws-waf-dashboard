import urllib.parse
import boto3
import io
import gzip
import os
import math

print('Loading function')

s3 = boto3.client('s3')
firehose = boto3.client('firehose')
firehose_stream_name = os.environ.get('FIREHOSE_STREAM_NAME')

def putRecordsToKinesisStream(streamName, records, client, attemptsMade, maxAttempts):
    failedRecords = []
    codes = []
    errMsg = ''
    # if put_records throws for whatever reason, response['xx'] will error out, adding a check for a valid
    # response will prevent this
    response = None
    try:
        response = client.put_record_batch(
        DeliveryStreamName=streamName,
        Records=[
            {
                'Data': records
            }
        ])
        print(response)
    except Exception as e:
        print(response)
        failedRecords = records
        errMsg = str(e)


    # if there are no failedRecords (put_record_batch succeeded), iterate over the response to gather results
    if not failedRecords and response and response['FailedPutCount'] > 0:
        for idx, res in enumerate(response['Records']):
            # (if the result does not have a key 'ErrorCode' OR if it does and is empty) => we do not need to re-ingest
            if not res.get('ErrorCode'):
                continue

            codes.append(res['ErrorCode'])
            failedRecords.append(records[idx])

        errMsg = 'Individual error codes: ' + ','.join(codes)

    if failedRecords:
        if attemptsMade + 1 < maxAttempts:
            print('Some records failed while calling PutRecords to Kinesis stream, retrying. %s' % (errMsg))
            putRecordsToKinesisStream(streamName, failedRecords, client, attemptsMade + 1, maxAttempts)
        else:
            raise RuntimeError('Could not put records after %s attempts. %s' % (str(maxAttempts), errMsg))

def putRecordToKinesisStream(streamName, records, client, attemptsMade, maxAttempts):
    failedRecords = []
    codes = []
    errMsg = ''
    # if put_records throws for whatever reason, response['xx'] will error out, adding a check for a valid
    # response will prevent this
    response = None
    try:
        response = client.put_record(
        DeliveryStreamName=streamName,
        Record={
                'Data': records
            })
    except Exception as e:
        print(response)
        failedRecords = records
        errMsg = str(e)

    if failedRecords:
        if attemptsMade + 1 < maxAttempts:
            print('Some records failed while calling PutRecords to Kinesis stream, retrying. %s' % (errMsg))
            putRecordsToKinesisStream(streamName, failedRecords, client, attemptsMade + 1, maxAttempts)
        else:
            raise RuntimeError('Could not put records after %s attempts. %s' % (str(maxAttempts), errMsg))

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
            #putRecordsToKinesisStream(firehose_stream_name, ''.join(lines).strip(), firehose, 1, 2)

    except Exception as e:
        print(e)
        raise e
