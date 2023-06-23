package com.myorg;


import software.amazon.awscdk.CfnOutput;
import software.constructs.Construct;
import software.amazon.awscdk.NestedStack;
import software.amazon.awscdk.RemovalPolicy;
import software.amazon.awscdk.services.iam.*;
import software.amazon.awscdk.services.kinesisfirehose.CfnDeliveryStream;
import software.amazon.awscdk.services.logs.LogGroup;
import software.amazon.awscdk.services.logs.LogStream;
import software.amazon.awscdk.services.logs.RetentionDays;
import software.amazon.awscdk.services.opensearchservice.Domain;
import software.amazon.awscdk.services.s3.Bucket;

import java.util.List;

public class StreamStack extends NestedStack {
    LogGroup cwLogGroup;
    LogStream cwLogStreamOpenSearch;
    LogStream cwLogStreamS3;
    Role firehoseRole;

    public StreamStack(final Construct scope, final String id, StreamStackProps streamStackProps) {
        super(scope, id, streamStackProps);

        //todo parametrise
        String wafIndexName = "awswaf";
        int streamBufferSize = 5;
        int streamBufferTimeInterval = 60;


        createLoggingConfiguration();

        Bucket logDeliveryBucket = Bucket.Builder.create(this, "osdfwLogBucket")
                .removalPolicy(RemovalPolicy.RETAIN)
                .build();

        this.firehoseRole = generateFirehoseRole(streamStackProps, logDeliveryBucket);

        CfnDeliveryStream.ElasticsearchDestinationConfigurationProperty openSearchDestinationForFirehose = CfnDeliveryStream.ElasticsearchDestinationConfigurationProperty.builder()
                .bufferingHints(CfnDeliveryStream.ElasticsearchBufferingHintsProperty.builder()
                        .intervalInSeconds(streamBufferTimeInterval)
                        .sizeInMBs(streamBufferSize)
                        .build())
                .cloudWatchLoggingOptions(CfnDeliveryStream.CloudWatchLoggingOptionsProperty.builder()
                        .enabled(true)
                        .logGroupName(this.cwLogGroup.getLogGroupName())
                        .logStreamName(this.cwLogStreamOpenSearch.getLogStreamName())
                        .build())
                .domainArn(streamStackProps.getOpenSearchDomain().getDomainArn())
                .indexName(wafIndexName)
                .indexRotationPeriod("OneDay")
                .retryOptions(CfnDeliveryStream.ElasticsearchRetryOptionsProperty.builder().durationInSeconds(60).build())
                .roleArn(this.firehoseRole.getRoleArn())
                .s3BackupMode("AllDocuments")
                .s3Configuration(CfnDeliveryStream.S3DestinationConfigurationProperty.builder()
                        .bucketArn(logDeliveryBucket.getBucketArn())
                        .bufferingHints(CfnDeliveryStream.BufferingHintsProperty.builder()
                                .intervalInSeconds(streamBufferTimeInterval * 5)
                                .sizeInMBs(streamBufferSize * 10)
                                .build())
                        .compressionFormat("ZIP")
                        .prefix("/log")
                        .roleArn(this.firehoseRole.getRoleArn())
                        .cloudWatchLoggingOptions(CfnDeliveryStream.CloudWatchLoggingOptionsProperty.builder()
                                .enabled(true)
                                .logGroupName(this.cwLogGroup.getLogGroupName())
                                .logStreamName(this.cwLogStreamS3.getLogStreamName())
                                .build())
                        .build())
                .build();


        CfnDeliveryStream wafLogsDeliveryStream = CfnDeliveryStream.Builder.create(this, "osdfwWafFirehoseDeliveryStream")
                .deliveryStreamName("aws-waf-logs-osdfw")
                .deliveryStreamType("DirectPut")
                .elasticsearchDestinationConfiguration(openSearchDestinationForFirehose)
                .build();


        CfnOutput.Builder.create(this, "osdfwVarOsDomain")
                .value(streamStackProps.getOpenSearchDomain().getDomainArn())
                .build();

        CfnOutput.Builder.create(this, "osdfwFirehoseArn")
                .description("Firehose ARN")
                .value(wafLogsDeliveryStream.getAttrArn())
                .build();

    }

    public void createLoggingConfiguration() {
        this.cwLogGroup = LogGroup.Builder.create(this, "osdfwFirehose")
                .removalPolicy(RemovalPolicy.DESTROY)
                .retention(RetentionDays.ONE_MONTH)
                .build();

        this.cwLogStreamS3 = LogStream.Builder.create(this, "osdfwS3Delivery")
                .logGroup(cwLogGroup)
                .removalPolicy(RemovalPolicy.DESTROY)
                .build();

        this.cwLogStreamOpenSearch = LogStream.Builder.create(this, "osdfwOsDelivery")
                .logGroup(cwLogGroup)
                .removalPolicy(RemovalPolicy.DESTROY)
                .build();
    }

    public Role generateFirehoseRole(StreamStackProps streamStackProps, Bucket logDeliveryBucket) {
        Role firehoseRole = Role.Builder.create(this, "osdfwLogDeliveryRole")
                .managedPolicies(List.of(ManagedPolicy.fromAwsManagedPolicyName("AdministratorAccess"))) //todo
                .description("Role for WAF Dashboards log delivery")
                .assumedBy(new ServicePrincipal("firehose.amazonaws.com"))
                .build();

        ManagedPolicy.Builder.create(this, "osdfwFirehosePolicy")
                .statements(generatePolicyStatements(streamStackProps.getOpenSearchDomain(), logDeliveryBucket))
                .roles(List.of(firehoseRole))//todo
                .build();

        return firehoseRole;
    }

    public List<PolicyStatement> generatePolicyStatements(Domain openSearchDomain, Bucket firehoseDeliveryBucket) {
        PolicyStatement s3AccessStatement = PolicyStatement.Builder.create()
                .sid("osdfwS3AccessStatement")
                .effect(Effect.ALLOW)
                .actions(List.of(
                        "s3:AbortMultipartUpload",
                        "s3:GetBucketLocation",
                        "s3:GetObject",
                        "s3:ListBucket",
                        "s3:ListBucketMultipartUploads",
                        "s3:PutObject"))
                .resources(List.of(
                        firehoseDeliveryBucket.getBucketArn(),
                        firehoseDeliveryBucket.getBucketArn() + "/*"
                ))
                .build();

        PolicyStatement openSearchPutAccessStatement = PolicyStatement.Builder.create()
                .sid("osdfwOpenSearchPutAccessStatement")
                .effect(Effect.ALLOW)
                .actions(List.of(
                        "es:DescribeElasticsearchDomain",
                        "es:DescribeElasticsearchDomains",
                        "es:DescribeElasticsearchDomainConfig",
                        "es:ESHttpPost",
                        "es:ESHttpPut"))
                .resources(List.of(
                        openSearchDomain.getDomainArn(),
                        openSearchDomain.getDomainArn() + "/*"))
                .build();

        PolicyStatement openSearchMiscGetAccessStatement = PolicyStatement.Builder.create()
                .sid("osdfwOpenSearchMiscAccessStatement")
                .effect(Effect.ALLOW)
                .actions(List.of("es:ESHttpGet"))
                .resources(List.of(
                        openSearchDomain.getDomainArn() + "/_all/_settings",
                        openSearchDomain.getDomainArn() + "/_cluster/stats",
                        openSearchDomain.getDomainArn() + "/awswaf/_mapping/%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%",
                        openSearchDomain.getDomainArn() + "/_nodes",
                        openSearchDomain.getDomainArn() + "/_nodes/stats",
                        openSearchDomain.getDomainArn() + "/_nodes/*/stats",
                        openSearchDomain.getDomainArn() + "/_stats",
                        openSearchDomain.getDomainArn() + "/awswaf/_stats"))
                .build();

        PolicyStatement cwLogDeliveryAccessStatement = PolicyStatement.Builder.create()
                .sid("osdfwLogDeliveryAccessStatement")
                .effect(Effect.ALLOW)
                .actions(List.of("logs:PutLogEvents"))
                .resources(List.of(this.cwLogGroup.getLogGroupArn() + ":*"))
                .build();

        PolicyStatement admin = PolicyStatement.Builder.create()
                .sid("osdfwAdminAccessStatement")
                .effect(Effect.ALLOW)
                .actions(List.of("*"))
                .resources(List.of("*"))
                .build();

        return List.of(s3AccessStatement,
                openSearchPutAccessStatement,
                openSearchMiscGetAccessStatement,
                cwLogDeliveryAccessStatement,
                admin);//todo);
    }

}
