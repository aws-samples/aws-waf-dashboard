package com.myorg;

import software.amazon.awscdk.services.events.EventPattern;
import software.amazon.awscdk.services.events.Rule;
import software.amazon.awscdk.services.events.targets.LambdaFunction;
import software.amazon.awscdk.services.iam.*;
import software.amazon.awscdk.services.lambda.Runtime;
import software.amazon.awscdk.services.lambda.*;
import software.amazon.awscdk.services.logs.RetentionDays;
import software.amazon.awscdk.services.s3.assets.AssetOptions;
import software.constructs.Construct;
import software.amazon.awscdk.NestedStack;
import software.amazon.awscdk.BundlingOptions;
import software.amazon.awscdk.CustomResource;
import software.amazon.awscdk.RemovalPolicy;
import software.amazon.awscdk.Duration;

import java.util.List;
import java.util.Locale;
import java.util.Map;


public class AppStack extends NestedStack {
    public Function dashboardsCustomizerLambda;

    public AppStack(Construct scope, String id, StreamStackProps props, String bundleLambda) {
        super(scope, id, props);

        Code lambdaCodeLocation = null;  


        if (bundleLambda.equalsIgnoreCase("true")){

                List<String> bundleCommand = List.of("bash", "-c", 
                        "DIR=$(pwd) && "                        
                        +"mkdir /asset-output/python && "
                        + "pip install -r requirements.txt -t /asset-output/python  && "
                        + "cd /asset-output/python && "
                        + "find . -type f "
                        + "-not -path '*.pyc' "
                        + "-exec cp --parents {} .. \\; && "
                        + "cd ${DIR} && "
                        + "rm -fr /asset-output/python &&"
                        + "find . -type f "
                        + "-not -path './python_virtual_env/*' "
                        + "-not -path '*.pyc' "
                        + "-not -path '*.zip' "
                        + "-not -path './.DS_Store' "
                        + "-exec cp --parents {} /asset-output \\; && "
                        + "cd /asset-output && "
                        + "zip -r ${DIR}/os-customizer-lambda.zip *");
                
                BundlingOptions bundlingOptions = BundlingOptions.builder()
                                .image(Runtime.PYTHON_3_9.getBundlingImage())
                                .command(bundleCommand)
                                .build();
                lambdaCodeLocation = Code.fromAsset("assets", 
                        AssetOptions.builder().bundling(bundlingOptions).build());
        } else {
                lambdaCodeLocation = Code.fromAsset("assets/os-customizer-lambda.zip");
        }
 
        

        Role customizerRole = createLambdaRole();

        this.dashboardsCustomizerLambda = Function.Builder.create(this, "osdfwDashboardsSeeder")
                .architecture(Architecture.ARM_64)
                .description("AWS WAF Dashboards Solution main function")
                .handler("src/lambda_function.handler")
                .logRetention(RetentionDays.ONE_MONTH)
                .role(customizerRole) //todo
                .code(lambdaCodeLocation)
                .runtime(Runtime.PYTHON_3_9)
                .memorySize(128)
                .timeout(Duration.seconds(160))
                .environment(Map.of(
                        "ES_ENDPOINT", props.getOpenSearchDomain().getDomainEndpoint(),
                        "REGION", this.getRegion(),
                        "ACCOUNT_ID", this.getAccount()
                ))
                .build();

        createCustomizer(dashboardsCustomizerLambda, props);

        Function customizerUpdaterLambda = Function.Builder.create(this, "osdfwDashboardsUpdater")
                .architecture(Architecture.ARM_64)
                .description("AWS WAF Dashboards Solution updater function")
                .handler("src/lambda_function.update")
                .logRetention(RetentionDays.ONE_MONTH)
                .role(customizerRole) //todo
                .code(lambdaCodeLocation)
                .runtime(Runtime.PYTHON_3_9)
                .memorySize(128)
                .timeout(Duration.seconds(160))
                .environment(Map.of(
                        "ES_ENDPOINT", props.getOpenSearchDomain().getDomainEndpoint(),
                        "REGION", this.getRegion(),
                        "ACCOUNT_ID", this.getAccount()
                ))
                .build();

        List<Rule> eventRules = createEvents(customizerUpdaterLambda);

        for (Rule rule : eventRules) {
            customizerUpdaterLambda.addPermission(
                    rule.getRuleName().toLowerCase(Locale.ROOT),
                    Permission.builder()
                            .action("lambda:InvokeFunction")
                            .principal(new ServicePrincipal("events.amazonaws.com"))
                            .sourceArn(rule.getRuleArn())
                            .build());
        }
    }

    private List<Rule> createEvents(Function targetLambdaFn) {
        
        Rule newACLForWafV2 = Rule.Builder.create(this, "osdfwCaptureNewAclsWafv2")
                .description("AWS WAF Dashboards Solution - detects new WebACLs and rules for WAFv2.")
                .eventPattern(EventPattern.builder()
                        .source(List.of("aws.wafv2"))
                        .detailType(List.of("AWS API Call via CloudTrail"))
                        .detail(Map.of(
                                "eventSource", List.of("wafv2.amazonaws.com"),
                                "eventName", List.of("CreateWebACL", "CreateRule")
                        ))
                        .build())
                .targets(List.of(LambdaFunction.Builder.create(targetLambdaFn).build()))
                .enabled(true)
                .build();
  
         Rule newACLIDs3Sink = Rule.Builder.create(this, "osdfwCaptureNewAclsS3Sink")
                .description("AWS WAF Dashboards Solution - detects new WebACL ID in logs.")
                .eventPattern(EventPattern.builder()
                        .source(List.of("sink.s3"))
                        .detailType(List.of("S3 Sink"))
                        .detail(Map.of(
                                "eventSource", List.of("sink.lambda"),
                                "eventName", List.of("CreateWebACL")
                        ))
                        .build())
                .targets(List.of(LambdaFunction.Builder.create(targetLambdaFn).build()))
                .enabled(true)
                .build();               

        // todo add conditional parameter to disable waf v1 capabilities
        Rule newACLRulesForWafRegional = Rule.Builder.create(this, "osdfwCaptureNewAclsWafv1Regional")
                .description("AWS WAF Dashboards Solution - detects new WebACLs and rules for WAF Regional.")
                .eventPattern(EventPattern.builder()
                        .source(List.of("aws.waf-regional"))
                        .detailType(List.of("AWS API Call via CloudTrail"))
                        .detail(Map.of(
                                "eventSource", List.of("waf.amazonaws.com"),
                                "eventName", List.of("CreateWebACL", "CreateRule")
                        ))
                        .build())
                .targets(List.of(LambdaFunction.Builder.create(targetLambdaFn).build()))
                .enabled(true)
                .build();

        Rule newACLRulesForWafGlobal = Rule.Builder.create(this, "osdfwCaptureNewAclsWafv1Global")
                .description("AWS WAF Dashboards Solution - detects new WebACLs and rules for WAF Global.")
                .eventPattern(EventPattern.builder()
                        .source(List.of("aws.waf"))
                        .detailType(List.of("AWS API Call via CloudTrail"))
                        .detail(Map.of(
                                "eventSource", List.of("waf-regional.amazonaws.com"),
                                "eventName", List.of("CreateWebACL", "CreateRule")
                        ))
                        .build())
                .targets(List.of(LambdaFunction.Builder.create(targetLambdaFn).build()))
                .enabled(true)
                .build();

        return List.of(newACLRulesForWafRegional, newACLRulesForWafGlobal, newACLForWafV2, newACLIDs3Sink);
    }

    private Role createLambdaRole() {
        //todo too broad
        PolicyStatement policyStatement = PolicyStatement.Builder.create()
                .effect(Effect.ALLOW)
                .actions(List.of(
                        "es:*",
                        //"es:UpdateElasticsearchDomainConfig",
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "events:PutRule",
                        "events:DeleteRule",
                        "lambda:AddPermission",
                        "events:PutTargets",
                        "events:RemoveTargets",
                        "lambda:RemovePermission",
                        "iam:PassRole",
                        "waf:ListWebACLs",
                        "waf-regional:ListWebACLs",
                        "waf:ListRules",
                        "waf-regional:ListRules",
                        "wafv2:ListWebACLs",
                        "s3:*"
                ))
                .resources(List.of("*"))
                .build();

        ManagedPolicy policy = ManagedPolicy.Builder.create(this, "osdfwCustomizerLambdaPolicy")
                .statements(List.of(policyStatement))
                .build();

        return Role.Builder.create(this, "osdfwCustomizerLambdaRole")
                .assumedBy(new ServicePrincipal("lambda.amazonaws.com"))
                .description("AWS WAF Dashboards Lambda role")
                .managedPolicies(List.of(policy))
                .build();

    }

    public void createCustomizer(Function dashboardsCustomizerLambda, StreamStackProps props) {
        CustomResource.Builder.create(this, "osdfwCustomResourceLambda")
                .serviceToken(dashboardsCustomizerLambda.getFunctionArn())
                .removalPolicy(RemovalPolicy.DESTROY)
                .properties(Map.of(
                        "StackName", this.getStackName(),
                        "Region", this.getRegion(),
                        "Host", props.getOpenSearchDomain().getDomainEndpoint(),
                        "AccountID", this.getAccount()
                ))
                .build();
    }
}
