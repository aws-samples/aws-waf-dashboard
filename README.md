# AWS WAF Dashboard

## Description

AWS WAF Dashboards are ready to use dashboards (build on Amazon OpenSearch Service with OpenSearch Dashboards) which can be quickly connected to already existing AWS WAF configuration and allow visualization of AWS WAF Logs with multiple build in visualization diagrams.

To start using  AWS WAF Dashboards you don't need to have any prior experience with Amazon OpenSearch or even AWS WAF, minimal AWS knowledge is require. You just need to run AWS CDK commands - which will do all the rest. The whole process takes around 30 minutes (with 25 minutes of waiting).

*Note:* You will need to launch the AWS CDK project in the us-east-1 AWS Region if you are using an AWS WAF web ACL that is associated to an Amazon CloudFront distribution. Otherwise, you have the option to launch the AWS CDK project in any AWS Region that supports the AWS services to be deployed.
Alternatively if you have enabled WAF logging into S3 you can copy those logs (suffix: .log.gz) into dedicated S3 bucket and tey will be also ingested.

## Installation

#### Deploy the solution by using the AWS CDK
We provide an AWS Cloud Development Kit (AWS CDK) project that you will deploy to set up the whole solution automatically in your preferred AWS account. 

Use the integrated development environment (IDE) of your choice. Make sure you have set up your environment with all the prerequisites of working with the AWS CDK. This particular AWS CDK project is written in Java, so make sure to also check the prerequisites for working with the CDK in Java. 

To deploy the solution
1.	Clone the repo by running the following command.

```
git clone https://github.com/aws-samples/aws-waf-dashboard.git 
```
2.	Navigate into the cloned project folder by running the following command.

```
cd aws-waf-dashboard
```
3.	Run the cdk commands to deploy the infrastructure.
 
The first time you deploy an AWS CDK app into an environment (account and AWS Region), you’ll need to install a bootstrap stack. This stack includes resources that are needed for the toolkit’s operation. For example, the stack includes an Amazon Simple Storage Services (Amazon S3) bucket that is used to store templates and assets during the deployment process.

Run the following command to bootstrap your environment.
```
cdk bootstrap
```
4.	After the bootstrap command has completed, you can start deploying the solution. You will need to pass two parameters with your deployment command: 
•	The email that you will use as your username.
•	The Cognito domain. You can enter the name of your choice for the Cognito domain. 

Note that the Cognito domain name you choose will serve as a domain prefix for the Cognito hosted UI URL and needs to be unique. See Configuring a user pool domain in the Amazon Cognito User Guide if you need more information on Cognito domains.

Run the following command:

```
cdk deploy --parameters osdfwDashboardsAdminEmail=<yourEmail> --parameters osdfwCognitoDomain=<uniqueCognitoDomain>
```
Type *y* and press enter when prompted if you wish to deploy the changes.

There are three more optional AWS CDK deployment parameters that have default values. You can use these parameters in addition to the mandatory parameters (the email and Cognito domain). The additional parameters are the following:	

•	**EBS size for the OpenSearch Service cluster:** *osdfwOsEbsSize*

•	**Node type for the OpenSearch Service cluster:** *osdfwOsNodeSize*

•	**OpenSearchDomainName:** *osdfwOsDomainName*

#### Verify that the OpenSearch dashboard works
To test the OpenSearch dashboard:
1.	First, check the email address that you provided in the parameter for *osdfwDashboardsAdminEmail*. You should have received an email with the required password to log in to the OpenSearch dashboard. Make a note of it. 

2.	Now return to the environment where you ran the AWS CDK deployment. There should be a link under Outputs, as shown in the graphic below:

<img src="graphics/1.png" width="400">

3.	Select the link and log into the OpenSearch dashboard. Provide the email address that you set up in Step 1 and the password that was sent to it. You will be prompted to update the password.

4.	In the OpenSearch dashboard, choose the OpenSearch Dashboards logo (the burger icon) at the top left. Then under Dashboards, choose WAFDashboard. This will display the AWS WAF dashboard.

<img src="graphics/2.png" width="400">

The dashboard should still be empty because it hasn’t connected with AWS WAF yet.

#### Connect WAF logs
To connect to AWS WAF logs
1.	Open the AWS WAF console and choose Web ACLs. Then choose your desired web ACL.
2.	If you haven’t enabled AWS WAF logs yet, you need to do so now in order to continue. To do this, choose the Logging and metrics tab in your web ACL, and then choose Enable.
3.	For Amazon Kinesis Data Firehose delivery stream, select the Kinesis Firehose that was created by the template in Step 1. Its name starts with aws-waf-logs. 
4.	Save your changes.

#### Copy WAF logs 
Copy WAF logs that youre interestd in from S3 from loacation configured in web ACL into bucket displayed in output of cdk deployment, ex:

```
OSDfW.osdfwS3SinkBucketName = osdfw-osdfws3sinkbucket26ae0e20-1uutfdionqwmf
```

#### Final result
That's all! Now, your WAF logs will be send from WAF service throug Kinesis Firehose directly to the OpenSearch cluster and will become available to you using OpenSearch dashboards. After a couple of minutes, you should start seeing that your dashboards have got data on it.

Important! By the default, OpenSearch dashboard will be publicly accessible from Internet (although only Administrator will be able to create users who will be able to log in via Cognito). In production environment, we recomend to put a proxy in front of it, to allow access only from specific IP addresses.

<img src="graphics/3.png" width="700">
