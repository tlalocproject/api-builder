import os
import json
import copy
import time
import boto3

from tlaloc_commons import commons  # type: ignore
from swagger_ui_bundle import swagger_ui_path


class builder:
    """
    Class to build and deploy an API

    Parameters:
        config (dict): A dictionary with the following parameters:
            path (str): The path to the API source files
            name (str): The name of the API
            deployer (str): The name of the deployer
            provider (str): The provider of the API if set to aws, the following parameters are required:

                aws_profile (str): The AWS profile to use
                aws_region (str): The AWS region to deploy the API
                aws_bucket (str): The AWS bucket to store the API files
                aws_stage (str): The AWS stage to deploy the API
                aws_stack (str): The AWS stack name to deploy the API

    Raises:
        ValueError: If the config parameter is not a dictionary
        ValueError: If the config.path parameter is not a non empty string that corresponds to an existing path
        ValueError: If the config.path parameter does not contain a folder named "API"
        ValueError: If the config.name parameter is not a non empty string
        ValueError: If the config.deployer parameter is not a non empty string
        ValueError: If the config.provider parameter is not a non empty string
        ValueError: If the config.aws_profile parameter is not a non empty string
        ValueError: If the config.aws_region parameter is not a non empty string
        ValueError: If the config.aws_bucket parameter is not a non empty string
        ValueError: If the config.aws_stage parameter is not a non empty string
        ValueError: If the config.aws_stack parameter is not a non empty string
        ValueError: If the provider parameter is not "aws"
    """

    def __init__(self, config):

        # Initialize the config dictionary
        self.config = {}
        self.built = False
        self.deployed = False

        # Checking common config parameters #######################################

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
        if "API" not in os.listdir(config["path"]):
            raise ValueError('The path must contain a folder named "API"')
        self.config["path"] = config["path"]
        self.config["path_sources"] = os.path.join(self.config["path"], "API")
        self.config["path_temporal"] = os.path.join(
            os.path.dirname(self.config["path"]),
            "." + os.path.basename(self.config["path_sources"]),
        )
        self.config["path_documentation"] = os.path.join(
            os.path.dirname(self.config["path"]), "docs"
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

        # Checking the provider parameter
        if (
            not config.get("provider")
            or not isinstance(config["provider"], str)
            or not config["provider"].strip()
        ):
            raise ValueError(
                "Config must have a non empty string parameter named provider"
            )
        self.config["provider"] = config["provider"]

        # Checking the version parameter
        if config.get("version") and not isinstance(config["version"], str):
            raise ValueError("Config must have a non empty string for version")
        self.config["version"] = config["version"]

        # Checking the description parameter
        if config.get("description") and not isinstance(config["description"], str):
            raise ValueError("Config must have a non empty string for description")
        self.config["description"] = config["description"]

        # Checking the title parameter
        if config.get("title") and not isinstance(config["title"], str):
            raise ValueError("Config must have a non empty string for title")
        self.config["title"] = config["title"]

        # Storing timestamp
        self.config["timestamp"] = int(time.time())

        # Checking the AWS deployment parameters ##################################
        if self.config["provider"] == "aws":

            # Checking the aws_profile parameter
            if (
                not config.get("aws_profile")
                or not isinstance(config["aws_profile"], str)
                or not config["aws_profile"].strip()
            ):
                raise ValueError(
                    "Config must be a non empty string parameter aws_profile"
                )
            self.config["aws_profile"] = config["aws_profile"]

            # Checking the aws_region parameter
            if (
                not config.get("aws_region")
                or not isinstance(config["aws_region"], str)
                or not config["aws_region"].strip()
            ):
                raise ValueError(
                    "Config must be a non empty string parameter aws_region"
                )
            self.config["aws_region"] = config["aws_region"]

            # Checking the aws_bucket parameter
            if (
                not config.get("aws_bucket")
                or not isinstance(config["aws_bucket"], str)
                or not config["aws_bucket"].strip()
            ):
                raise ValueError(
                    "Config must be a non empty string parameter aws_bucket"
                )
            self.config["aws_bucket"] = config["aws_bucket"]

            # Checking the aws_stage parameter
            if (
                not config.get("aws_stage")
                or not isinstance(config["aws_stage"], str)
                or not config["aws_stage"].strip()
            ):
                raise ValueError(
                    "Config must be a non empty string parameter aws_stage"
                )
            self.config["aws_stage"] = config["aws_stage"]

            # Checking the aws_stack parameter
            if (
                not config.get("aws_stack")
                or not isinstance(config["aws_stack"], str)
                or not config["aws_stack"].strip()
            ):
                raise ValueError(
                    "Config must be a non empty string parameter aws_stack"
                )
            self.config["aws_stack"] = config["aws_stack"]
            self.config["aws_stack_file"] = commons.get_hash(
                f"{self.config["deployer"]}/{self.config["aws_stack"]}"
            )

        else:

            raise ValueError("Invalid provider")

    def build(self, swagger=False):
        """
        Build the API files

        Parameters:
            swagger (bool): If True, the swagger file will be generated

        Returns:
            None

        Raises:
            ValueError: If the provider is not supported
        """

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

        # Generating swagger documentation
        if swagger:
            self._build_swagger()
            print(
                "Swagger Documentation:\n    {}".format(
                    json.dumps(self.swagger, indent=4).replace("\n", "\n    ")
                )
            )

        # Initialize methods dictionary
        self._get_methods()
        print(
            "API Methods Summary:\n    {}".format(
                json.dumps(self.building["methods"], indent=4).replace("\n", "\n    ")
            )
        )

        # Making temporal tree for function zips
        print("Making temporal tree for lambda zips")
        self._make_temporal_tree()

        # Copying files to temporal tree
        print("Copying files to temporal tree")
        self._copy_temporal_files()

        # Preparing temporal files
        print("Preparing temporal files")
        self._prepare_temporal_files()

        # Creating the zip files
        print("Zipping the files")
        self._zip_files()

        if self.config["provider"] == "aws":

            # Make the method template
            print("Making the methods template")
            self._aws_build_methods()

            # Make the API template
            print("Making the API template")
            self._aws_build_apigateway()

        else:

            raise ValueError("Invalid provider")

        # Set the built flag to True
        self.built = True

    def _get_filetree(self):
        """
        Get the file tree from the API source files

        Parameters:
            None

        Returns:
            None
        """

        # Initialize the filetree dictionary
        filetree = {}

        # Walk through the directory and build the filetree
        for root, dirs, files in os.walk(self.config["path_sources"]):

            # Create a nested dictionary for each directory
            directory = filetree
            for part in os.path.relpath(root, self.config["path_sources"]).split(
                os.sep
            ):
                if part != ".":
                    directory = directory.setdefault(part, {})

            # Add files to the current directory
            directory.update({file: None for file in files})

        # Store the filetree in the building dictionary
        self.building["filetree"] = filetree

    def _get_structure(self):
        """
        Get the structure of the API from the filetree

        Parameters:
            None

        Returns:
            None

        Raises:
            ValueError: If the filetree contains an invalid HTTP method
        """

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
                    if k not in commons.http_methods:
                        raise ValueError("Invalid HTTP method: {}".format(k))
                else:
                    check_http_methods(v)

        check_http_methods(filetree_copy)

        # Store the structure in the building dictionary
        self.building["structure"] = filetree_copy

    def _build_swagger(self):

        def _add_methods(structure, path):
            methods = {}
            for token in structure:
                if token in commons.http_methods:
                    with open(
                        os.path.join(
                            self.config["path_sources"],
                            os.path.join(path, token),
                            "index.mjs",
                        )
                    ) as f:
                        content = f.read()
                        start = content.find("/** swagger")
                        start = content.find("\n", start)
                        end = content.find("\n*/", start) + 1
                        swagger_comment = content[start:end]
                        if f"/{path}" not in methods:
                            methods[f"/{path}"] = {}
                        methods[f"/{path}"][token.lower()] = json.loads(
                            f"{{{swagger_comment}}}"
                        )
                else:
                    methods = methods | _add_methods(
                        structure[token], os.path.join(path, token)
                    )
            return methods

        # Initialize the swagger dictionary
        self.swagger = {
            "openapi": "3.0.0",
            "info": {
                "title": self.config["name"],
            },
            "schemes": ["https", "http"],
            "paths": _add_methods(self.building["structure"], ""),
        }
        if "title" in self.config:
            self.swagger["info"]["title"] = self.config["title"]
        if "version" in self.config:
            self.swagger["info"]["version"] = self.config["version"]
        if "description" in self.config:
            self.swagger["info"]["description"] = self.config["description"]

        # Clear the docs directory
        if os.path.exists(self.config["path_documentation"]):
            os.system(f"rm -rf {self.config['path_documentation']}/*")
        else:
            os.makedirs(self.config["path_documentation"])

        # Write the swagger file
        json.dump(
            self.swagger,
            indent=4,
            sort_keys=True,
            fp=open(
                os.path.join(self.config["path_documentation"], "swagger.json"), "w"
            ),
        )

        # Copy the swagger ui files
        os.system(f"cp -r {swagger_ui_path}/* {self.config["path_documentation"]}")

        # Modify the initializer file
        index_html_path = os.path.join(
            self.config["path_documentation"], "swagger-initializer.js"
        )
        with open(index_html_path, "r") as f:
            index_html = f.read()
        index_html = index_html.replace(
            'url: "https://petstore.swagger.io/v2/swagger.json"',
            'url: "./swagger.json"',
        )
        with open(index_html_path, "w") as f:
            f.write(index_html)

    def _get_methods(self):
        """
        Get the methods from the structure and prepares tje data structure

        Parameters:
            None

        Returns:
            None
        """

        # Initialize the methods dictionary
        self.building["methods"] = {}

        # Function to get the methods
        def get_methods(d, path):
            for token in d:
                path_sources = os.path.join(path, token)
                if token in commons.http_methods:
                    method_hash = commons.get_hash(
                        f"{self.config["deployer"]}-{path}/{token}"
                    )
                    last_change = int(os.path.getmtime(path_sources))
                    self.building["methods"][method_hash] = {
                        "hash": method_hash,
                        "method": token,
                        "zip": f"{last_change}-{method_hash}.zip",
                        "json": f"{last_change}-{method_hash}.json",
                        "path_sources": path_sources,
                        "resource": "/".join(path_sources.split("/")[2:-1]),
                        "path_temporal": os.path.join(
                            self.config["path_temporal"], method_hash
                        ),
                    }

                else:
                    get_methods(d[token], path_sources)

        # Get the methods from the structure
        get_methods(self.building["structure"], self.config["path_sources"])

    def _make_temporal_tree(self):
        """
        Make the temporal tree for the function files

        Parameters:
            None

        Returns:
            None
        """

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
        """
        Copy the files to the temporal directories for each method

        Parameters:
            None

        Returns:
            None
        """
        # Copy the files to the temporal directories for each method
        for method in self.building["methods"]:
            os.system(
                f"cp -r {self.building["methods"][method]["path_sources"]}/* {self.building['methods'][method]['path_temporal']}"
            )

    def _prepare_temporal_files(self):
        """
        Prepare the temporal files for each method, executing the preparation rules

        Parameters:
            None

        Returns:
            None
        """

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
        """
        Clean the mjs file applying the comment rules

        Parameters:
            None

        Returns:
            None
        """

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
        """
        Zip the files for each method

        Parameters:
            None

        Returns:
            None
        """

        # Zip the files for each method
        for method in self.building["methods"]:
            os.system(
                f"cd {self.building['methods'][method]["path_temporal"]} && zip -r {self.building['methods'][method]['zip']} * >/dev/null 2>&1"
            )

    def _aws_build_methods(self):
        """
        Make the methods template for AWS Cloudformation

        Parameters:
            None

        Returns:
            None
        """

        # Iterate over the methods
        for method in self.building["methods"]:

            # Creating method short reference
            method = self.building["methods"][method]

            method["template"] = {
                "AWSTemplateFormatVersion": "2010-09-09",
                "Parameters": {
                    "parGateway": {"Type": "String"},
                    "parResourceId": {"Type": "String"},
                },
                "Resources": {
                    f"{method["hash"]}Method": {
                        "Type": "AWS::ApiGateway::Method",
                        "Properties": {
                            "AuthorizationType": "NONE",
                            "HttpMethod": method["method"],
                            "ResourceId": {"Ref": "parResourceId"},
                            "RestApiId": {"Ref": "parGateway"},
                            "Integration": {
                                "Type": "AWS_PROXY",
                                "IntegrationHttpMethod": "POST",
                                "Uri": {
                                    "Fn::Sub": f"arn:aws:apigateway:${{AWS::Region}}:lambda:path/2015-03-31/functions/${{{method["hash"]}Function.Arn}}/invocations",
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
                            "Handler": "index.handler",
                            "Role": {"Fn::GetAtt": f"{method["hash"]}Role.Arn"},
                            "Runtime": "nodejs20.x",
                            "Timeout": 10,
                            "MemorySize": 256,
                            "TracingConfig": {"Mode": "Active"},
                            "Code": {
                                "S3Bucket": self.config["aws_bucket"],
                                "S3Key": f"API/{method["zip"]}",
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
            json.dump(
                method["template"],
                indent=4,
                sort_keys=True,
                fp=open(f"{method["path_temporal"]}/{method["json"]}", "w"),
            )

    def _aws_build_apigateway(self):
        """
        Make the API template for AWS Cloudformation

        Parameters:
            None

        Returns:
            None
        """

        # Initialize the depends list
        dependence = ["apiGateway"]
        for method in self.building["methods"]:
            dependence.append(f"{self.building['methods'][method]['hash']}Stack")

        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                "apiGateway": {
                    "Type": "AWS::ApiGateway::RestApi",
                    "Properties": {
                        "Name": self.config["name"],
                        "Parameters": {"EndpointConfiguration": "REGIONAL"},
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
                        "TracingEnabled": True,
                        "MethodSettings": [
                            {
                                "DataTraceEnabled": True,
                                "HttpMethod": "*",
                                "LoggingLevel": "INFO",
                                "ResourcePath": "/*",
                            }
                        ],
                        "StageName": self.config["aws_stage"],
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

        # Calculating the API resources
        resources_methods = {}
        for method in self.building["methods"]:
            # Adding the method to the resources list and adding the parent resource
            if self.building["methods"][method]["resource"] not in resources_methods:
                resources_methods[self.building["methods"][method]["resource"]] = []
            resources_methods[self.building["methods"][method]["resource"]].append(
                self.building["methods"][method]["method"]
            )

        # Calculating all required resources paths
        resources_all = []
        for resource in resources_methods:
            while len(resource) > 0:
                if resource not in resources_all:
                    resources_all.append(resource)
                resource = "/".join(resource.split("/")[:-1])

        # Creating all required resources paths
        for resource in resources_all:

            # Calculating the resource hash
            resource_hash = commons.get_hash(resource)

            # Calculating the parent resource
            resource_parent = {"Fn::GetAtt": "apiGateway.RootResourceId"}
            if len(resource.split("/")) > 1:
                resource_parent = {
                    "Ref": f"{commons.get_hash('/'.join(resource.split('/')[:-1]))}Resource"
                }

            # Adding the parent resource to the template
            template["Resources"][f"{resource_hash}Resource"] = {
                "Type": "AWS::ApiGateway::Resource",
                "Properties": {
                    "ParentId": resource_parent,
                    "PathPart": resource.split("/")[-1],
                    "RestApiId": {"Ref": "apiGateway"},
                },
            }

        # Creating the OPTION method for CORS
        for resource in resources_methods:

            # Checking to avoid overwriting options
            if "OPTIONS" in resources_methods[resource]:
                continue

            # Calculating the resource hash
            resource_hash = commons.get_hash(resource)
            resource_id = resource_parent = {"Fn::GetAtt": "apiGateway.RootResourceId"}
            if len(resource) > 0:
                resource_id = {"Ref": f"{resource_hash}Resource"}

            # Adding the CORS method to the parent resource
            template["Resources"][f"{resource_hash}ResourceOPTIONS"] = {
                "Type": "AWS::ApiGateway::Method",
                "Properties": {
                    "AuthorizationType": "NONE",
                    "RestApiId": {"Ref": "apiGateway"},
                    "ResourceId": resource_id,
                    "HttpMethod": "OPTIONS",
                    "Integration": {
                        "Type": "MOCK",
                        "PassthroughBehavior": "WHEN_NO_MATCH",
                        "RequestTemplates": {"application/json": '{"statusCode": 200}'},
                        "IntegrationResponses": [
                            {
                                "StatusCode": 200,
                                "ResponseParameters": {
                                    "method.response.header.Access-Control-Allow-Headers": "'*'",
                                    "method.response.header.Access-Control-Allow-Methods": "'GET,OPTIONS'",
                                    "method.response.header.Access-Control-Allow-Origin": "'*'",
                                },
                            }
                        ],
                    },
                    "MethodResponses": [
                        {
                            "StatusCode": 200,
                            "ResponseModels": {"application/json": "Empty"},
                            "ResponseParameters": {
                                "method.response.header.Access-Control-Allow-Headers": False,
                                "method.response.header.Access-Control-Allow-Methods": False,
                                "method.response.header.Access-Control-Allow-Origin": False,
                            },
                        }
                    ],
                },
            }

        # Creating the methods
        for method in self.building["methods"]:

            resource = self.building["methods"][method]["resource"]

            # Calculating the parent resource
            resource_parent = {"Fn::GetAtt": "apiGateway.RootResourceId"}
            if len(resource) > 0:
                resource_parent = {"Ref": f"{commons.get_hash(resource)}Resource"}

            template["Resources"][
                f"{self.building['methods'][method]['hash']}Stack"
            ] = {
                "Type": "AWS::CloudFormation::Stack",
                "Properties": {
                    "TemplateURL": f"https://{self.config["aws_bucket"]}.s3.amazonaws.com/API/{self.building['methods'][method]['json']}",
                    "Parameters": {
                        "parGateway": {"Ref": "apiGateway"},
                        "parResourceId": resource_parent,
                    },
                },
            }

        # Create the template file
        json.dump(
            template,
            indent=4,
            sort_keys=True,
            fp=open(
                f"{self.config["path_temporal"]}/{self.config["timestamp"]}-{self.config["aws_stack_file"]}.json",
                "w",
            ),
        )

    def deploy(self, wait=False):
        """
        Deploys the API

        Parameters:
            None

        Returns:
            None

        Raises:
            ValueError: If the provider is not supported
        """

        if not self.built:

            raise ValueError("API must be built before deploying")

        if self.config["provider"] == "aws":

            self._aws_deploy(wait)

        else:

            raise ValueError("Invalid provider")

        # Set the deployed flag to True
        self.deployed = True

    def _aws_deploy(self, wait=False):
        """
        Deploy the API to AWS Cloudformation

        Parameters:
            None

        Returns:
            None
        """
        # Create the aws session
        self.aws = boto3.Session(profile_name=self.config["aws_profile"])

        # Uploading the files to S3
        print("Uploading the files to S3")
        self._aws_upload()

        # Deploying cloudformation
        print("Deploying cloudformation")
        commons.aws.cloudformation.deploy(self, "API", capabilities=["CAPABILITY_IAM"])

        # Wait for the deployment to finish
        if wait:
            print("Waiting for the deployment to finish")
            commons.aws.cloudformation.deploy_wait(self)

        # Delete the pointer to the aws session - No need to close it
        del self.aws

    def _aws_upload(self):
        """
        Upload the files to S3

        Parameters:
            None

        Returns:
            None
        """
        # Create the S3 client
        s3_client = self.aws.client("s3", region_name=self.config["aws_region"])

        # For each method, upload the zip file to S3
        for method in self.building["methods"]:
            s3_client.upload_file(
                os.path.join(
                    self.building["methods"][method]["path_temporal"],
                    self.building["methods"][method]["zip"],
                ),
                self.config["aws_bucket"],
                f"API/{self.building["methods"][method]["zip"]}",
            )
            s3_client.upload_file(
                os.path.join(
                    self.building["methods"][method]["path_temporal"],
                    self.building["methods"][method]["json"],
                ),
                self.config["aws_bucket"],
                f"API/{self.building["methods"][method]["json"]}",
            )

        # Upload the API template to S3
        s3_client.upload_file(
            f"{self.config["path_temporal"]}/{self.config["timestamp"]}-{self.config["aws_stack_file"]}.json",
            self.config["aws_bucket"],
            f"API/{self.config["timestamp"]}-{self.config["aws_stack_file"]}.json",
        )

        # Close the S3 client
        s3_client.close()
