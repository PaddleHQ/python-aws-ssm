import click
import logging
from python_aws_ssm.parameters import ParameterStore
from json import dumps
from yaml import safe_load
from os import exit
from pathlib import Path


log = logging.getLogger()
parameter_store = ParameterStore()


@click.group()
@click.option("--debug", prompt=False, is_flag=True)
def cli(debug):
    if debug:
        log.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        log.addHandler(handler)

        log.debug("debug logging on")
    pass


@click.command()
@click.option("--path", help="Path to get from SSM")
@click.option("--key", prompt=False)
@click.option(
    "--recursive",
    default=False,
    prompt=False,
    help="If true return a nested object with all keys value under the base path",
)
def get(path: str, key: str | None = None, recursive: bool = False) -> None:
    """
    Retrieves a path and a key from the path or everything from the path
    :param: required_parameters: path
    :return if both path and key then return the key from the path
    if only path is requested return everything from the path
    returns json
    """

    # Requesting the base path
    if path:
        parameters = parameter_store.get_parameters_by_path(
            ssm_base_path=path, recursive=recursive
        )
        if key:
            # And return a specific key
            value = parameters.get(key)
            return dumps(value)
    # Otherwise return the whole value
    return dumps(parameters)


@click.command()
@click.option("--overwrite/--no-overwrite", default=False, prompt=False)
@click.option(
    "--value", default=None, help="A string to be stored in SSM, limit of 4kb"
)
@click.option("--path", help="The name of the key where it will be stored")
@click.argument("file")
@click.group
@click.option(
    "--to-json",
    default=False,
    prompt=False,
    help="Enables converting a YAML file to JSON, limit of 4kb",
)
@click.option(
    "--yaml-node", default=None, help="The name of a top level node that will be stored"
)

def put(
    value: str,
    path: str,
    yaml_node: str = None,
    overwrite: bool = False,
    file: str | None = None,
) -> str:
    """
    Stores a string value in a SSM path
    Supports reading from a yaml file , convert it to json and strore it,
    if a yaml node is specified then that node only will be stored
    :param: required_parameters: path
    :param str value
    :param str yaml_node
    :param bool overwrite
    :param str file
    :return Json response AWS
    :TODO: add support for tags
    """

    if value:
        final_value = value
    elif file:
        logging.debug(f"Reading from file: {file}")
        yaml_data = safe_load(Path(file).read_text())
        if yaml_node:
            try:
                final_value = yaml_data[yaml_node]
                final_value = dumps(yaml_data)
            except KeyError:
                logging.fatal(f"Yaml node {yaml_node} not found, exiting")
                exit(-1)
    else:
        logging.fatal("Either a value or a file must be specified exiting")
        exit(-2)

    ret = parameter_store.put_parameter(
        path=path, value=final_value, overwrite=overwrite
    )
    return dumps(ret)


cli.add_command(get)
cli.add_command(put)

if __name__ == "__main__":
    cli()
