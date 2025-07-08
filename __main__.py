import pulumi
import pulumi_aws as aws
import pulumi_docker as docker
import base64
import json
import os
import hashlib

# Get region
region = aws.get_region().name

# VPC
vpc = aws.ec2.Vpc("vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_support=True,
    enable_dns_hostnames=True
)

# Public Subnets in 2 AZs
subnet1 = aws.ec2.Subnet("subnet-1",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone=f"{region}a",
    map_public_ip_on_launch=True
)

subnet2 = aws.ec2.Subnet("subnet-2",
    vpc_id=vpc.id,
    cidr_block="10.0.2.0/24",
    availability_zone=f"{region}b",
    map_public_ip_on_launch=True
)

# Internet Gateway & Routing
igw = aws.ec2.InternetGateway("igw", vpc_id=vpc.id)
route_table = aws.ec2.RouteTable("routeTable", vpc_id=vpc.id, routes=[{
    "cidr_block": "0.0.0.0/0",
    "gateway_id": igw.id
}])

aws.ec2.RouteTableAssociation("routeTableAssoc1", subnet_id=subnet1.id, route_table_id=route_table.id)
aws.ec2.RouteTableAssociation("routeTableAssoc2", subnet_id=subnet2.id, route_table_id=route_table.id)

# Security Groups
sg = aws.ec2.SecurityGroup("flask-sg",
    vpc_id=vpc.id,
    ingress=[{"protocol": "tcp", "from_port": 5000, "to_port": 5000, "cidr_blocks": ["0.0.0.0/0"]}],
    egress=[{"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]}]
)

rds_sg = aws.ec2.SecurityGroup("rds-sg",
    vpc_id=vpc.id,
    ingress=[{"protocol": "tcp", "from_port": 5432, "to_port": 5432, "security_groups": [sg.id]}],
    egress=[{"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]}]
)

# RDS Subnet Group
rds_subnet_group = aws.rds.SubnetGroup("rds-subnet-group",
    subnet_ids=[subnet1.id, subnet2.id],
    tags={"Name": "rds-subnet-group"}
)

# RDS Database
rds = aws.rds.Instance("patient-db",
    allocated_storage=20,
    engine="postgres",
    engine_version="15.8",
    instance_class="db.t3.micro",
    db_name="patients",
    username="postgres",
    password="postgres123",
    db_subnet_group_name=rds_subnet_group.name,
    vpc_security_group_ids=[rds_sg.id],
    publicly_accessible=True,
    skip_final_snapshot=True
)

# ECR Repository
repo = aws.ecr.Repository("flask-repo")

# Docker Image Build & Push
auth = aws.ecr.get_authorization_token()
decoded = base64.b64decode(auth.authorization_token).decode()
username, password = decoded.split(":")

hash_data = b""
for file in ["app.py", "requirements.txt"]:
    if os.path.exists(file):
        with open(file, "rb") as f:
            hash_data += f.read()

app_hash = hashlib.sha256(hash_data).hexdigest()[:8]
image_name = pulumi.Output.secret(
    repo.repository_url.apply(lambda url: f"{url}:{app_hash}")
)

image = docker.Image(
    "flask-app",
    build=docker.DockerBuildArgs(context="."),
    image_name=image_name,
    registry=docker.RegistryArgs(
        server=repo.repository_url,
        username=username,
        password=password,
    )
)

# ECS Cluster
cluster = aws.ecs.Cluster("flask-cluster")

# IAM Role
role = aws.iam.Role("ecsTaskExecRole",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    })
)

aws.iam.RolePolicyAttachment("ecsTaskExecRolePolicy",
    role=role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
)

# CloudWatch Logs
log_group = aws.cloudwatch.LogGroup("flask-logs", retention_in_days=1)

# ECS Task Definition with RDS injected
task_def = aws.ecs.TaskDefinition("flask-task",
    family="flask-task",
    cpu="256",
    memory="512",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    execution_role_arn=role.arn,
    container_definitions=pulumi.Output.all(image_name, log_group.name, region, rds.address).apply(
        lambda args: json.dumps([{
            "name": "flask-app",
            "image": args[0],
            "portMappings": [{"containerPort": 5000}],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": args[1],
                    "awslogs-region": args[2],
                    "awslogs-stream-prefix": "flask"
                }
            },
            "environment": [
                {"name": "DB_HOST", "value": args[3]},
                {"name": "DB_NAME_PG", "value": "patients"},
                {"name": "DB_USER", "value": "postgres"},
                {"name": "DB_PASSWORD", "value": "postgres123"}
            ]
        }])
    )
)

# ECS Service
service = aws.ecs.Service("flask-service",
    cluster=cluster.arn,
    desired_count=1,
    launch_type="FARGATE",
    task_definition=task_def.arn,
    network_configuration={
        "assignPublicIp": True,
        "subnets": [subnet1.id, subnet2.id],
        "security_groups": [sg.id]
    }
)

# Outputs
pulumi.export("repo_url", repo.repository_url)
pulumi.export("cluster_name", cluster.name)
pulumi.export("service_name", service.name)
pulumi.export("rds_endpoint", rds.address)
pulumi.export("image_tag_used", image_name)
