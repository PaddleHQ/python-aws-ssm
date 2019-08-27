from unittest import TestCase
from unittest.mock import MagicMock

from python_aws_ssm import __version__
from python_aws_ssm.parameters import ParameterStore


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
