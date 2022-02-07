from typing import List
import unittest
from unittest.mock import Mock, patch

from tutor.plugins import filters


class PluginFiltersTests(unittest.TestCase):
    @patch.object(filters.FiltersCache, "instance", return_value=filters.FiltersCache())
    def test_add(self, _mock_filters: Mock) -> None:
        @filters.add("tests:count-sheeps")
        def filter1(value: int) -> int:
            return value + 1

        value = filters.apply_filter("tests:count-sheeps", 0)
        self.assertEqual(1, value)

    @patch.object(filters.FiltersCache, "instance", return_value=filters.FiltersCache())
    def test_add_items(self, _mock_filters: Mock) -> None:
        @filters.add("tests:add-sheeps")
        def filter1(sheeps: List[int]) -> List[int]:
            return sheeps + [0]

        filters.add_items("tests:add-sheeps", [1, 2])
        filters.add_items("tests:add-sheeps", [3, 4])

        sheeps: List[int] = filters.apply_filter("tests:add-sheeps", [])
        self.assertEqual([0, 1, 2, 3, 4], sheeps)
