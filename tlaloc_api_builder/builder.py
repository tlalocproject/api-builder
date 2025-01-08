import os
import json
import copy
import time
import boto3
import hashlib

http_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "ANY"]


class builder:

    def __init__(self, config):

        # Initialize the config dictionary
        self.config = {}

        # Checking if the config is a dictionary
        if not isinstance(config, dict):
            raise ValueError("Config must be a dictionary")

        # Checking the config.path parameter
        if (
            not config.get("path")
            or not isinstance(config["path"], str)
            or not config["path"].strip()
            or not os.path.exists(config["path"])
        ):
            raise ValueError(
                "Config must be a non empty string that corresponds to an existing path"
            )
        self.config["path"] = config["path"]
        self.config["path_temporal"] = os.path.join(
            os.path.dirname(self.config["path"]),
            "." + os.path.basename(self.config["path"]),
        )

        # Checking the config.name parameter
        if (
            not config.get("name")
            or not isinstance(config["name"], str)
            or not config["name"].strip()
        ):
            raise ValueError("Config must be a non empty string parameter name")
        self.config["name"] = config["name"]

        # Checking the deployer parameter
        if (
            not config.get("deployer")
            or not isinstance(config["deployer"], str)
            or not config["deployer"].strip()
        ):
            raise ValueError(
                "Config must have a non empty string parameter named deployer"
            )
        self.config["deployer"] = config["deployer"]

        # Checking the profile parameter
        if (
            not config.get("profile")
            or not isinstance(config["profile"], str)
            or not config["profile"].strip()
        ):
            raise ValueError("Config must be a non empty string parameter profile")
        self.config["profile"] = config["profile"]

        # Checking the region parameter
        if (
            not config.get("region")
            or not isinstance(config["region"], str)
            or not config["region"].strip()
        ):
            raise ValueError("Config must be a non empty string parameter region")
        self.config["region"] = config["region"]

        # Checking the bucket parameter
        if (
            not config.get("bucket")
            or not isinstance(config["bucket"], str)
            or not config["bucket"].strip()
        ):
            raise ValueError("Config must be a non empty string parameter bucket")
        self.config["bucket"] = config["bucket"]

        # Checking the stage parameter
        if (
            not config.get("stage")
            or not isinstance(config["stage"], str)
            or not config["stage"].strip()
        ):
            raise ValueError("Config must be a non empty string parameter stage")
        self.config["stage"] = config["stage"]

        # Checking the stack parameter
        if (
            not config.get("stack")
            or not isinstance(config["stack"], str)
            or not config["stack"].strip()
        ):
            raise ValueError("Config must be a non empty string parameter stack")
        self.config["stack"] = config["stack"]
        self.config["stack_hash"] = self._get_hash(
            f"{self.config["deployer"]}/{self.config["stack"]}"
        )

        # Storing timestamp
        self.config["timestamp"] = int(time.time())

    def build(self):

        # Initialize the building dictionary
        self.building = {}

        # Reporting the configuration in use
        print(
            "Building API with config:\n    {}".format(
                json.dumps(self.config, indent=4).replace("\n", "\n    ")
            )
        )

        # Obtaining the file tree
        self._get_filetree()
        print(
            "File Tree:\n    {}".format(
                json.dumps(self.building["filetree"], indent=4).replace("\n", "\n    ")
            )
        )

        # API structure
        self._get_structure()
        print(
            "API Structure:\n    {}".format(
                json.dumps(self.building["structure"], indent=4).replace("\n", "\n    ")
            )
        )

        # Initialize methods dictionary
        self._get_methods()
        print(
            "API Methods Summary:\n    {}".format(
                json.dumps(self.building["methods"], indent=4).replace("\n", "\n    ")
            )
        )

        # Making temporal tree for lambda zips
        print("Making temporal tree for lambda zips")
        self._make_temporal_tree()

        # Copying files to temporal tree
        print("Copying files to temporal tree")
        self._copy_temporal_files()

        # Preparing temporal files
        print("Preparing temporal files")
        self._prepare_temporal_files()

        # Ziping the files
        print("Zipping the files")
        self._zip_files()

        # Make the method template
        print("Making the methods template")
        self._make_methods_template()

        # Make the API template
        print("Making the API template")
        self._make_api_template()

    def _get_filetree(self):

        # Initialize the filetree dictionary
        filetree = {}

        # Walk through the directory and build the filetree
        for root, dirs, files in os.walk(self.config["path"]):

            # Create a nested dictionary for each directory
            directory = filetree
            for part in os.path.relpath(root, self.config["path"]).split(os.sep):
                if part != ".":
                    directory = directory.setdefault(part, {})

            # Add files to the current directory
            directory.update({file: None for file in files})

        # Store the filetree in the building dictionary
        self.building["filetree"] = filetree

    def _get_structure(self):

        # Make a deep copy of the filetree
        filetree_copy = copy.deepcopy(self.building["filetree"])

        # Remove all the null values from the filetree
        def remove_null_keys(d):
            if not isinstance(d, dict):
                return d
            return {k: remove_null_keys(v) for k, v in d.items() if v is not None}

        filetree_copy = remove_null_keys(filetree_copy)

        # Check if all empty dictionaries in the filetree have a key that is a valid HTTP method
        def check_http_methods(d):
            if not isinstance(d, dict):
                return
            for k, v in d.items():
                if not v:
                    if k not in http_methods:
                        raise ValueError("Invalid HTTP method: {}".format(k))
                else:
                    check_http_methods(v)

        check_http_methods(filetree_copy)

        # Store the structure in the building dictionary
        self.building["structure"] = filetree_copy

    def _get_methods(self):

        # Initialize the methods dictionary
        self.building["methods"] = {}

        # Get the methods from the structure
        def get_methods(d, path):
            for token in d:
                if token in http_methods:
                    self.building["methods"][f"{path}/{token}"] = {
                        "path_temporal": f"{path}/{token}".replace(
                            self.config["path"], self.config["path_temporal"], 1
                        ),
                        "hash": self._get_hash(
                            f"{self.config["deployer"]}/{path}/{token}"
                        ),
                        "method": token,
                    }
                    self.building["methods"][f"{path}/{token}"][
                        "zip"
                    ] = f"{self.config["timestamp"]}-{self.building['methods'][f"{path}/{token}"]['hash']}.zip"
                else:
                    get_methods(d[token], f"{path}/{token}")

        get_methods(self.building["structure"], self.config["path"])

    def _get_hash(self, string):

        # Return the MD5 hash of the string
        return hashlib.md5(string.encode("utf-8")).hexdigest()

    def _make_temporal_tree(self):

        # Remove the temporal directory if it exists
        if os.path.exists(self.config["path_temporal"]):
            os.system(f"rm -rf {self.config['path_temporal']}")

        # Create the temporal directory
        os.makedirs(self.config["path_temporal"])

        # Create the temporal directories for the methods
        for method in self.building["methods"]:
            os.makedirs(
                self.building["methods"][method]["path_temporal"], exist_ok=True
            )

    def _copy_temporal_files(self):

        # Copy the files to the temporal directories for each method
        for method in self.building["methods"]:
            os.system(
                f"cp -r {method}/* {self.building['methods'][method]['path_temporal']}"
            )

    def _prepare_temporal_files(self):

        # Apply preparation rules to the files
        for method in self.building["methods"]:

            # for each file in the method directory
            for root, dirs, files in os.walk(
                self.building["methods"][method]["path_temporal"]
            ):
                for file in files:
                    if file.endswith(".mjs"):
                        self._clean_mjs(os.path.join(root, file))

    def _clean_mjs(self, file_path):

        # Initialize the file_clean string and the rules list
        file_clean = ""
        rules = []

        # Read the file and apply the rules
        with open(file_path, "r") as f:
            for line in f:
                line_strip = line.strip()
                if line_strip.startswith("//// IF"):
                    line_split = line_strip.split(" ")
                    rule = [line_split[2], "==", line_split[3]]
                    if rule in rules:
                        raise ValueError("Rule is already in use")
                    rules.append(rule)
                elif line_strip.startswith("//// ENDIF"):
                    if len(rules) == 0:
                        raise ValueError("No rule to close")
                    rules.pop()
                else:
                    write = True
                    for rule in rules:
                        if rule[1] == "==" and self.config[rule[0]] == rule[2]:
                            continue
                        else:
                            write = False
                            break
                    if write:
                        file_clean += line

        # Write the cleaned file
        with open(file_path, "w") as f:
            f.write(file_clean)

    def _zip_files(self):

        # Zip the files for each method
        for method in self.building["methods"]:
            os.system(
                f"cd {self.building['methods'][method]["path_temporal"]} && zip -r {self.building['methods'][method]['zip']} * >/dev/null 2>&1"
            )

    def _make_methods_template(self):

        # Itereate over the methods
        for method in self.building["methods"]:

            # Creating method short reference
            method = self.building["methods"][method]

            method["template"] = {
                "AWSTemplateFormatVersion": "2010-09-09",
                "Parameters": {
                    "parGateway": {"Type": "String"},
                    "parResourceid": {"Type": "String"},
                },
                "Resources": {
                    f"{method["hash"]}Method": {
                        "Type": "AWS::ApiGateway::Method",
                        "Properties": {
                            "AuthorizationType": "NONE",
                            "HttpMethod": method["method"],
                            "ResourceId": {"Ref": "parResourceid"},
                            "RestApiId": {"Ref": "parGateway"},
                            "Integration": {
                                "Type": "AWS_PROXY",
                                "IntegrationHttpMethod": "POST",
                                "Uri": {
                                    "Fn::Sub": "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${<<id>>function.Arn}/invocations"
                                },
                            },
                        },
                    },
                    f"{method["hash"]}Role": {
                        "Type": "AWS::IAM::Role",
                        "Properties": {
                            "AssumeRolePolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Principal": {
                                            "Service": "lambda.amazonaws.com"
                                        },
                                        "Action": "sts:AssumeRole",
                                    }
                                ],
                            },
                            "Policies": [
                                {
                                    "PolicyName": "LambdaExecutionPolicy",
                                    "PolicyDocument": {
                                        "Version": "2012-10-17",
                                        "Statement": [
                                            {
                                                "Effect": "Allow",
                                                "Action": [
                                                    "logs:CreateLogGroup",
                                                    "logs:CreateLogStream",
                                                    "logs:PutLogEvents",
                                                ],
                                                "Resource": "arn:aws:logs:*:*:*",
                                            },
                                            {
                                                "Effect": "Allow",
                                                "Action": [
                                                    "xray:PutTraceSegments",
                                                    "xray:PutTelemetryRecords",
                                                ],
                                                "Resource": "*",
                                            },
                                        ],
                                    },
                                }
                            ],
                            "ManagedPolicyArns": [
                                "arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"
                            ],
                        },
                    },
                    f"{method["hash"]}Function": {
                        "Type": "AWS::Lambda::Function",
                        "Properties": {
                            "FunctionName": method["hash"],
                            "Handler": {"Fn::Sub": f"{method["method"]}.handler"},
                            "Role": {"Fn::GetAtt": f"{method["hash"]}Role.Arn"},
                            "Runtime": "nodejs20.x",
                            "Timeout": 10,
                            "MemorySize": 256,
                            "TracingConfig": {"Mode": "Active"},
                            "Code": {
                                "S3Bucket": self.config["bucket"],
                                "S3Key": method["zip"],
                            },
                        },
                    },
                    f"{method["hash"]}Invoke": {
                        "Type": "AWS::Lambda::Permission",
                        "Properties": {
                            "Action": "lambda:InvokeFunction",
                            "FunctionName": {
                                "Fn::GetAtt": f"{method["hash"]}Function.Arn"
                            },
                            "Principal": "apigateway.amazonaws.com",
                        },
                    },
                },
            }

            # Create the template file
            with open(
                f"{method["path_temporal"]}/{self.config["timestamp"]}-{method["hash"]}.json",
                "w",
            ) as f:
                f.write(json.dumps(method["template"], indent=4, sort_keys=True))

    def _make_api_template(self):

        # Initialize the depends list
        dependence = ["apiGateway"]
        for method in self.building["methods"]:
            dependence.append(f"{self.building['methods'][method]['hash']}")

        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                "apiGateway": {
                    "Type": "AWS::ApiGateway::RestApi",
                    "Properties": {
                        "Name": self.config["name"],
                        "Parameters": {
                            "endpointConfigurationTypes": {
                                "Type": "String",
                                "default": "REGIONAL",
                            },
                        },
                    },
                },
                f"apiGatewayDeployment{self.config["timestamp"]}": {
                    "Type": "AWS::ApiGateway::Deployment",
                    "Properties": {
                        "RestApiId": {"Ref": "apiGateway"},
                    },
                    "DependsOn": dependence,
                },
                "apiGatewayStage": {
                    "Type": "AWS::ApiGateway::Stage",
                    "Properties": {
                        "RestApiId": {"Ref": "apiGateway"},
                        "DeploymentId": {
                            "Ref": f"apiGatewayDeployment{self.config["timestamp"]}"
                        },
                        "tracingEnabled": True,
                        "methodSettings": [
                            {
                                "DataTraceEnabled": True,
                                "HttpMethod": "*",
                                "LoggingLevel": "INFO",
                                "ResourcePath": "/*",
                            }
                        ],
                        "StageName": self.config["stage"],
                    },
                    "DependsOn": [f"apiGatewayDeployment{self.config["timestamp"]}"],
                },
            },
            "Outputs": {
                "apiId": {
                    "Value": {"Ref": "apiGateway"},
                },
            },
        }

        for method in self.building["methods"]:
            template["Resources"][self.building["methods"][method]["hash"]] = {
                "Type": "AWS::CloudFormation::Stack",
                "Properties": {
                    "TemplateURL": f"{self.building['methods'][method]['path_temporal']}/{self.config["timestamp"]}-{self.building['methods'][method]['hash']}.json",
                    "Parameters": {
                        "parGateway": {"Ref": "apiGateway"},
                        "parResourceid": {"Fn::GetAtt": "apiGateway.RootResourceId"},
                    },
                },
            }

        # Create the template file
        with open(
            f"{self.config["path_temporal"]}/{self.config["timestamp"]}-{self.config["stack_hash"]}.json",
            "w",
        ) as f:
            f.write(json.dumps(template, indent=4, sort_keys=True))

    def deploy(self):

        # Create the aws session
        self.aws = boto3.Session(profile_name=self.config["profile"])

        # Uploading the files to S3
        print("Uploading the files to S3")
        self._upload_files()

        # Deploying clouformation
        print("Deploying clouformation")
        self._deploy_cloudformation()

        # Delete the pointer to the aws session - No need to close it
        del self.aws

    def _upload_files(self):

        # Create the S3 client
        s3_client = self.aws.client("s3", region_name=self.config["region"])

        # For each method, upload the zip file to S3
        for method in self.building["methods"]:
            s3_client.upload_file(
                os.path.join(
                    self.building["methods"][method]["path_temporal"],
                    self.building["methods"][method]["zip"],
                ),
                self.config["bucket"],
                self.building["methods"][method]["zip"],
            )
            s3_client.upload_file(
                os.path.join(
                    self.building["methods"][method]["path_temporal"],
                    self.building["methods"][method]["json"],
                ),
                self.config["bucket"],
                self.building["methods"][method]["json"],
            )

        # Upload the API template to S3
        s3_client.upload_file(
            f"{self.config["path_temporal"]}/{self.config["timestamp"]}-{self.config["stack_hash"]}.json",
            self.config["bucket"],
            f"{self.config["timestamp"]}-{self.config["stack_hash"]}.json",
        )

        # Close the S3 client
        s3_client.close()

    def _deploy_cloudformation(self):

        # Create the CloudFormation client
        cloudformation_client = self.aws.client(
            "cloudformation", region_name=self.config["region"]
        )

        # Create the stack
        cloudformation_client.create_stack(
            StackName=self.config["stack"],
            TemplateURL=f"https://{self.config["bucket"]}.s3.amazonaws.com/{self.config["timestamp"]}-{self.config["stack_hash"]}.json",
            Capabilities=["CAPABILITY_NAMED_IAM"],
        )

        # Close the CloudFormation client
        cloudformation_client.close()
