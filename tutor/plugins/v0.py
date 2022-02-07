import importlib
import os
from glob import glob
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type, Union

import appdirs
import click
import pkg_resources

from tutor import exceptions, fmt, serialize
from tutor.__about__ import __app__
from tutor.types import Config

from . import actions, filters

# A v0 hook can be either a Dict or a List
# TODO can we simplify this by defining separate hook filters?
InitHook = List[str]
ImageHook = Dict[str, str]
Hook = Union[InitHook, ImageHook]


class BasePlugin:
    """
    Tutor plugins are defined by a name and an object that implements one or more of the
    following properties:

    `config` (dict str->dict(str->str)): contains "add", "defaults", "set" keys. Entries
    in these dicts will be added or override the global configuration. Keys in "add" and
    "defaults" will be prefixed by the plugin name in uppercase.

    `patches` (dict str->str): entries in this dict will be used to patch the rendered
    Tutor templates. For instance, to add "somecontent" to a template that includes '{{
    patch("mypatch") }}', set: `patches["mypatch"] = "somecontent"`. It is recommended
    to store all patches in separate files, and to dynamically list patches by listing
    the contents of a "patches"  subdirectory.

    `templates` (str): path to a directory that includes new template files for the
    plugin. It is recommended that all files in the template directory are stored in a
    `myplugin` folder to avoid conflicts with other plugins. Plugin templates are useful
    for content re-use, e.g: "{% include 'myplugin/mytemplate.html'}".

    `hooks` (dict str->list[str]): hooks are commands that will be run at various points
    during the lifetime of the platform. For instance, to run `service1` and `service2`
    in sequence during initialization, you should define:

        hooks["init"] = ["service1", "service2"]

    It is then assumed that there are `myplugin/hooks/service1/init` and
    `myplugin/hooks/service2/init` templates in the plugin `templates` directory.

    `command` (click.Command): if a plugin exposes a `command` attribute, users will be able to run it from the command line as `tutor pluginname`.
    """

    def __init__(self, name: str, loader: Optional[Any] = None) -> None:
        self.name = name
        self.loader = loader
        self.obj: Optional[Any] = None
        # TODO we can probably get rid of all these attributes if we register
        # all of them as actions/filters
        self.config: Dict[str, Config] = {}
        self.hooks: Dict[str, Hook] = {}
        self.templates_root: Optional[str] = None

    def install(self) -> "BasePlugin":
        """
        TODO document me
        """
        filters.add_item("plugins:installed", self)

        @actions.add("enable_plugins")
        def _enable(plugin_names: List[str]) -> None:
            """
            Load list of enabled plugins.

            Note: if there are multiple plugins with the same name, they will all be enabled.
            """
            if self.name in plugin_names:
                self.enable()

        return self

    def enable(self) -> "BasePlugin":
        """
        TODO document me
        TODO cleaner code

        This method is not called by the constructor, because it might be
        costly. Thus, we only call it for plugins that are actually enabled.
        """
        # Add self to enabled plugins
        filters.add_item("plugins:enabled", self)

        self.load_obj()
        self.load_config()
        self.load_patches()
        self.load_hooks()
        self.load_templates_root()
        self.load_command()

        return self

    def load_obj(self) -> None:
        """
        Override this method to write to the `obj` attribute.
        """
        raise NotImplementedError

    def load_config(self) -> None:
        """
        Load config and check types.
        """
        config = get_callable_attr(self.obj, "config", {})
        if not isinstance(config, dict):
            raise exceptions.TutorError(
                f"Invalid config in plugin {self.name}. Expected dict, got {config.__class__}."
            )
        for name, subconfig in config.items():
            if not isinstance(name, str):
                raise exceptions.TutorError(
                    f"Invalid config entry '{name}' in plugin {self.name}. Expected str, got {config.__class__}."
                )
            if not isinstance(subconfig, dict):
                raise exceptions.TutorError(
                    f"Invalid config entry '{name}' in plugin {self.name}. Expected str keys, got {config.__class__}."
                )
            for key in subconfig.keys():
                if not isinstance(key, str):
                    raise exceptions.TutorError(
                        f"Invalid config entry '{name}.{key}' in plugin {self.name}. Expected str, got {key.__class__}."
                    )
        self.config = config

    def load_patches(self) -> None:
        """
        Load patches and check the types are right.
        """
        patches = get_callable_attr(self.obj, "patches", {})
        if not isinstance(patches, dict):
            raise exceptions.TutorError(
                f"Invalid patches in plugin {self.name}. Expected dict, got {patches.__class__}."
            )
        for patch_name, content in patches.items():
            if not isinstance(patch_name, str):
                raise exceptions.TutorError(
                    f"Invalid patch name '{patch_name}' in plugin {self.name}. Expected str, got {patch_name.__class__}."
                )
            if not isinstance(content, str):
                raise exceptions.TutorError(
                    f"Invalid patch '{patch_name}' in plugin {self.name}. Expected str, got {content.__class__}."
                )

        @filters.add("env:patches")
        def _env_patches(
            all_patches: List[Tuple[str, str]], patch_name: str
        ) -> List[Tuple[str, str]]:
            patch = patches.get(patch_name) if patches else None
            if patch is not None:
                all_patches.append((self.name, patch))
            return all_patches

    def load_hooks(self) -> None:
        """
        Load hooks and check types.

        Returns {"hook name": Hook}
        """
        hooks = get_callable_attr(self.obj, "hooks", default={})
        if not isinstance(hooks, dict):
            raise exceptions.TutorError(
                f"Invalid hooks in plugin {self.name}. Expected dict, got {hooks.__class__}."
            )
        for hook_name, hook in hooks.items():
            if not isinstance(hook_name, str):
                raise exceptions.TutorError(
                    f"Invalid hook name '{hook_name}' in plugin {self.name}. Expected str, got {hook_name.__class__}."
                )
            if isinstance(hook, list):
                for service in hook:
                    if not isinstance(service, str):
                        raise exceptions.TutorError(
                            f"Invalid service in hook '{hook_name}' from plugin {self.name}. Expected str, got {service.__class__}."
                        )
            elif isinstance(hook, dict):
                for name, value in hook.items():
                    if not isinstance(name, str) or not isinstance(value, str):
                        raise exceptions.TutorError(
                            f"Invalid hook '{hook_name}' in plugin {self.name}. Only str -> str entries are supported."
                        )
            else:
                raise exceptions.TutorError(
                    f"Invalid hook '{hook_name}' in plugin {self.name}. Expected dict or list, got {hook.__class__}."
                )
        self.hooks = hooks

        @filters.add("apps:tasks")
        def _app_tasks(
            triggers: List[Tuple[str, Hook]],
            trigger_name: str,
        ) -> List[Tuple[str, Hook]]:
            """
            TODO better filter name.

            Yields: (plugin name, hook)
            """
            hook: Optional[Hook] = self.hooks.get(trigger_name)
            if hook:
                triggers.append((self.name, hook))
            return triggers

    def load_templates_root(self) -> None:
        templates_root = get_callable_attr(self.obj, "templates", default=None)
        if templates_root is not None:
            assert isinstance(templates_root, str)
            # TODO other places make use of the templates_root attribute, which is actually useless
            filters.add_item("env:templates:roots", templates_root)
        self.templates_root = templates_root

    def load_command(self) -> None:
        command = getattr(self.obj, "command", None)
        if command is not None:
            assert isinstance(command, click.Command)
            # We force the command name to the plugin name
            command.name = self.name
            filters.add_item("cli:commands", command)

    def config_key(self, key: str) -> str:
        """
        Config keys in the "add" and "defaults" dicts should be prefixed by the plugin name, in uppercase.
        """
        return self.name.upper() + "_" + key

    # TODO all config properties should be moved to filters

    @property
    def config_add(self) -> Config:
        return self.config.get("add", {})

    @property
    def config_set(self) -> Config:
        return self.config.get("set", {})

    @property
    def config_defaults(self) -> Config:
        return self.config.get("defaults", {})

    @property
    def version(self) -> str:
        raise NotImplementedError

    @classmethod
    def iter_all(cls) -> Iterator["BasePlugin"]:
        """
        TODO do we really need this? if yes, document this.
        """
        yield from []


class EntrypointPlugin(BasePlugin):
    """
    Entrypoint plugins are regular python packages that have a 'tutor.plugin.v0' entrypoint.

    The API for Tutor plugins is currently in development. The entrypoint will switch to
    'tutor.plugin.v1' once it is stabilised.
    """

    ENTRYPOINT = "tutor.plugin.v0"

    def __init__(self, entrypoint: pkg_resources.EntryPoint) -> None:
        self.loader: pkg_resources.EntryPoint
        super().__init__(entrypoint.name, entrypoint)

    def load_obj(self) -> None:
        self.obj = self.loader.load()

    @property
    def version(self) -> str:
        if not self.loader.dist:
            return "0.0.0"
        return self.loader.dist.version

    @classmethod
    def iter_all(cls) -> Iterator["EntrypointPlugin"]:
        for entrypoint in pkg_resources.iter_entry_points(cls.ENTRYPOINT):
            try:
                error: Optional[str] = None
                yield cls(entrypoint)
            except pkg_resources.VersionConflict as e:
                error = e.report()
            except Exception as e:  # pylint: disable=broad-except
                error = str(e)
            if error:
                fmt.echo_error(
                    f"Failed to load entrypoint '{entrypoint.name} = {entrypoint.module_name}' from distribution {entrypoint.dist}: {error}"
                )


class OfficialPlugin(BasePlugin):
    """
    Official plugins have a "plugin" module which exposes a __version__ attribute.
    Official plugins should be manually added by calling `OfficialPlugin('name').install()`.
    """

    def load_obj(self) -> None:
        self.obj = importlib.import_module(f"tutor{self.name}.plugin")

    @property
    def version(self) -> str:
        version = importlib.import_module(f"tutor{self.name}.__about__").__version__
        if not isinstance(version, str):
            raise TypeError("OfficialPlugin __version__ must be 'str'")
        return version


class DictPlugin(BasePlugin):
    # Name of the environment variable that stores the path to the yaml plugin root.
    ROOT_ENV_VAR_NAME = "TUTOR_PLUGINS_ROOT"
    ROOT = os.path.expanduser(
        os.environ.get(ROOT_ENV_VAR_NAME, "")
    ) or appdirs.user_data_dir(appname=__app__ + "-plugins")

    def __init__(self, data: Config):
        self.loader: Config
        name = data["name"]
        if not isinstance(name, str):
            raise exceptions.TutorError(
                f"Invalid plugin name: '{name}'. Expected str, got {name.__class__}"
            )
        super().__init__(name, data)

    def load_obj(self) -> None:
        # Create a generic object (sort of a named tuple) which will contain all
        # key/values from data
        class Module:
            pass

        self.obj = Module()
        for key, value in self.loader.items():
            setattr(self.obj, key, value)

    @property
    def version(self) -> str:
        version = self.loader["version"]
        if not isinstance(version, str):
            raise TypeError("DictPlugin.version must be str")
        return version

    @classmethod
    def iter_all(cls) -> Iterator[BasePlugin]:
        for path in glob(os.path.join(cls.ROOT, "*.yml")):
            with open(path, encoding="utf-8") as f:
                data = serialize.load(f)
                if not isinstance(data, dict):
                    raise exceptions.TutorError(
                        f"Invalid plugin: {path}. Expected dict."
                    )
                try:
                    yield cls(data)
                except KeyError as e:
                    raise exceptions.TutorError(
                        f"Invalid plugin: {path}. Missing key: {e.args[0]}"
                    )


@actions.add("install_plugins")
def _install_v0_plugins() -> None:
    """
    TODO document me
    """
    classes: List[Type[BasePlugin]] = [EntrypointPlugin, OfficialPlugin, DictPlugin]
    for PluginClass in classes:
        for plugin in PluginClass.iter_all():
            plugin.install()


def get_callable_attr(
    plugin: Any, attr_name: str, default: Optional[Any] = None
) -> Optional[Any]:
    """
    Return the attribute of a plugin. If this attribute is a callable, return
    the return value instead.
    """
    attr = getattr(plugin, attr_name, default)
    if callable(attr):
        attr = attr()  # pylint: disable=not-callable
    return attr
