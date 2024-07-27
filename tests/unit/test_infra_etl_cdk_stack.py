import aws_cdk as core
import aws_cdk.assertions as assertions

from infra_etl_cdk.infra_etl_cdk_stack import InfraEtlCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in infra_etl_cdk/infra_etl_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = InfraEtlCdkStack(app, "infra-etl-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
