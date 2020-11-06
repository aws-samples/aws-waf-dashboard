import boto3

bucket_prefix = "waf-dashboards-"
regions = ["us-east-1","us-east-2","us-west-1","us-west-2","ca-central-1","eu-central-1","eu-west-1","eu-west-2","eu-west-3","eu-north-1","ap-northeast-1","ap-northeast-2","ap-northeast-3","ap-southeast-1","ap-southeast-2","ap-south-1","sa-east-1"]

for region in regions:
    
    print("Working on region: " + region);
    bucket_name = bucket_prefix + region
    
    print("-> Bucket: " + bucket_name);
    
    #Copying domain-setter-lambda.zip
    boto3.resource('s3').Bucket(bucket_name).upload_file("domain-setter-lambda.zip", 'domain-setter-lambda.zip')
    boto3.client('s3', region_name=region).put_object_acl(ACL='public-read',Bucket=bucket_name,Key='domain-setter-lambda.zip');
    
    #Copying es-cognito-auth-lambda.zip
    boto3.resource('s3').Bucket(bucket_name).upload_file("es-cognito-auth-lambda.zip", 'es-cognito-auth-lambda.zip')
    boto3.client('s3', region_name=region).put_object_acl(ACL='public-read',Bucket=bucket_name,Key='es-cognito-auth-lambda.zip');
    
    #Copying kibana-customizer-lambda.zip
    boto3.resource('s3').Bucket(bucket_name).upload_file("kibana-customizer-lambda.zip", 'kibana-customizer-lambda.zip')
    boto3.client('s3', region_name=region).put_object_acl(ACL='public-read',Bucket=bucket_name,Key='kibana-customizer-lambda.zip');
    
    
    #s3 = boto3.client('s3', region_name=region)
    #s3.delete_object(Bucket=bucket_name,Key='domain-setter-lambda.py');