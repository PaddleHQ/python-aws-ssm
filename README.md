[![Build Status](https://travis-ci.com/PaddleHQ/python-aws-ssm.svg?branch=master)](https://travis-ci.com/PaddleHQ/python-aws-ssm)
[![codecov](https://codecov.io/gh/PaddleHQ/python-aws-ssm/branch/master/graph/badge.svg)](https://codecov.io/gh/PaddleHQ/python-aws-ssm)
[![license](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![codestyle](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

# python-aws-ssm
Python package that interfaces with [AWS System Manager](https://www.amazonaws.cn/en/systems-manager/).

## Why to use python-aws-ssm and not the boto3 SSM client?
This package is wrapping boto3 SSM client and hides the complexity dealing with the not so Python friendly AWS SDK.
Perfect use case for this package is when secure parameters for an application are stored to
[AWS Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
using a path hierarchy. During application startup you can use this package to fetch them and use them in your application.

## Warning

The SSM service is rate-limited by default. We strongly suggest using
retrieving SSM keys by path, e.g. via `ParameterStore.get_parameters_by_path()`.
This requires grouping keys by a useful path but reduces the chance of
your own services being rate-limited in turn.

## Install
```bash
pip install python-aws-ssm
```

## Examples

#### Basic Usage

```python
from python_aws_ssm.parameters import ParameterStore

# Assuming you have the parameters in the following format:
# my-service/dev/param-1  -> with value `a`
# my-service/dev/param-2  -> with value `b`
parameter_store = ParameterStore()
# Requesting the base path
parameters = parameter_store.get_parameters_by_path("/my-service/dev/")
# And getting a specific value
value = parameters.get("param-1")
# value should be `a`
```

#### Required parameters on path

Requesting parameters by path is efficient but comes with an additional
burden of validation: clients typically expect a number of keys to be
present, e.g. the path `/service/foo/db/` might be used to retrieve the
database credentials including the host name at `/service/foo/db/hostname`.
The onus of verifying that this key is present is by default on the client.

To assert the presence of these keys automatically, pass a set of required
parameters via the `parameters` keyword argument:

```python
from python_aws_ssm.parameters import ParameterStore, MissingParameterError

# Assuming you have the following keys:
#  * /service/foo/db/hostname
#  * /service/foo/db/username
#  * /service/foo/db/password
#  * /service/foo/db/port
#  * /service/foo/db/description
parameter_store = ParameterStore()
# Requesting the base path but asserting presence of required parameters
try:
    parameters = parameter_store.get_parameters_by_path(
            "/service/foo/db/",
            required_parameters={"hostname", "username", "password", "port"}
        )
except MissingParameterError as e:
    # Report on the missing parameters.
    print(e.msg)
else:
    # Use the parameters, knowing that they exist.
    print(parameters['hostname'])  # guaranteed to exist.
```

#### Recursive and nested options

```python
from python_aws_ssm.parameters import ParameterStore

# Assuming you have the parameters in the following format:
# my-service/dev/param-1  -> with value `a`
# my-service/dev/param-2  -> with value `b`
parameter_store = ParameterStore()
# Requesting the base path
parameters = parameter_store.get_parameters_by_path(
    "/my-service/", recursive=True, nested=True
)
# And getting a specific value
dev_parameters = parameters.get("dev")
# value should be {"param-1": "a", "param-2": "b"}
```

#### Get parameters by name

```python
from python_aws_ssm.parameters import ParameterStore

# Assuming you have the parameters in the following format:
# my-service/dev/param-1  -> with value `a`
# common/dev/param-2  -> with value `b`
parameter_store = ParameterStore()
# Requesting the base path
parameters = parameter_store.get_parameters(
    ["/my-service/dev/param-1", "/common/dev/param-2"]
)
# And getting a specific value
dev_parameters = parameters.get("/common/dev/param-2")
# value should be `b`
```

#### With custom client

```python
from python_aws_ssm.parameters import ParameterStore
import boto3

# Initialise an SSM client to specify the source of the credentials.
# e.g. locally a profile would be more likely; an AWS Lambda would most
# likely not override the credentials source.
ssm_client = boto3.Session(profile_name='dev').client('ssm')
parameter_store = ParameterStore(ssm_client)

parameters = parameter_store.get_parameters(["/service/path/"])
```

## Development

If you are missing any features or have found a bug, please open a PR or a new Github issue.


#### Setup
This project uses Poetry to manage the dependencies and the virtual environment.
Follow the instructions from Poetry website (https://poetry.eustace.io/docs/#installation) to configure your local environment.

After completing the Poetry setup, the virtual environment can be created running:
```shell
make setup
```

#### Tests
Tests are run by Pytest
```shell
make test
```

#### Code style
- Mypy is used for type annotations (https://github.com/python/mypy)
- Black formatter (https://github.com/psf/black) is used to keep the coding style consistent.
- Isort (https://github.com/timothycrosley/isort) is used to sort the imports.
To format the codebase just run:
```shell
make format
```
and to check it before pushing:
```shell
make lint
```

### Using the library from the command line
#### Build and install the package
```bash
$ poetry build
Building python-aws-ssm (1.0.0)
  - Building sdist
  - Built python-aws-ssm-1.0.0.tar.gz
  - Building wheel
  - Built python_aws_ssm-1.0.0-py3-none-any.whl

$ pip install dist/python_aws_ssm-1.0.0-py3-none-any.whl
```

#### Usage
```
$ aws-ssm-param
Usage: aws-ssm-param [OPTIONS] COMMAND [ARGS]...

Options:
  --debug
  --help   Show this message and exit.

Commands:
  get  Retrieves the value of a key from SSM Returns the raw value
  put  Stores a string value in a SSM path
```
#### Put
```
$ aws-ssm-param put
Usage: aws-ssm-param put [OPTIONS] [FILE]

  Stores a string value in a SSM path

  Supports reading from a yaml file , convert it to json and store the result.
  if a yaml node is specified then the content of that node will be stored

Options:
  --overwrite / --no-overwrite  Defaults to --no-overwrite
  --value TEXT                  A string to be stored in SSM, limit of 4kb
  --path TEXT                   The name of the key where it will be stored
  --to-json                     Enables converting a YAML file to JSON, limit
                                of 4kb
  --yaml-node TEXT              The name of a top level node that will be
                                stored
  --help                        Show this message and exit.
  ```

### Get
```
$ aws-ssm-param get
Usage: aws-ssm-param get [OPTIONS]

  Retrieves the value of a key from SSM Returns the raw value

Options:
  --key TEXT  Key to get from SSM  [required]
  --help      Show this message and exit.
```