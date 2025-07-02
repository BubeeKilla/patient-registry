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
vpc = aws.ec2.Vpc("vpc", cidr_block="10.0.0.0/16")

# Public Subnet
subnet = aws.ec2.Subnet("subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    map_public_ip_on_launch=True
)

# Internet Gateway & Routing
igw = aws.ec2.InternetGateway("igw", vpc_id=vpc.id)
route_table = aws.ec2.RouteTable("routeTable", vpc_id=vpc.id, routes=[{
    "cidr_block": "0.0.0.0/0",
    "gateway_id": igw.id
}])
aws.ec2.RouteTableAssociation("routeTableAssoc", subnet_id=subnet.id, route_table_id=route_table.id)

# Security Group (Expose port 5000)
sg = aws.ec2.SecurityGroup("flask-sg",
    vpc_id=vpc.id,
    ingress=[{"protocol": "tcp", "from_port": 5000, "to_port": 5000, "cidr_blocks": ["0.0.0.0/0"]}],
    egress=[{"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]}]
)

# ECR Repository
repo = aws.ecr.Repository("flask-repo")

# Docker Image Build & Push
auth = aws.ecr.get_authorization_token()
decoded = base64.b64decode(auth.authorization_token).decode()
username, password = decoded.split(":")

# Hash app files to force image rebuilds when code changes
hash_data = b""
for file in ["app.py", "requirements.txt"]:
    if os.path.exists(file):
        with open(file, "rb") as f:
            hash_data += f.read()

app_hash = hashlib.sha256(hash_data).hexdigest()[:8]

# Correct way to build image_name with apply
image_name = repo.repository_url.apply(lambda url: f"{url}:{app_hash}")

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

# Task Execution Role
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

# Task Definition
task_def = aws.ecs.TaskDefinition("flask-task",
    family="flask-task",
    cpu="256",
    memory="512",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    execution_role_arn=role.arn,
    container_definitions=pulumi.Output.all(image.image_name, log_group.name, region).apply(
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
            }
        }])
    )
)

# Fargate Service
service = aws.ecs.Service("flask-service",
    cluster=cluster.arn,
    desired_count=1,
    launch_type="FARGATE",
    task_definition=task_def.arn,
    network_configuration={
        "assignPublicIp": True,
        "subnets": [subnet.id],
        "security_groups": [sg.id]
    }
)

# Outputs
pulumi.export("repo_url", repo.repository_url)
pulumi.export("cluster_name", cluster.name)
pulumi.export("service_name", service.name)
