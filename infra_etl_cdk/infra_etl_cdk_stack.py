from aws_cdk import (
    aws_ec2 as ec2,
    Stack,
    Fn,
)
from constructs import Construct

import logging


class VpcPublicConstruct(Stack):

    def __init__(
        self,
        scope: Construct,
        stack_id: str,
        cidr: str = None,
        cidr_mask: int = None,
        max_azs: int = 3,
        vpc: ec2.Vpc | str = None,
        vpc_arguments: dict = None,
        associate_network_acl: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(scope, stack_id, **kwargs)

        if cidr is not None and cidr_mask is not None:
            self.vpc = self.vpc_creation(cidr, cidr_mask, max_azs)
        elif vpc is not None:
            if vpc_arguments is None:
                vpc_arguments = dict()
            else:
                assert isinstance(vpc_arguments, dict), TypeError(
                    f'Argument "vpc_arguments" must be of type dict; got {type(vpc_arguments)} instead'
                )
            self.vpc = self.vpc_linking(vpc, **vpc_arguments)
        else:
            raise ValueError("Either 'cidr' and 'cidr_mask' or 'vpc' must be provided.")

        # For existing resources this will remove the existing NetworkACL association
        if associate_network_acl:
            logging.warning("Associating Subnets in VPC with a NetworkACL")
            ec2.NetworkAcl(
                self,
                "RedshiftSubnetsAcl",
                vpc=self.vpc,
                subnet_selection=self.vpc.select_subnets(),
            )

    def vpc_creation(self, cidr: str, cidr_mask: int, max_azs: int) -> ec2.Vpc:
        ## VPC Parameters Check
        assert isinstance(cidr, str), TypeError(
            f'Argument "cidr" must be of type str; got {type(cidr)} instead'
        )
        assert isinstance(max_azs, int), TypeError(
            f'Argument "max_azs" must be of type int; got {type(max_azs)} instead'
        )
        # Change if required
        assert (
            max_azs >= 3
        ), "Max AZs must be grater than or equal to 3. Us east 1 requirement for Redshift. "
        vpc = ec2.Vpc(
            self,
            "RedshiftVpc",
            ip_addresses=ec2.IpAddresses.cidr(cidr),
            max_azs=max_azs,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    cidr_mask=cidr_mask,
                    name=f"private{i}",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                )
                for i in range(max_azs)
            ],
        )
        return vpc

    def vpc_linking(self, vpc: ec2.Vpc | str, **kwargs):
        """
        VPC linking for security group creation
        Creates a IVpc instance as proxy to specified VPC
        :param vpc: str or ec2.Vpc
        :param vpc_subnets: list of ec2.SubnetSelection
        :param kwargs: Dictionary with keys as arguments for "ec2.Vpc.from_vpc_attributes"
        :return: ec2.Vpc
        """
        ## VPC Parameters Check
        assert isinstance(vpc, (ec2.Vpc, str)), TypeError(
            f'Argument "vpc" must be of type (ec2.Vpc, str); got {type(vpc)} instead'
        )
        if isinstance(vpc, str):
            azs = Fn.get_azs()
            vpc = ec2.Vpc.from_vpc_attributes(
                self, "ExistingVPC", availability_zones=azs, vpc_id=vpc, **kwargs
            )
        assert vpc.select_subnets().subnets is not None, ValueError(
            f'Argument "vpc" must have subnets.'
        )
        return vpc

    def network_acl(
        self, vpc: ec2.Vpc, vpc_subnets: ec2.SubnetSelection
    ) -> ec2.NetworkAcl:
        return ec2.NetworkAcl(
            self,
            "RedshiftSubnetsAcl",
            vpc=vpc,
            subnet_selection=vpc_subnets,
        )

    def to_see(self, ingress_sources: list):
        ## Subnets
        db_subnet_group = rds.SubnetGroup(
            self,
            id="DatabaseSubnetGroup",
            vpc=vpc,
            description=f"Subnet group for data base",
            subnet_group_name=f"{self.stack_name}subnet-group_db",
            vpc_subnets=ec2.SubnetSelection(
                one_per_az=True,
                subnets=vpc_subnets,
            ),
        )

        tcp3306 = ec2.Port(
            protocol=ec2.Protocol("TCP"),
            from_port=3306,
            to_port=3306,
            string_representation="tcp3306 PostgreSQL",
        )
        tcp5432 = ec2.Port(
            protocol=ec2.Protocol("TCP"),
            from_port=5432,
            to_port=5432,
            string_representation="tcp5432 PostgreSQL",
        )

        ## Database Security Group
        dbsg = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            description="Security group for Vector Aurora database.",
            security_group_name=self.stack_id + " Database",
        )
        dbsg.add_ingress_rule(
            peer=dbsg, connection=ec2.Port.all_tcp(), description="All referencing rule"
        )
        # dbsg.add_egress_rule(
        #     peer=ec2.Peer.ipv4("0.0.0.0/0"), connection=allAll, description="all out"
        # )

        for ingress_source in ingress_sources:
            dbsg.add_ingress_rule(
                peer=ingress_source,
                connection=tcp5432,
                description="tcp5432 PostgreSQL",
            )
            dbsg.add_ingress_rule(
                peer=ingress_source,
                connection=tcp3306,
                description="tcp3306 PostgreSQL",
            )

        return vpc, vpc_subnets, dbsg, db_subnet_group


class InfraEtlCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # example resource
        # queue = sqs.Queue(
        #     self, "InfraEtlCdkQueue",
        #     visibility_timeout=Duration.seconds(300),
        # )
