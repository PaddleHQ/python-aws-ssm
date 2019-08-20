[![Build Status](https://wdp9fww0r9.execute-api.us-west-2.amazonaws.com/production/badge/PaddleHQ/python-aws-ssm)](https://wdp9fww0r9.execute-api.us-west-2.amazonaws.com/production/results/PaddleHQ/python-aws-ssm)
[![codecov](https://codecov.io/gh/PaddleHQ/python-aws-ssm/branch/master/graph/badge.svg)](https://codecov.io/gh/PaddleHQ/python-aws-ssm)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
<a href="https://github.com/ambv/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>

# python-aws-ssm
Python package that interfaces with [AWS System Manager](https://www.amazonaws.cn/en/systems-manager/).

## Why to use python-aws-ssm and not the aws-sdk-go?
This package is wrapping the aws-sdk-go and hides the complexity dealing with the not so Python friendly AWS SDK.
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
from aws_ssm.parameters import ParameterStore

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
from aws_ssm.parameters import ParameterStore

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
from aws_ssm.parameters import ParameterStore

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

## Development

If you are missing any features or have found a bug, please open a PR or a new Github issue.

TODO:
* How to run tests?
