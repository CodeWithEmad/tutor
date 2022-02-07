from typing import Any, Callable, Dict, List, TypeVar

from tutor import fmt

# For now, this signature is not very restrictive. In the future, we could improve it by writing:
#
# P = ParamSpec("P")
# CallableFilter = Callable[Concatenate[T, P], T]
#
# See PEP-612: https://www.python.org/dev/peps/pep-0612/
# Unfortunately, this piece of code fails because of a bug in mypy:
# https://github.com/python/mypy/issues/11833
# https://github.com/python/mypy/issues/8645
# https://github.com/python/mypy/issues/5876
# https://github.com/python/typing/issues/696
T = TypeVar("T")
CallableFilter = Callable[..., Any]


# TODO the list of filters should be hardcoded as static variables in a separate module and documented (same for actions)


class FiltersCache:
    """
    Singleton set of named filters.
    """

    INSTANCE = None

    @classmethod
    def instance(cls) -> "FiltersCache":
        if cls.INSTANCE is None:
            cls.INSTANCE = cls()
        return cls.INSTANCE

    def __init__(self) -> None:
        self.filters: Dict[str, List[CallableFilter]] = {}


def add(name: str) -> Callable[[CallableFilter], CallableFilter]:
    """
    Decorator for functions that will be applied to a single named filter.

    The return value of each filter function will be passed as the first argument of the next one.

    Usage:

        @filters.add("my-filter")
        def my_func(value, some_other_arg):
            # Do something with `value`
            ...
            return value

    TODO use python decorator to make it easier to troubleshoot on error
    """

    def inner(func: CallableFilter) -> CallableFilter:
        if name not in FiltersCache.instance().filters:
            FiltersCache.instance().filters[name] = []
        FiltersCache.instance().filters[name].append(func)

        return func

    return inner


def add_item(name: str, item: T) -> None:
    """
    TODO explain me
    """
    add_items(name, [item])


def add_items(name: str, items: List[T]) -> None:
    """
    TODO explain me
    """

    @add(name)
    def callback(value: List[T], *_args: Any, **_kwargs: Any) -> List[T]:
        return value + items


def apply_filter(name: str, value: T, *args: Any, **kwargs: Any) -> T:
    """
    Apply all declared filters to a single value, passing along the additional arguments.
    """
    for func in FiltersCache.instance().filters.get(name, []):
        try:
            value = func(value, *args, **kwargs)
        except:
            fmt.echo_error(f"Error applying {func} for filter '{name}'")
            raise
    return value


def clear_filter(name: str) -> None:
    """
    Clear any previously defined filter with the given name.

    This is a dangerous function that should only be called in tests.
    """
    FiltersCache.instance().filters.get(name, []).clear()
