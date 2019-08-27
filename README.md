![build](https://action-badges.now.sh/PaddleHQ/python-aws-ssm)
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

