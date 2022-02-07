import unittest
from unittest.mock import Mock, patch


from tutor.plugins import actions


class PluginActionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.side_effect_int = 0

    @patch.object(actions.ActionsCache, "instance", return_value=actions.ActionsCache())
    def test_add(self, _mock_actions: Mock) -> None:
        @actions.add("test-action")
        def _test_action_1(increment: int) -> None:
            self.side_effect_int += increment

        @actions.add("test-action")
        def _test_action_2(increment: int) -> None:
            self.side_effect_int += increment * 2

        actions.do_action("test-action", 1)
        self.assertEqual(3, self.side_effect_int)

    @patch.object(actions.ActionsCache, "instance", return_value=actions.ActionsCache())
    def test_do_action_once(self, _mock_actions: Mock) -> None:
        @actions.add("test-action")
        def _test_action(increment: int) -> None:
            self.side_effect_int += increment

        actions.do_action_once("test-action", 10)
        actions.do_action_once("test-action", 10)
        self.assertEqual(10, self.side_effect_int)
