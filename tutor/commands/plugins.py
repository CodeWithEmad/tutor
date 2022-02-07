import os
import shutil
import urllib.request
from typing import List

import click

from tutor import config as tutor_config
from tutor import env as tutor_env
from tutor import exceptions, fmt, plugins
from tutor.plugins.v0 import DictPlugin

from .context import Context


@click.group(
    name="plugins",
    short_help="Manage Tutor plugins",
    help="Manage Tutor plugins to add new features and customize your Open edX platform",
)
def plugins_command() -> None:
    """
    All plugin commands should work even if there is no existing config file. This is
    because users might enable plugins prior to configuration or environment generation.
    """


@click.command(name="list", help="List installed plugins")
def list_command() -> None:
    for plugin in plugins.iter_installed():
        status = "" if plugins.is_enabled(plugin.name) else " (disabled)"
        print(f"{plugin.name}=={plugin.version}{status}")


@click.command(help="Enable a plugin")
@click.argument("plugin_names", metavar="plugin", nargs=-1)
@click.pass_obj
def enable(context: Context, plugin_names: List[str]) -> None:
    config = tutor_config.load_minimal(context.root)
    for plugin in plugin_names:
        plugins.enable(config, plugin)
        fmt.echo_info(f"Plugin {plugin} enabled")
    tutor_config.save_config_file(context.root, config)
    fmt.echo_info(
        "You should now re-generate your environment with `tutor config save`."
    )


@click.command(
    short_help="Disable a plugin",
    help="Disable one or more plugins. Specify 'all' to disable all enabled plugins at once.",
)
@click.argument("plugin_names", metavar="plugin", nargs=-1)
@click.pass_obj
def disable(context: Context, plugin_names: List[str]) -> None:
    config = tutor_config.load_minimal(context.root)
    disable_all = "all" in plugin_names
    for plugin in plugins.iter_enabled():
        if disable_all or plugin.name in plugin_names:
            fmt.echo_info(f"Disabling plugin {plugin.name}...")
            for key, value in plugin.config_set.items():
                value = tutor_env.render_unknown(config, value)
                fmt.echo_info(f"    Removing config entry {key}={value}")
            plugins.disable(config, plugin)
            delete_plugin(context.root, plugin.name)
            fmt.echo_info("    Plugin disabled")
    tutor_config.save_config_file(context.root, config)
    fmt.echo_info(
        "You should now re-generate your environment with `tutor config save`."
    )


def delete_plugin(root: str, name: str) -> None:
    plugin_dir = tutor_env.pathjoin(root, "plugins", name)
    if os.path.exists(plugin_dir):
        try:
            shutil.rmtree(plugin_dir)
        except PermissionError as e:
            raise exceptions.TutorError(
                f"Could not delete file {e.filename} from plugin {name} in folder {plugin_dir}"
            )


@click.command(
    short_help="Print the location of yaml-based plugins",
    help=f"""Print the location of yaml-based plugins. This location can be manually
defined by setting the {DictPlugin.ROOT_ENV_VAR_NAME} environment variable""",
)
def printroot() -> None:
    fmt.echo(DictPlugin.ROOT)


@click.command(
    short_help="Install a plugin",
    help=f"""Install a plugin, either from a local YAML file or a remote, web-hosted
location. The plugin will be installed to {DictPlugin.ROOT_ENV_VAR_NAME}.""",
)
@click.argument("location")
def install(location: str) -> None:
    basename = os.path.basename(location)
    if not basename.endswith(".yml"):
        basename += ".yml"
    plugin_path = os.path.join(DictPlugin.ROOT, basename)

    if location.startswith("http"):
        # Download file
        response = urllib.request.urlopen(location)
        content = response.read().decode()
    elif os.path.isfile(location):
        # Read file
        with open(location, encoding="utf-8") as f:
            content = f.read()
    else:
        raise exceptions.TutorError(f"No plugin found at {location}")

    # Save file
    if not os.path.exists(DictPlugin.ROOT):
        os.makedirs(DictPlugin.ROOT)
    with open(plugin_path, "w", newline="\n", encoding="utf-8") as f:
        f.write(content)
    fmt.echo_info(f"Plugin installed at {plugin_path}")


plugins_command.add_command(list_command)
plugins_command.add_command(enable)
plugins_command.add_command(disable)
plugins_command.add_command(printroot)
plugins_command.add_command(install)
