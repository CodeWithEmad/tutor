from unittest.mock import Mock, patch

from click.testing import CliRunner

from tests.helpers import TestContext, temporary_root, PluginsTestCase
from tutor import images, plugins
from tutor.__about__ import __version__
from tutor.commands.cli import cli
from tutor.commands.images import ImageNotFoundError


class ImagesTests(PluginsTestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()
        super().setUp()

    def test_images_help(self) -> None:
        result = self.runner.invoke(cli, ["images", "--help"])
        self.assertEqual(0, result.exit_code)
        self.assertIsNone(result.exception)

    def test_images_pull_image(self) -> None:
        with temporary_root() as root:
            context = TestContext(root)
            result = self.runner.invoke(cli, ["images", "pull"], obj=context)
            self.assertEqual(0, result.exit_code)
            self.assertIsNone(result.exception)

    def test_images_pull_plugin_invalid_plugin_should_throw_error(self) -> None:
        with temporary_root() as root:
            context = TestContext(root)
            result = self.runner.invoke(cli, ["images", "pull", "plugin"], obj=context)
            self.assertEqual(1, result.exit_code)
            self.assertEqual(ImageNotFoundError, type(result.exception))

    @patch.object(images, "pull", return_value=None)
    def test_images_pull_plugin(self, image_pull: Mock) -> None:
        plugin1 = plugins.v0.DictPlugin(
            {
                "name": "plugin1",
                "hooks": {
                    "remote-image": {
                        "service1": "service1:1.0.0",
                        "service2": "service2:2.0.0",
                    }
                },
            }
        )
        plugin1.enable()
        with temporary_root() as root:
            context = TestContext(root)
            result = self.runner.invoke(
                cli, ["images", "pull", "service1"], obj=context
            )
        self.assertIsNone(result.exception)
        self.assertEqual(0, result.exit_code)
        image_pull.assert_called_once_with("service1:1.0.0")

    def test_images_printtag_image(self) -> None:
        with temporary_root() as root:
            context = TestContext(root)
            result = self.runner.invoke(
                cli, ["images", "printtag", "openedx"], obj=context
            )
        self.assertEqual(0, result.exit_code)
        self.assertIsNone(result.exception)
        self.assertRegex(
            result.output, fr"docker.io/overhangio/openedx:{__version__}\n"
        )

    def test_images_printtag_plugin(self) -> None:
        plugin1 = plugins.v0.DictPlugin(
            {
                "name": "plugin1",
                "hooks": {
                    "build-image": {
                        "service1": "service1:1.0.0",
                        "service2": "service2:2.0.0",
                    }
                },
            }
        )
        plugin1.enable()
        with temporary_root() as root:
            context = TestContext(root)
            result = self.runner.invoke(
                cli, ["images", "printtag", "service1"], obj=context
            )
        self.assertIsNone(result.exception)
        self.assertEqual(0, result.exit_code, result)
        self.assertEqual(result.output, "service1:1.0.0\n")

    @patch.object(images, "build", return_value=None)
    def test_images_build_plugin(self, mock_image_build: Mock) -> None:
        plugin1 = plugins.v0.DictPlugin(
            {
                "name": "plugin1",
                "hooks": {
                    "build-image": {
                        "service1": "service1:1.0.0",
                        "service2": "service2:2.0.0",
                    }
                },
            }
        )
        plugin1.enable()
        with temporary_root() as root:
            context = TestContext(root)
            result = self.runner.invoke(
                cli, ["images", "build", "service1"], obj=context
            )
        self.assertIsNone(result.exception)
        self.assertEqual(0, result.exit_code)
        mock_image_build.assert_called()
        self.assertIn("service1:1.0.0", mock_image_build.call_args[0])

    @patch.object(images, "build", return_value=None)
    def test_images_build_plugin_with_args(self, image_build: Mock) -> None:
        plugin1 = plugins.v0.DictPlugin(
            {
                "name": "plugin1",
                "hooks": {
                    "build-image": {
                        "service1": "service1:1.0.0",
                        "service2": "service2:2.0.0",
                    }
                },
            }
        )
        plugin1.enable()
        build_args = [
            "images",
            "build",
            "--no-cache",
            "-a",
            "myarg=value",
            "--add-host",
            "host",
            "--target",
            "target",
            "-d",
            "docker_args",
            "service1",
        ]
        with temporary_root() as root:
            context = TestContext(root)
            result = self.runner.invoke(
                cli,
                build_args,
                obj=context,
            )
        self.assertEqual(0, result.exit_code)
        self.assertIsNone(result.exception)
        image_build.assert_called()
        self.assertIn("service1:1.0.0", image_build.call_args[0])
        for arg in image_build.call_args[0][2:]:
            # The only extra args are `--build-arg`
            if arg != "--build-arg":
                self.assertIn(arg, build_args)

    def test_images_push(self) -> None:
        with temporary_root() as root:
            context = TestContext(root)
            result = self.runner.invoke(cli, ["images", "push"], obj=context)
        self.assertEqual(0, result.exit_code)
        self.assertIsNone(result.exception)
