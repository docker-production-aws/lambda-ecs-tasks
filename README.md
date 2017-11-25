# Docker in Production using AWS CloudFormation ECS Task Runner Custom Resource

This repository defines a CloudFormation custom resource Lamdba function called `ecsTasks`, which is included with the Pluralsight course [Docker in Production using Amazon Web Services](https://app.pluralsight.com/library/courses/docker-production-using-amazon-web-services/table-of-contents).

This function is a CloudFormation custom resource that runs ECS tasks and polls the task until successful completion or failure.  The function will report both ECS task failures and any task that exits with a non-zero code as a failure.

## Branches

This repository contains two branches:

- [`master`](https://github.com/docker-production-aws/lambda-ecs-tasks/tree/master) - represents the initial starting state of the repository as viewed in the course.  Specifically this is an empty repository that you are instructed to create in the module **Creating CloudFormation Custom Resources Using AWS Lambda**.

- [`final`](https://github.com/docker-production-aws/lambda-ecs-tasks/tree/final) - represents the final state of the repository after completing all configuration tasks as described in the course material.

> The `final` branch is provided as a convenience in the case you get stuck, or want to avoid manually typing out large configuration files.  In most cases however, you should attempt to configure this repository by following the course material.

To clone this repository and checkout a branch you can simply use the following commands:

```
$ git clone https://github.com/docker-production-aws/packer-ecs.git
...
...
$ git checkout final
Switched to branch 'final'
$ git checkout master
Switched to branch 'master'
```

## Errata

No known issues.

## Further Reading

- [confd Quick Start Guide](https://github.com/kelseyhightower/confd/blob/master/docs/quick-start-guide.md)

## Build Instructions

To complete the build process you need the following tools installed:

- Python 2.7
- PIP package manager
- [AWS CLI](https://aws.amazon.com/cli/)
- [jq](https://stedolan.github.io/jq/)

Any dependencies need to defined in `src/requirements.txt`.  Note that you do not need to include `boto3`, as this is provided by AWS for Python Lambda functions.

To build the function and its dependencies:

`make build`

This will create the necessary dependencies in the `src` folder and create a ZIP package in the `build` folder.  This file is suitable for upload to the AWS Lambda service to create a Lambda function.

```
$ make build
=> Building ecsTasks.zip...
Collecting cfn_lambda_handler (from -r requirements.txt (line 1))
Installing collected packages: cfn-lambda-handler
...
...
Successfully installed cfn-lambda-handler-1.0.0
updating: vendor/cfn_lambda_handler_1.0.0.dist-info/ (stored 0%)
updating: vendor/cfn_lambda_handler.py (deflated 67%)
updating: vendor/cfn_lambda_handler.pyc (deflated 62%)
updating: requirements.txt (stored 0%)
updating: setup.cfg (stored 0%)
updating: ecs_tasks.py (deflated 63%)
=> Built build/ecsTasks.zip
```

### Function Naming

The default name for this function is `ecsTasks` and the corresponding ZIP package that is generated is called `ecsTasks.zip`.

If you want to change the function name, you can either update the `FUNCTION_NAME` setting in the `Makefile` or alternatively configure an environment variable of the same name to override the default function name.

## Publishing the Function

When you publish the function, you are simply copying the built ZIP package to an S3 bucket.  Before you can do this, you must ensure you have created the S3 bucket and your environment is configured correctly with appropriate AWS credentials and/or profiles.

To specify the S3 bucket that the function should be published to, you can either configure the `S3_BUCKET` setting in the `Makefile` or alternatively configure an environment variable of the same name to override the default S3 bucket name.

> [Versioning](http://docs.aws.amazon.com/AmazonS3/latest/dev/Versioning.html) should be enabled on the S3 bucket

To deploy the built ZIP package:

`make publish`

This will upload the built ZIP package to the configured S3 bucket.

> When a new or updated package is published, the S3 object version will be displayed.

### Publish Example

```
$ make publish
...
...
=> Built build/ecsTasks.zip
=> Publishing ecsTasks.zip to s3://123456789012-cfn-lambda...
=> Published to S3 URL: https://s3.amazonaws.com/123456789012-cfn-lambda/ecsTasks.zip
=> S3 Object Version: gyujkgVKoH.NVeeuLYTi_7n_NUburwa4
```

## CloudFormation Usage

This function is designed to be called from a CloudFormation template as a custom resource.

In general you should create a Lambda function per CloudFormation stack and then create custom resources that call the Lambda function.

### Defining the Lambda Function

The following CloudFormation template snippet demonstrates creating the Lambda function, along with supporting CloudWatch Logs and IAM role resources:

> Note this snippet assumes you have an ECS Cluster resource called `ApplicationCluster`, which is used to constrain the IAM privileges assigned to the Lambda function.

```
...
Resources:
  EcsTaskRunnerLogGroup:
    Type: "AWS::Logs::LogGroup"
    DeletionPolicy: "Delete"
    Properties:
      LogGroupName:
        Fn::Sub: /aws/lambda/${AWS::StackName}-ecsTasks
      RetentionInDays: 30
  EcsTaskRunner:
    Type: "AWS::Lambda::Function"
    DependsOn:
      - "EcsTaskRunnerLogGroup"
    Properties:
      Description: 
        Fn::Sub: "${AWS::StackName} ECS Task Runner"
      Handler: "ecs_tasks.handler"
      MemorySize: 128
      Runtime: "python2.7"
      Timeout: 300
      Role: 
        Fn::Sub: ${EcsTaskRunnerRole.Arn}
      FunctionName: 
        Fn::Sub: "${AWS::StackName}-ecsTasks"
      Code:
        S3Bucket: 
          Fn::Sub: "${AWS::AccountId}-cfn-lambda"
        S3Key: "ecsTasks.zip"
        S3ObjectVersion: "gyujkgVKoH.NVeeuLYTi_7n_NUburwa4"
  EcsTaskRunnerRole:
    Type: "AWS::IAM::Role"
    Properties:
      Path: "/"
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
        - Effect: "Allow"
          Principal: {"Service": "lambda.amazonaws.com"}
          Action: [ "sts:AssumeRole" ]
      Policies:
      - PolicyName: "ECSPermissions"
        PolicyDocument:
          Version: "2012-10-17"
          Statement:
          - Sid: "InvokeSelf"
            Effect: "Allow"
            Action:
              - "lambda:InvokeFunction"
            Resource:
              Fn::Sub: "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:${AWS::StackName}-ecsTasks"
          - Sid: "TaskDefinition"
            Effect: "Allow"
            Action:
            - "ecs:DescribeTaskDefinition"
            Resource: "*"
          - Sid: "EcsTasks"
            Effect: "Allow"
            Action:
            - "ecs:DescribeTasks"
            - "ecs:ListTasks"
            - "ecs:RunTask"
            - "ecs:StartTask"
            - "ecs:StopTask"
            - "ecs:DescribeContainerInstances"
            - "ecs:ListContainerInstances"
            Resource: "*"
            Condition:
              ArnEquals:
                ecs:cluster: 
                  Fn::Sub: "arn:aws:ecs:${AWS::Region}:${AWS::AccountId}:cluster/${ApplicationCluster}"
          - Sid: "ManageLambdaLogs"
            Effect: "Allow"
            Action:
            - "logs:CreateLogGroup"
            - "logs:CreateLogStream"
            - "logs:PutLogEvents"
            - "logs:PutRetentionPolicy"
            - "logs:PutSubscriptionFilter"
            - "logs:DescribeLogStreams"
            - "logs:DeleteLogGroup"
            - "logs:DeleteRetentionPolicy"
            - "logs:DeleteSubscriptionFilter"
            Resource: 
              Fn::Sub: "arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/${AWS::StackName}-ecsTasks:*:*"
...
...
```

### Creating Custom Resources that use the Lambda Function

The following custom resource calls the `EcsTaskRunner` Lambda function when the resource is created, updated or deleted:

```
  MigrateTask:
    Type: "Custom::ECSTask"
    Properties:
      ServiceToken:
        Fn::Sub: "${EcsTaskRunner.Arn}"
      Cluster: { "Ref": "ApplicationCluster" }
      TaskDefinition: { "Ref": "ApplicationTaskDefinition" }
      Count: 1              
      Timeout: 1800           # The maximum amount of time to wait for the task to complete - defaults to 290 seconds
      RunOnUpdate: True       # Controls if the task should run for update operations - defaults to True
      UpdateCriteria:         # Specifies criteria to determine if a task update should run
        - Container: app
          EnvironmentKeys:    # List of environment keys to compare.  The task is only run if the environment key value has changed.
            - DB_HOST
      PollInterval: 30        # How often to poll the status of a given task
      Overrides:              # Task definition overrides
        containerOverrides:
          - name: app
            command:
              - bundle
              - exec
              - rake
              - db:migrate
            environment:
              - name: SOME_VAR
                value: SOME_VALUE
      Instances:              # Optional list of container instances to run the task on
        - arn:aws:ecs:us-west-2:012345678901:container-instance/9d8698b5-5477-4b8b-bb63-dfd1e140b0d8

```

The following table describes the various properties you can configure when creating a custom resource that uses this Lambda function:

| Property       | Description                                                                                                                                                                                                                                                                                                                                                                                          | Required | Default Value |
|----------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|---------------|
| ServiceToken   | The ARN of the Lambda function                                                                                                                                                                                                                                                                                                                                                                       | Yes      |               |
| Cluster        | The name of the ECS Cluster to run the task on                                                                                                                                                                                                                                                                                                                                                       | Yes      |               |
| TaskDefinition | The family, family:revision or full ARN of the ECS task definition that the ECS task is executed from.                                                                                                                                                                                                                                                                                               | Yes      |               |
| Count          | The number of task instances to run.  If the Instances property is set, this count value is ignored as one task per instance will be run.  If set to 0, no tasks will be run (even if the Instances property is set).                                                                                                                                                                                | No       | 1             |
| Timeout        | The maximum time in seconds to wait for the task to complete successfully.                                                                                                                                                                                                                                                                                                                           | No       | 290           |
| RunOnUpdate    | Controls if the task should be run for update to the resource.                                                                                                                                                                                                                                                                                                                                       | No       | True          |
| UpdateCriteria | Optional list of criteria used to determine if the task should be run for an update to the resource.   If specified, you must configure the `Container` property as the name of a container in the task definition, and specify a list of environment variable keys using the `EnvironmentKey` property.  If any of the specified environment variable values  have changed, then the task will run. | No       |               |
| Overrides      | Optional task definition overrides to apply to the specified task definition.                                                                                                                                                                                                                                                                                                                        | No       |               |
| Instances      | Optional list of ECS container instances to run the task on.  If specified, you must use the ARN of each ECS container instance.                                                                                                                                                                                                                                                                     | No       |               |
| Triggers       | List of triggers that can be used to trigger updates to this resource, based upon changes to other resources.  This property is ignored by the Lambda function.  