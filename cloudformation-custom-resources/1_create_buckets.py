import boto3

bucket_prefix = "aws-waf-dashboard-"
regions = ["us-east-1","us-east-2","us-west-1","us-west-2","ca-central-1","eu-central-1","eu-west-1","eu-west-2","eu-west-3","eu-north-1","ap-northeast-1","ap-northeast-2","ap-northeast-3","ap-southeast-1","ap-southeast-2","ap-south-1","sa-east-1"]

for region in regions:
    
    print("Working on region: " + region);
    bucket_name = bucket_prefix + region
    
    s3 = boto3.client('s3', region_name=region)
    if (region != 'us-east-1'):
        s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
    else:
        s3.create_bucket(Bucket=bucket_name)
    
