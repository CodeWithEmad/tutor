# The goal of this module is to serve as the API to the plugins functionalities.
# Other modules must not have to bother about v0 or v1.
from copy import deepcopy
from typing import Dict, Iterator, List, Tuple, Union

from tutor import exceptions
from tutor.types import Config, get_typed

from . import actions, filters
from . import v0 as plugins_v0
from . import v1 as plugins_v1

# Key name under which plugins are listed
CONFIG_KEY = "PLUGINS"


def is_installed(name: str) -> bool:
    for plugin in iter_installed():
        if name == plugin.name:
            return True
    return False


def iter_installed() -> Iterator[plugins_v0.BasePlugin]:
    """
    Iterate on all installed plugins, sorted by name.

    This will yield all plugins, including those that have the same name.
    """
    plugins: List[plugins_v0.BasePlugin] = filters.apply_filter("plugins:installed", [])
    plugins.sort(key=lambda p: p.name)
    yield from plugins


def is_enabled(name: str) -> bool:
    for plugin in iter_enabled():
        if plugin.name == name:
            return True
    return False


def enable(config: Config, name: str) -> None:
    if not is_installed(name):
        raise exceptions.TutorError(f"plugin '{name}' is not installed.")
    if config.get(CONFIG_KEY) is None:
        config[CONFIG_KEY] = []
    enabled = get_typed(config, CONFIG_KEY, list, [])
    if name in enabled:
        return
    enabled.append(name)
    enabled.sort()


def disable(config: Config, plugin: plugins_v0.BasePlugin) -> None:
    # Remove plugin-specific set config
    for key in plugin.config_set.keys():
        config.pop(key, None)

    # Remove plugin from list of enabled plugins
    enabled = get_typed(config, CONFIG_KEY, list, [])
    while plugin.name in enabled:
        enabled.remove(plugin.name)


def get_enabled(name: str) -> plugins_v0.BasePlugin:
    for plugin in iter_enabled():
        if plugin.name == name:
            return plugin
    raise ValueError(f"Enabled plugin {name} could not be found.")


def iter_enabled() -> Iterator[plugins_v0.BasePlugin]:
    """
    Iterate on the list of enabled plugins, sorted by name.

    Note that enabled plugins are not deduplicated. Thus, if two plugins have
    the same name, both will be enabled.
    """
    plugins: List[plugins_v0.BasePlugin] = filters.apply_filter("plugins:enabled", [])
    plugins.sort(key=lambda p: p.name)
    yield from plugins


def iter_patches(name: str) -> Iterator[Tuple[str, str]]:
    """
    Yields: plugin_name (str), patch (str)
    """
    yield from plugins_v1.iter_patches(name)


def iter_hooks(
    hook_name: str,
) -> Iterator[Tuple[str, Union[Dict[str, str], List[str]]]]:
    """
    Yields: (plugin name, hook)
    """
    yield from filters.apply_filter("apps:tasks", [], hook_name)


@actions.add("load_user_config")
def _on_load_minimal_config(config: Config) -> None:
    """
    Load enabled plugins

    This action should be done once at the top of the main function.
    """
    actions.do_action("install_plugins")
    actions.do_action("enable_plugins", config.get(CONFIG_KEY, []))
