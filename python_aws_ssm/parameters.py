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

        parameters = self.client.get_parameters(
            Names=ssm_key_names, WithDecryption=True
        ).get("Parameters")
        return {
            parameter.get("Name"): parameter.get("Value")
            for parameter in parameters
            if parameter.get("Name") in ssm_key_names
        }

    def get_parameters_by_path(
        self,
        ssm_base_path: str,
        with_decryption: bool = True,
        recursive: bool = False,
        nested: bool = False,
    ) -> Dict[str, Optional[str]]:
        """
        Retrieve all the keys under a certain path on SSM.
        * Wnen recursive is set to False, SSM doesn't parameters under a nested path.
            e.g.: /{ssm_base_path}/foo/bar will not return 'bar' nor '/foo/bar'.
        * When recursive and nested are set to True, a nested dictionary is returned.
            e.g.: /{ssm_base_path}/foo/bar will return {"foo": {"bar": "value"}}
        * When nested is set to False, the full subpath is returned as key.
            e.g.: /{ssm_base_path}/foo/bar will return {"foo/bar": "value"}}}
        """

        parameters = self.client.get_parameters_by_path(
            Path=ssm_base_path, Recursive=recursive, WithDecryption=with_decryption
        ).get("Parameters")

        parameters = {
            parameter.get("Name").replace(ssm_base_path, ""): parameter.get("Value")
            for parameter in parameters
        }

        return (
            self._parse_parameters(parameters) if recursive and nested else parameters
        )

    @staticmethod
    def _parse_parameters(
        parameters: Dict[str, Optional[str]]
    ) -> Dict[Union[Dict, str], Optional[Union[Dict, str]]]:
        parsed_dict: Dict[Union[Dict, str], Optional[Union[Dict, str]]] = {}
        for key, value in parameters.items():
            nested_dict = ParameterStore._tree_dict(key.split("/"), value)
            parsed_dict = ParameterStore._deep_merge(parsed_dict, nested_dict)
        return parsed_dict

    @staticmethod
    def _tree_dict(key_list: List[Any], value: Optional[Any]) -> Dict[Any, Any]:
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
