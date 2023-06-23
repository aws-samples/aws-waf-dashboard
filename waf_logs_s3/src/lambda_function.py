import urllib.parse
import boto3
import io
import gzip
import os

print('Loading function')

s3 = boto3.client('s3')
firehose = boto3.client('firehose')

firehose_stream_name = os.environ.get('FIREHOSE_STREAM_NAME')

def lambda_handler(event, context):
    #print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read()
        fobj=io.BytesIO(content)
        with gzip.open(fobj, mode='rt') as fh:
            #todo: change to batch  
            lines =  fh.readlines()
            for line in lines:
                fh_response = firehose.put_record(
                DeliveryStreamName=firehose_stream_name,
                Record={
                        'Data': line.strip()
                })
                print(fh_response)

    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e
