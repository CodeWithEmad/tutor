from typing import Iterator, List, Tuple

from . import filters


def iter_patches(patch_name: str) -> Iterator[Tuple[str, str]]:
    """
    TODO Document this.
    """
    filter_name = "env:patches"
    patches: List[Tuple[str, str]] = filters.apply_filter(filter_name, [], patch_name)
    yield from patches
