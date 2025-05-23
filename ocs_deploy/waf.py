﻿# ocs_deploy/stacks/waf.py
from aws_cdk import Stack, RemovalPolicy, aws_wafv2 as wafv2, aws_logs as logs, aws_iam as iam, CfnOutput
from constructs import Construct
from ocs_deploy.config import OCSConfig

class WAFStack(Stack):
    """
    Represents a CDK stack for deploying a WAF Web ACL associated with an Application Load Balancer.
    Includes AWS Managed Rules and rate limiting in count mode, with logging to CloudWatch.
    """

    def __init__(
        self,
        scope: Construct,
        config: OCSConfig,
        load_balancer_arn: str,
        **kwargs
    ) -> None:
        super().__init__(
            scope, config.stack_name("waf"), env=config.cdk_env(), **kwargs
        )
        self.config = config

        # Define the Web ACL
        self.web_acl = wafv2.CfnWebACL(
            self,
            "DjangoWebACL",
            name=config.make_name("DjangoWAF"),
            scope="REGIONAL",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=config.make_name("DjangoWAFMetrics"),
                sampled_requests_enabled=True,
            ),
            rules=[
                # Rule 1: AWS Managed Common Rule Set (Count mode)
                wafv2.CfnWebACL.RuleProperty(
                    name="AWSManagedCommonRuleSet",
                    priority=0,
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesCommonRuleSet",
                        )
                    ),
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(count={}),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name=config.make_name("CommonRuleSetMetrics"),
                        sampled_requests_enabled=True,
                    ),
                ),
                # Rule 2: Rate Limiting (Count mode)
                wafv2.CfnWebACL.RuleProperty(
                    name="RateLimitRule",
                    priority=1,
                    statement=wafv2.CfnWebACL.StatementProperty(
                        rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                            limit=2000,
                            aggregate_key_type="IP",
                        )
                    ),
                    action=wafv2.CfnWebACL.RuleActionProperty(count={}),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name=config.make_name("RateLimitMetrics"),
                        sampled_requests_enabled=True,
                    ),
                ),
            ],
        )

        # Associate with the ALB
        wafv2.CfnWebACLAssociation(
            self,
            "WAFAssociation",
            web_acl_arn=self.web_acl.attr_arn,
            resource_arn=load_balancer_arn,
        )

        # Create a CloudWatch Log Group for WAF logs with the required prefix
        log_group = logs.LogGroup(
            self,
            "WAFLogGroup",
            log_group_name=f"aws-waf-logs-{config.make_name('waf-logs')}",
            retention=logs.RetentionDays.TWO_YEARS,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Add a resource policy to allow WAF to write logs
        log_group.add_to_resource_policy(
            statement=iam.PolicyStatement(
                actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                principals=[iam.ServicePrincipal("wafv2.amazonaws.com")],
                resources=[log_group.log_group_arn],
            )
        )

        # Add WAF Logging Configuration
        logging_config = wafv2.CfnLoggingConfiguration(
            self,
            "WAFLoggingConfig",
            resource_arn=self.web_acl.attr_arn,
            log_destination_configs=[log_group.log_group_arn.replace(":*", "")],
        )

        # Ensure the log group policy is applied before the logging configuration
        logging_config.node.add_dependency(log_group)

        # Output the Web ACL ARN
        CfnOutput(
            self,
            config.make_name("WebACLArn"),
            value=self.web_acl.attr_arn,
            description="ARN of the WAF Web ACL",
        )

        # Output the Log Group ARN
        CfnOutput(
            self,
            config.make_name("WAFLogGroupArn"),
            value=log_group.log_group_arn,
            description="ARN of the WAF Log Group",
        )