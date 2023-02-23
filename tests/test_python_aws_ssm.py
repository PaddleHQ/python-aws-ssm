import os
import botocore
from unittest import TestCase
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from pathlib import Path
from python_aws_ssm.cli import cli
from python_aws_ssm import __version__
from python_aws_ssm.parameters import (
    InvalidParametersError,
    MissingParameterError,
    ParameterStore,
)


def test_version():
    assert __version__ == "1.0.0"


class TestCli(TestCase):
    def setUp(self):
        self.parameter_store = ParameterStore(client=MagicMock())
        os.environ["AWS_ACCESS_KEY_ID"] = "testingtestingtesting"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testingtesting"
        os.environ["AWS_SESSION_TOKEN"] = "testingtesting"
        os.environ["AWS_REGION"] = "eu-west-1"

    def tearDown(self):
        del os.environ["AWS_ACCESS_KEY_ID"]
        del os.environ["AWS_SECRET_ACCESS_KEY"]
        del os.environ["AWS_SESSION_TOKEN"]
        del os.environ["AWS_REGION"]

    def __mock_api_call(cls, operation_name: str, kwargs: dict) -> dict:
        if operation_name == "GetParameters":
            return cls.__generate_response_ssm_get_parameters()
        if operation_name == "PutParameter":
            return cls.__generate_response_ssm_put_parameters()

    def __generate_response_ssm_get_parameters(self) -> dict:
        return {
            "InvalidParameters": [],
            "Parameters": [
                {
                    "ARN": "arn:aws:ssm:eu-west-1:111111111111:parameter/my/test/8",
                    "DataType": "text",
                    "LastModifiedDate": 1.677065896099e9,
                    "Name": "/my/test/8",
                    "Type": "String",
                    "Value": "TEST",
                    "Version": 1,
                }
            ],
        }

    def __generate_response_ssm_put_parameters(self) -> dict:
        return {"Tier": "Standard", "Version": 1}

    def test_cli_get(self):
        """
        Test the get argument with a single key
        """
        with patch(
            "botocore.client.BaseClient._make_api_call", new=self.__mock_api_call
        ):
            result = CliRunner().invoke(cli, ["get", "--key", "/my/test/8"])

        print(result.__dict__)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout_bytes, b"TEST\n")

    def test_cli_put_value_positive(self):
        """
        Test the put argument with a single value
        """
        with patch(
            "botocore.client.BaseClient._make_api_call", new=self.__mock_api_call
        ):
            result = CliRunner().invoke(
                cli, ["put", "--value", "TEST", "--path", "/my/test/8"]
            )

        print(result.__dict__)
        self.assertEqual(result.exit_code, 0)

    def test_cli_put_no_value(self):
        """
        Test the put argument without a value
        """
        with patch(
            "botocore.client.BaseClient._make_api_call",
            new=self.__mock_api_call,
        ):
            result = CliRunner().invoke(cli, ["put", "--path", "/my/test/8"])
            self.assertEqual(result.exit_code, -2)

    def test_cli_put_value_exists(self):
        """
        Test the put argument with a single value in a path that already exists
        """

        def put_parameter_side_effect(**kwargs):
            raise botocore.exceptions.ClientError(
                {
                    "Error": {
                        "Code": "ParameterAlreadyExists",
                        "Message": "The parameter already exists. To overwrite this value, set the overwrite option in the request to true.",
                    }
                },
                "put_parameter",
            )

        with patch(
            "python_aws_ssm.cli.parameter_store.put_parameter",
            side_effect=put_parameter_side_effect,
        ):
            result = CliRunner().invoke(
                cli, ["put", "--value", "TEST", "--path", "/my/test/8"]
            )
            self.assertEqual(result.exit_code, -3)

    def test_cli_put_file(self):
        """
        Test the put argument from a file
        """
        fixture = "./tests/fixtures/file.yaml"
        with patch("botocore.client.BaseClient._make_api_call") as mocked:
            mocked.return_value = {"Tier": "Standard", "Version": 1}

            result = CliRunner().invoke(cli, ["put", "--path", "/my/test/8", fixture])
            mocked.assert_called_with(
                "PutParameter",
                {
                    "Name": "/my/test/8",
                    "Value": Path(fixture).read_text(),
                    "Type": "String",
                    "Overwrite": False,
                    "Tags": [],
                    "Tier": "Standard",
                },
            )
        self.assertEqual(result.exit_code, 0)

    def test_cli_put_file_node(self):
        """
        Test the put argument from a file, converts it to json and only stores one node
        """
        fixture = "./tests/fixtures/file.yaml"
        with patch("botocore.client.BaseClient._make_api_call") as mocked:
            mocked.return_value = {"Tier": "Standard", "Version": 1}

            result = CliRunner().invoke(
                cli,
                [
                    "put",
                    "--path",
                    "/my/test/8",
                    "--to-json",
                    "--yaml-node",
                    "xmas-fifth-day",
                    fixture,
                ],
            )
            mocked.assert_called_with(
                "PutParameter",
                {
                    "Name": "/my/test/8",
                    "Value": '{"calling-birds": "four", "french-hens": 3, "golden-rings": 5, "partridges": {"count": 1, "location": "a pear tree"}, "turtle-doves": "two"}',
                    "Type": "String",
                    "Overwrite": False,
                    "Tags": [],
                    "Tier": "Standard",
                },
            )
        self.assertEqual(result.exit_code, 0)


class TestGetParameters(TestCase):
    def setUp(self):
        self.parameter_store = ParameterStore(client=MagicMock())

    def tearDown(self):
        pass

    def test_put_parameter(self):
        """
        Test the put parameter function with a single value
        """

        self.parameter_store.client.put_parameter.return_value = {
            "Tier": "Standard",
            "Version": 1,
        }

        self.parameter_store.put_parameter(path="/test/path", value="TEST")

        self.parameter_store.client.put_parameter.assert_called_once_with(
            Name="/test/path",
            Value="TEST",
            Type="String",
            Overwrite=False,
            Tags=[],
            Tier="Standard",
        )

    def test_get_parameters_keys_are_mapped(self):
        self.parameter_store.client.get_parameters.return_value = {
            "Parameters": [
                {"Name": "foo_ssm_key_1", "Value": "foo_ssm_value_1"},
                # Note: foo_ssm_key_2 does not exist so is not returned from SSM.
                {"Name": "foo_ssm_key_3", "Value": "foo_ssm_value_3"},
            ]
        }

        secrets = self.parameter_store.get_parameters(
            ["foo_ssm_key_1", "foo_ssm_key_2", "foo_ssm_key_3"]
        )

        self.assertEqual(
            {
                "foo_ssm_key_1": "foo_ssm_value_1",
                "foo_ssm_key_2": None,
                "foo_ssm_key_3": "foo_ssm_value_3",
            },
            secrets,
        )

        self.parameter_store.client.get_parameters.assert_called_once_with(
            Names=["foo_ssm_key_1", "foo_ssm_key_2", "foo_ssm_key_3"],
            WithDecryption=True,
        )

    def test_get_parameters_unknown_keys_are_ignored(self):
        self.parameter_store.client.get_parameters.return_value = {
            "Parameters": [
                {"Name": "foo_ssm_key_1", "Value": "foo_ssm_value_1"},
                {"Name": "some_other_key", "Value": "value"},
            ]
        }

        secrets = self.parameter_store.get_parameters(["foo_ssm_key_1"])

        self.assertEqual({"foo_ssm_key_1": "foo_ssm_value_1"}, secrets)

    def test_get_parameters_aws_errors_are_not_caught(self):
        expected_error = Exception("Unexpected AWS error!")
        self.parameter_store.client.get_parameters.side_effect = expected_error

        with self.assertRaises(Exception, msg="Unexpected AWS error!"):
            self.parameter_store.get_parameters(["/key"])

    def test_get_parameters_by_path_keys_are_mapped(self):
        self.parameter_store.client.get_parameters_by_path.return_value = {
            "Parameters": [
                {"Name": "/bar/env/foo_ssm_key_1", "Value": "foo_ssm_value_1"},
                {"Name": "/bar/env/foo_ssm_key_2", "Value": "foo_ssm_value_2"},
            ]
        }
        secrets = self.parameter_store.get_parameters_by_path("/bar/env/")

        self.assertEqual(
            {"foo_ssm_key_1": "foo_ssm_value_1", "foo_ssm_key_2": "foo_ssm_value_2"},
            secrets,
        )

        self.parameter_store.client.get_parameters_by_path.assert_called_once_with(
            Path="/bar/env/", Recursive=False, WithDecryption=True
        )

    def test_get_parameters_by_path_are_stripped_of_leading_slashes(self):
        """
        Leading slashes of parameters are stripped consistently.

        When requesting parameters by a path that is not recursive and nested,
        the leading slashes should be consistently stripped. In versions <= 0.1.2,
        the leading slashes were not included if the parameter path ended in a
        trailing slash, but not if the parameter path ended without a trailing
        slash…
        """
        self.parameter_store.client.get_parameters_by_path.return_value = {
            "Parameters": [
                {"Name": "/bar/env/foo_ssm_key_1", "Value": "foo_ssm_value_1"},
                {"Name": "/bar/env/foo_ssm_key_2", "Value": "foo_ssm_value_2"},
            ]
        }
        # Note that the requested path has no trailing slash.
        parameters_path = "/bar/env"
        secrets = self.parameter_store.get_parameters_by_path(parameters_path)

        self.assertEqual(
            {"foo_ssm_key_1": "foo_ssm_value_1", "foo_ssm_key_2": "foo_ssm_value_2"},
            secrets,
        )

        self.parameter_store.client.get_parameters_by_path.assert_called_once_with(
            Path=parameters_path, Recursive=False, WithDecryption=True
        )

    def test_get_parameters_by_path_recursive_not_nested(self):
        self.parameter_store.client.get_parameters_by_path.return_value = {
            "Parameters": [
                {"Name": "/bar/env/foo_ssm_key_1", "Value": "foo_ssm_value_1"},
                {"Name": "/bar/env/foo_ssm_key_2", "Value": "foo_ssm_value_2"},
            ]
        }
        secrets = self.parameter_store.get_parameters_by_path(
            "/bar/", recursive=True, nested=False
        )

        self.assertEqual(
            {
                "env/foo_ssm_key_1": "foo_ssm_value_1",
                "env/foo_ssm_key_2": "foo_ssm_value_2",
            },
            secrets,
        )

        self.parameter_store.client.get_parameters_by_path.assert_called_once_with(
            Path="/bar/", Recursive=True, WithDecryption=True
        )

    def test_get_parameters_by_path_recursive_nested(self):
        self.parameter_store.client.get_parameters_by_path.return_value = {
            "Parameters": [
                {"Name": "/bar/env/foo_ssm_key_1", "Value": "foo_ssm_value_1"},
                {"Name": "/bar/env/foo_ssm_key_2", "Value": "foo_ssm_value_2"},
            ]
        }
        secrets = self.parameter_store.get_parameters_by_path(
            "/bar/", recursive=True, nested=True
        )

        self.assertEqual(
            {
                "env": {
                    "foo_ssm_key_1": "foo_ssm_value_1",
                    "foo_ssm_key_2": "foo_ssm_value_2",
                }
            },
            secrets,
        )

        self.parameter_store.client.get_parameters_by_path.assert_called_once_with(
            Path="/bar/", Recursive=True, WithDecryption=True
        )

    def test_get_parameter_by_path_aws_errors_are_not_caught(self):
        expected_error = Exception("Unexpected AWS error!")
        self.parameter_store.client.get_parameters_by_path.side_effect = expected_error

        with self.assertRaises(Exception, msg="Unexpected AWS error!"):
            self.parameter_store.get_parameters_by_path(["/key"])

    def test_get_required_parameters_by_path_can_be_asserted(self) -> None:
        """
        Required parameters that are missing from a path result in an error.
        """

        self.parameter_store.client.get_parameters_by_path.return_value = {
            "Parameters": [
                # Only one of the required parameters is returned.
                {"Name": "/path/sub/key", "Value": "foo_ssm_value_1"},
                {"Name": "/path/sub/key2", "Value": "foo_ssm_value_2"},
            ]
        }

        expected_msg = "Missing parameters [baz, foo/bar] on path /path/sub/"
        with self.assertRaises(MissingParameterError, msg=expected_msg) as exc_info:
            self.parameter_store.get_parameters_by_path(
                "/path/sub/", required_parameters={"baz", "foo/bar", "key"}
            )
        assert exc_info.exception.parameter_path == "/path/sub/"
        assert len(exc_info.exception.parameter_names) == 2
        assert sorted(exc_info.exception.parameter_names) == sorted(["baz", "foo/bar"])

    def test_required_parameters_by_path_are_checked_before_recursive_nested(self):
        self.parameter_store.client.get_parameters_by_path.return_value = {
            "Parameters": [
                {"Name": "/bar/env/foo_ssm_key_1", "Value": "foo_ssm_value_1"},
                {"Name": "/bar/env/foo_ssm_key_2", "Value": "foo_ssm_value_2"},
            ]
        }
        secrets = self.parameter_store.get_parameters_by_path(
            "/bar/",
            recursive=True,
            nested=True,
            required_parameters={"env/foo_ssm_key_1", "env/foo_ssm_key_2"},
        )

        self.assertEqual(
            {
                "env": {
                    "foo_ssm_key_1": "foo_ssm_value_1",
                    "foo_ssm_key_2": "foo_ssm_value_2",
                }
            },
            secrets,
        )

        self.parameter_store.client.get_parameters_by_path.assert_called_once_with(
            Path="/bar/", Recursive=True, WithDecryption=True
        )

    def test_requesting_invalid_parameters(self):
        """Assert requesting invalid parameters results in an exception."""
        self.parameter_store.client.get_parameters.return_value = {
            "Parameters": [{"Name": "/test/foo", "Value": "foo_ssm_value_1"}],
            "InvalidParameters": ["/test/bar"],
        }

        with self.assertRaises(
            InvalidParametersError, msg='Invalid parameters ["/test/bar"] requested'
        ) as exc_info:
            self.parameter_store.get_parameters(["/test/foo", "/test/bar"])
        assert exc_info.exception.invalid_parameters == ["/test/bar"]
