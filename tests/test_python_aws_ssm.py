from unittest import TestCase
from unittest.mock import MagicMock

from python_aws_ssm import __version__
from python_aws_ssm.parameters import MissingParameterError, ParameterStore


def test_version():
    assert __version__ == "0.1.2"


class TestGetParameters(TestCase):
    def setUp(self):
        self.parameter_store = ParameterStore(client=MagicMock())

    def tearDown(self):
        pass

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
        e: MissingParameterError
        with self.assertRaises(MissingParameterError, msg=expected_msg) as e:
            self.parameter_store.get_parameters_by_path(
                "/path/sub/", required_parameters={"baz", "foo/bar", "key"}
            )
            assert e.parameter_path == "/path/sub/"
            assert e.parameter_names == ["baz", "foo/bar"]

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
