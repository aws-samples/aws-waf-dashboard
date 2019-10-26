import boto3

bucket_prefix = "aws-waf-dashboard-"
regions = ["us-east-1","us-east-2","us-west-1","us-west-2","ca-central-1","eu-central-1","eu-west-1","eu-west-2","eu-west-3","eu-north-1","ap-northeast-1","ap-northeast-2","ap-northeast-3","ap-southeast-1","ap-southeast-2","ap-south-1","sa-east-1"]

for region in regions:
    
    print("Working on region: " + region);
    bucket_name = bucket_prefix + region
    
    file1 = 'domain-setter-lambda.zip'
    file2 = 'es-cognito-auth-lambda.zip'
    file3 = 'kibana-customizer-lambda.zip'

    s3 = boto3.resource('s3')
    s3.Bucket(bucket_name).upload_file(file1,file1)
    s3.Bucket(bucket_name).upload_file(file2,file2)
    s3.Bucket(bucket_name).upload_file(file3,file3)

    s3 = boto3.client('s3', region_name=region)
    s3.put_object_acl(ACL='public-read', Bucket=bucket_name, Key=file1)
    s3.put_object_acl(ACL='public-read', Bucket=bucket_name, Key=file2)
    s3.put_object_acl(ACL='public-read', Bucket=bucket_name, Key=file3)
