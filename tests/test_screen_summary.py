"""Regressions for the summarized screen and for serving recorded evidence.

The summary is what a model reads instead of the raw dump, so its job is
narrow: never offer a selector this server would refuse, and never hide that a
selector is ambiguous.
"""

import unittest

from contratos.mcp import HarnessError
from contratos.ui_control import validate_selector
from logica.evidencias.capturas import read_artifact_bytes
from logica.navegacion.resumen import summarize_ui_tree


SCREEN = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy rotation="0">
  <node class="android.widget.FrameLayout" package="com.android.settings" bounds="[0,0][1080,2400]">
    <node class="android.widget.TextView" text="All apps" bounds="[0,100][500,200]"/>
    <node class="androidx.recyclerview.widget.RecyclerView" scrollable="true" bounds="[0,200][1080,2400]">
      <node class="android.widget.LinearLayout" clickable="true" bounds="[0,200][1080,400]">
        <node class="android.widget.TextView" text="Calendar" bounds="[50,240][400,360]"/>
      </node>
      <node class="android.widget.LinearLayout" clickable="true" bounds="[0,400][1080,600]">
        <node class="android.widget.TextView" text="Clock" bounds="[50,440][400,560]"/>
      </node>
      <node class="android.widget.LinearLayout" clickable="true" bounds="[0,600][1080,800]">
        <node class="android.widget.TextView" text="Clock" bounds="[50,640][400,760]"/>
      </node>
    </node>
    <node class="android.widget.EditText" content-desc="Search" resource-id="com.android.settings:id/q" bounds="[0,0][1080,100]"/>
    <node class="android.widget.Switch" checkable="true" text="Wi-Fi" bounds="[0,800][1080,900]"/>
    <node class="android.widget.TextView" text="invisible" bounds="[0,0][0,0]"/>
  </node>
</hierarchy>
"""


class ScreenSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.summary = summarize_ui_tree(SCREEN)
        self.selectors = [action["selector"] for action in self.summary["actions"]]

    def test_every_offered_selector_is_one_this_server_accepts(self) -> None:
        """The whole point: the model gets back the vocabulary it must speak."""

        for selector in self.selectors:
            with self.subTest(selector=selector):
                self.assertEqual(validate_selector(selector).value, next(iter(selector.values())))

    def test_a_pressable_row_is_offered_by_the_words_it_shows(self) -> None:
        self.assertIn({"text": "Calendar"}, self.selectors)

    def test_a_repeated_label_is_reported_as_ambiguous(self) -> None:
        """Two rows say Clock; tapping by text is a coin toss and must say so."""

        clocks = [a for a in self.summary["actions"] if a["selector"] == {"text": "Clock"}]
        self.assertTrue(clocks)
        for entry in clocks:
            self.assertTrue(entry.get("ambiguous"))

    def test_a_unique_label_is_not_flagged(self) -> None:
        calendar = next(a for a in self.summary["actions"] if a["label"] == "Calendar")
        self.assertNotIn("ambiguous", calendar)

    def test_roles_separate_typing_from_pressing_from_toggling(self) -> None:
        roles = {action["label"]: action["role"] for action in self.summary["actions"]}
        self.assertEqual(roles["Search"], "input")
        self.assertEqual(roles["Wi-Fi"], "toggle")
        self.assertEqual(roles["Calendar"], "button")

    def test_a_resource_id_wins_over_weaker_identifiers(self) -> None:
        search = next(a for a in self.summary["actions"] if a["label"] == "Search")
        self.assertEqual(search["selector"], {"resource_id": "com.android.settings:id/q"})

    def test_scrolling_is_a_screen_fact_not_a_fake_target(self) -> None:
        """ui.scroll takes no selector, so a scrollable is never offered as one."""

        self.assertTrue(self.summary["can_scroll"])
        self.assertNotIn("scrollable", {a["role"] for a in self.summary["actions"]})

    def test_invisible_nodes_are_left_out(self) -> None:
        self.assertNotIn("invisible", self.summary["texts"])

    def test_the_words_on_screen_are_readable_without_the_dump(self) -> None:
        self.assertIn("All apps", self.summary["texts"])
        self.assertEqual(self.summary["foreground_package"], "com.android.settings")

    def test_a_broken_dump_is_a_typed_error(self) -> None:
        with self.assertRaises(HarnessError) as raised:
            summarize_ui_tree("<hierarchy><node")
        self.assertEqual(raised.exception.code.value, "UI_TREE_UNAVAILABLE")


class EvidenceResourceTests(unittest.TestCase):
    """Evidence is served by identifier, never by a path the caller composes."""

    def test_traversal_and_unknown_identifiers_are_refused(self) -> None:
        for hostile in (
            "../../README.md",
            "..\\..\\LICENSE",
            "/etc/passwd",
            "20260101-000000-000000-x.png/../../LICENSE",
            "screenshot.png",
            "",
            None,
            42,
        ):
            with self.subTest(artifact_id=hostile), self.assertRaises(HarnessError) as raised:
                read_artifact_bytes(hostile)
            self.assertEqual(raised.exception.code.value, "EVIDENCE_WRITE_FAILED")

    def test_a_well_shaped_but_absent_identifier_is_refused(self) -> None:
        with self.assertRaises(HarnessError):
            read_artifact_bytes("20260101-000000-000000-screen.png")
