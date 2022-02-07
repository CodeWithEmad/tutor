from unittest.mock import patch

from tutor import config as tutor_config
from tutor import exceptions, fmt, plugins
from tutor.plugins import v0 as plugins_v0
from tutor.plugins import actions
from tutor.types import Config, get_typed

from tests.helpers import PluginsTestCase


class PluginsTests(PluginsTestCase):
    def test_iter_installed(self) -> None:
        self.assertEqual([], list(plugins.iter_installed()))

    def test_is_installed(self) -> None:
        self.assertFalse(plugins.is_installed("dummy"))

    def test_official_plugins(self) -> None:
        # Create 2 official plugins
        plugin1 = plugins_v0.OfficialPlugin("plugin1").install()
        plugin2 = plugins_v0.OfficialPlugin("plugin2").install()
        self.assertEqual(
            [plugin1, plugin2],
            list(plugins.iter_installed()),
        )

    def test_enable(self) -> None:
        config: Config = {plugins.CONFIG_KEY: []}
        plugins_v0.OfficialPlugin("plugin1").install()
        plugins_v0.OfficialPlugin("plugin2").install()
        plugins.enable(config, "plugin2")
        plugins.enable(config, "plugin1")
        self.assertEqual(["plugin1", "plugin2"], config[plugins.CONFIG_KEY])

    def test_enable_twice(self) -> None:
        config: Config = {plugins.CONFIG_KEY: []}
        plugins_v0.OfficialPlugin("plugin1").install()
        plugins.enable(config, "plugin1")
        plugins.enable(config, "plugin1")
        self.assertEqual(["plugin1"], config[plugins.CONFIG_KEY])

    def test_enable_not_installed_plugin(self) -> None:
        config: Config = {"PLUGINS": []}
        self.assertRaises(exceptions.TutorError, plugins.enable, config, "plugin1")

    def test_disable(self) -> None:
        plugins.plugins_v0.DictPlugin(
            {
                "name": "plugin1",
                "version": "1.0.0",
                "config": {"set": {"KEY": "value"}},
            }
        ).install()
        plugins.plugins_v0.DictPlugin(
            {
                "name": "plugin2",
                "version": "1.0.0",
            }
        ).install()
        config: Config = {"PLUGINS": ["plugin1", "plugin2"]}
        actions.do_action("load_user_config", config)
        with patch.object(fmt, "STDOUT"):
            plugin = plugins.get_enabled("plugin1")
            plugins.disable(config, plugin)
        self.assertEqual(["plugin2"], config["PLUGINS"])

    def test_disable_removes_set_config(self) -> None:
        plugins.plugins_v0.DictPlugin(
            {
                "name": "plugin1",
                "version": "1.0.0",
                "config": {"set": {"KEY": "value"}},
            }
        ).install()
        config: Config = {"PLUGINS": ["plugin1"], "KEY": "value"}
        actions.do_action("load_user_config", config)
        plugin = plugins.get_enabled("plugin1")
        with patch.object(fmt, "STDOUT"):
            plugins.disable(config, plugin)
        self.assertEqual([], config["PLUGINS"])
        self.assertNotIn("KEY", config)

    def test_patches(self) -> None:
        plugins_v0.DictPlugin(
            {"name": "plugin1", "patches": {"patch1": "Hello {{ ID }}"}}
        ).enable()
        patches = list(plugins.iter_patches("patch1"))
        self.assertEqual([("plugin1", "Hello {{ ID }}")], patches)

    def test_plugin_without_patches(self) -> None:
        plugins.plugins_v0.DictPlugin({"name": "plugin1"}).enable()
        patches = list(plugins.iter_patches("patch1"))
        self.assertEqual([], patches)

    def test_configure(self) -> None:
        plugins_v0.DictPlugin(
            {
                "name": "plugin1",
                "config": {
                    "add": {"PARAM1": "value1", "PARAM2": "value2"},
                    "set": {"PARAM3": "value3"},
                    "defaults": {"PARAM4": "value4"},
                },
            }
        ).enable()

        base = tutor_config.get_base()
        defaults = tutor_config.get_defaults()

        self.assertEqual(base["PARAM3"], "value3")
        self.assertEqual(base["PLUGIN1_PARAM1"], "value1")
        self.assertEqual(base["PLUGIN1_PARAM2"], "value2")
        self.assertEqual(defaults["PLUGIN1_PARAM4"], "value4")

    def test_configure_set_does_not_override(self) -> None:
        config: Config = {"ID1": "oldid"}

        plugins_v0.DictPlugin(
            {"name": "plugin1", "config": {"set": {"ID1": "newid", "ID2": "id2"}}}
        ).enable()
        tutor_config.update_with_base(config)

        self.assertEqual("oldid", config["ID1"])
        self.assertEqual("id2", config["ID2"])

    def test_configure_set_random_string(self) -> None:
        plugins_v0.DictPlugin(
            {
                "name": "plugin1",
                "config": {"set": {"PARAM1": "{{ 128|random_string }}"}},
            }
        ).enable()
        config = tutor_config.get_base()
        tutor_config.render_full(config)

        self.assertEqual(128, len(get_typed(config, "PARAM1", str)))

    def test_configure_default_value_with_previous_definition(self) -> None:
        config: Config = {"PARAM1": "value"}
        plugins_v0.DictPlugin(
            {"name": "plugin1", "config": {"defaults": {"PARAM2": "{{ PARAM1 }}"}}}
        ).enable()
        tutor_config.update_with_defaults(config)
        self.assertEqual("{{ PARAM1 }}", config["PLUGIN1_PARAM2"])

    def test_config_load_from_plugins(self) -> None:
        config: Config = {}

        plugins_v0.DictPlugin(
            {"name": "plugin1", "config": {"add": {"PARAM1": "{{ 10|random_string }}"}}}
        ).enable()

        tutor_config.update_with_base(config)
        tutor_config.update_with_defaults(config)
        tutor_config.render_full(config)
        value1 = get_typed(config, "PLUGIN1_PARAM1", str)

        self.assertEqual(10, len(value1))

    def test_hooks(self) -> None:
        plugins_v0.DictPlugin(
            {"name": "plugin1", "hooks": {"init": ["myclient"]}}
        ).enable()
        self.assertEqual([("plugin1", ["myclient"])], list(plugins.iter_hooks("init")))

    def test_plugins_are_updated_on_config_change(self) -> None:
        config: Config = {}
        plugins_v0.DictPlugin({"name": "plugin1"}).install()
        actions.do_action("load_user_config", config)
        plugins1 = list(plugins.iter_enabled())
        config["PLUGINS"] = ["plugin1"]
        actions.do_action("load_user_config", config)
        plugins2 = list(plugins.iter_enabled())

        self.assertEqual([], plugins1)
        self.assertEqual(1, len(plugins2))

    def test_dict_plugin(self) -> None:
        plugin = plugins.plugins_v0.DictPlugin(
            {"name": "myplugin", "config": {"set": {"KEY": "value"}}, "version": "0.1"}
        )
        plugin.enable()
        self.assertEqual("myplugin", plugin.name)
        self.assertEqual({"KEY": "value"}, plugin.config_set)
