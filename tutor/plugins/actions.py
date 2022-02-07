from typing import Any, Callable, Dict, List, Set

# Similarly to CallableFilter, it should be possible to refine the definition of
# CallableAction in the future.
CallableAction = Callable[..., None]


class ActionsCache:
    """
    Singleton set of named actions.
    """

    INSTANCE = None

    @classmethod
    def instance(cls) -> "ActionsCache":
        if cls.INSTANCE is None:
            cls.INSTANCE = cls()
        return cls.INSTANCE

    def __init__(self) -> None:
        self.all: Dict[str, List[CallableAction]] = {}
        self.done: Set[str] = set()


def add(name: str) -> Callable[[CallableAction], CallableAction]:
    """
    TODO document me (along with other functions here)
    """

    def inner(action_func: CallableAction) -> CallableAction:
        if name not in ActionsCache.instance().all:
            ActionsCache.instance().all[name] = []
        ActionsCache.instance().all[name].append(action_func)
        return action_func

    return inner


def do_action(name: str, *args: Any, **kwargs: Any) -> None:
    for func in ActionsCache.instance().all.get(name, []):
        func(*args, **kwargs)
    ActionsCache.instance().done.add(name)


def do_action_once(name: str, *args: Any, **kwargs: Any) -> None:
    if name not in ActionsCache.instance().done:
        do_action(name, *args, **kwargs)


def clear_action(name: str) -> None:
    """
    Remove all hooks associated to an action name.

    This is a dangerous function that should only be called in tests.
    """
    try:
        ActionsCache.instance().all.pop(name)
    except KeyError:
        pass
