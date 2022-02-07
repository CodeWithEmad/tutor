from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from . import exceptions

ConfigValue = Union[
    str, float, None, bool, List[str], List[Any], Dict[str, Any], Dict[Any, Any]
]
Config = Dict[str, ConfigValue]


def cast_config(config: Any) -> Config:
    if not isinstance(config, dict):
        raise exceptions.TutorError(
            f"Invalid configuration: expected dict, got {config.__class__}"
        )
    for key in config.keys():
        if not isinstance(key, str):
            raise exceptions.TutorError(
                f"Invalid configuration: expected str, got {key.__class__} for key '{key}'"
            )
    return config


T = TypeVar("T")


def get_typed(
    config: Config, key: str, expected_type: Type[T], default: Optional[T] = None
) -> T:
    value = config.get(key, default)
    if not isinstance(value, expected_type):
        raise exceptions.TutorError(
            "Invalid config entry: expected {expected_type.__name__}, got {value.__class__} for key '{key}'"
        )
    return value
