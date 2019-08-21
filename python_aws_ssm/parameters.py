from typing import Any, Dict, List, Optional, Union

import boto3


class ParameterStore:
    def __init__(self, client: Optional[boto3.client] = None):
        self.client = client or boto3.client("ssm")

    def get_parameters(self, ssm_key_names: List[str]) -> Dict[str, Optional[str]]:
        """
        Retrieve keys from SSM.
        The keys are mapped to a dictionary for easy querying:
            * Keys that exist in SSM should have a matching key in the result dict
            and a matching value.
            * Keys that do not exist in SSM should also have a matching key, but
            have a matching value of None.
        If SSM somehow returns keys that are not requested, these keys are not
        returned in the result dict.
        """

        retrieved_parameters = self.client.get_parameters(
            Names=ssm_key_names, WithDecryption=True
        ).get("Parameters")

        # Initialise the result so that missing keys have a None value.
        filled_parameters: Dict[str, Optional[str]] = {
            parameter_name: None for parameter_name in ssm_key_names
        }

        # Merge the retrieved parameters in.
        for retrieved in retrieved_parameters:
            if retrieved.get("Name") in ssm_key_names:
                filled_parameters[retrieved.get("Name")] = retrieved.get("Value")

        return filled_parameters

    def get_parameters_by_path(
        self,
        ssm_base_path: str,
        with_decryption: bool = True,
        recursive: bool = False,
        nested: bool = False,
    ) -> Dict[str, Union[Dict, Optional[str]]]:
        """
        Retrieve all the keys under a certain path on SSM.
        * When recursive is set to False, SSM doesn't return keys under a nested path.
            e.g.: /{ssm_base_path}/foo/bar will not return 'bar' nor '/foo/bar'.
        * When recursive and nested are set to True, a nested dictionary is returned.
            e.g.: /{ssm_base_path}/foo/bar will return {"foo": {"bar": "value"}}
        * When nested is set to False, the full subpath is returned as key.
            e.g.: /{ssm_base_path}/foo/bar will return {"foo/bar": "value"}}}

        :return If nested=False, a dictionary of string to optional string value.
         If nested=True, a dictionary of string to potentially nested dictionaries with
         optional string values.
        """

        parameters = self.client.get_parameters_by_path(
            Path=ssm_base_path, Recursive=recursive, WithDecryption=with_decryption
        ).get("Parameters")

        parameters = {
            parameter.get("Name").replace(ssm_base_path, ""): parameter.get("Value")
            for parameter in parameters
        }

        return (
            # Non-nested is the default behaviour (hence `else parameters`).
            self._parse_parameters(parameters)
            if recursive and nested
            else parameters
        )

    @staticmethod
    def _parse_parameters(
        parameters: Dict[str, Optional[str]]
    ) -> Dict[str, Union[Dict, Optional[str]]]:
        parsed_dict: Dict[str, Union[Dict, Optional[str]]] = {}
        for key, value in parameters.items():
            nested_dict = ParameterStore._tree_dict(key.split("/"), value)
            parsed_dict = ParameterStore._deep_merge(parsed_dict, nested_dict)
        return parsed_dict

    @staticmethod
    def _tree_dict(key_list: List[Any], value: Optional[Any]) -> Dict[Any, Any]:
        """
        Build a nested dictionary path from a list of keys and a value.
        For example:
            _tree_dict(["foo", "bar", "koo"], 42) ==> {"foo": {"bar": {"koo": 42}}}
        """
        tree_dict: Dict[Any, Any] = {key_list[-1]: value}
        for key in reversed(key_list[:-1]):
            tree_dict = {key: tree_dict}
        return tree_dict

    @staticmethod
    def _deep_merge(a: Union[Dict, Any], b: Union[Dict, Any]) -> Union[Dict, Any]:
        # NOTE: Thanks to: https://stackoverflow.com/a/56177639/9563578
        if not isinstance(a, dict) or not isinstance(b, dict):
            return a if b is None else b
        else:
            keys = set(a.keys()) | set(b.keys())
            return {
                key: ParameterStore._deep_merge(a.get(key), b.get(key)) for key in keys
            }
