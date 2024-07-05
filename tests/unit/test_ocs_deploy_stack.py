import aws_cdk as core
import aws_cdk.assertions as assertions

from ocs_deploy.ocs_deploy_stack import OcsDeployStack


# example tests. To run these tests, uncomment this file along with the example
# resource in ocs_deploy/ocs_deploy_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = OcsDeployStack(app, "ocs-deploy")
    template = assertions.Template.from_stack(stack)  # noqa: F841


#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
