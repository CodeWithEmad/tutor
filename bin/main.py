#!/usr/bin/env python3
from tutor.commands.cli import main
from tutor.plugins.v0 import OfficialPlugin

# Manually install plugins (this is for creating the bundle)
for plugin_name in [
    "android",
    "discovery",
    "ecommerce",
    "forum",
    "license",
    "mfe",
    "minio",
    "notes",
    "richie",
    "webui",
    "xqueue",
]:
    try:
        OfficialPlugin(plugin_name).install()
    except ImportError:
        pass

if __name__ == "__main__":
    main()
