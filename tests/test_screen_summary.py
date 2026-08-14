"""Regressions for the summarized screen and for serving recorded evidence.

The summary is what a model reads instead of the raw dump, so its job is
narrow: never offer a selector this server would refuse, and never hide that a
selector is ambiguous.
"""

import unittest

from contratos.mcp import HarnessError
from contratos.ui_control import selector_mapping, validate_selector
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


CONTEXTUAL_DUPLICATES = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy>
  <node class="android.widget.FrameLayout" package="com.example" bounds="[0,0][1080,2400]">
    <node content-desc="Personal profile" bounds="[0,100][1080,500]">
      <node class="android.widget.LinearLayout" clickable="true" bounds="[0,100][1080,300]">
        <node class="android.widget.TextView" text="Save" bounds="[30,140][300,240]"/>
      </node>
    </node>
    <node content-desc="Work profile" bounds="[0,500][1080,900]">
      <node class="android.widget.LinearLayout" clickable="true" bounds="[0,500][1080,700]">
        <node class="android.widget.TextView" text="Save" bounds="[30,540][300,640]"/>
      </node>
    </node>
  </node>
</hierarchy>
"""


DESCENDANT_ACCESSIBILITY_LABEL = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy>
  <node class="android.widget.FrameLayout" package="com.android.settings" bounds="[0,0][1080,2400]">
    <node class="android.widget.LinearLayout" clickable="true" bounds="[0,0][120,120]">
      <node class="android.widget.ImageView" content-desc="Navigate up" bounds="[0,0][120,120]"/>
    </node>
  </node>
</hierarchy>
"""


HINT_ONLY_FIELD = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy>
  <node class="android.widget.FrameLayout" package="com.example.compra" bounds="[0,0][1080,2400]">
    <node class="android.widget.EditText" hint="¿Qué necesitas comprar?" clickable="true" focusable="true" bounds="[42,1900][1038,2100]"/>
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

    def test_descendant_accessibility_label_keeps_its_real_selector_kind(self) -> None:
        """A parent button must not relabel a child accessibility node as text."""

        actions = summarize_ui_tree(DESCENDANT_ACCESSIBILITY_LABEL)["actions"]

        self.assertEqual(actions[0]["label"], "Navigate up")
        self.assertEqual(actions[0]["selector"], {"content_desc": "Navigate up"})

    def test_hint_only_field_is_offered_for_semantic_text_input(self) -> None:
        """A field with no id or label must still be writable by its hint."""

        actions = summarize_ui_tree(HINT_ONLY_FIELD)["actions"]

        self.assertEqual(actions[0]["role"], "input")
        self.assertEqual(
            actions[0]["selector"], {"input_hint": "¿Qué necesitas comprar?"}
        )

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


class ContextualSelectorTests(unittest.TestCase):
    """Repeated labels become actionable only when the hierarchy proves context."""

    def setUp(self) -> None:
        self.actions = summarize_ui_tree(CONTEXTUAL_DUPLICATES)["actions"]

    def test_summary_anchors_repeated_labels_by_unique_semantic_ancestor(self) -> None:
        selectors = [action["selector"] for action in self.actions]

        self.assertIn(
            {"text": "Save", "within": {"content_desc": "Personal profile"}},
            selectors,
        )
        self.assertIn(
            {"text": "Save", "within": {"content_desc": "Work profile"}},
            selectors,
        )
        self.assertTrue(all(action.get("disambiguated") for action in self.actions))
        self.assertFalse(any(action.get("ambiguous") for action in self.actions))

    def test_contextual_selector_is_accepted_and_becomes_ancestor_xpath(self) -> None:
        from logica.navegacion.semantica import _locator

        raw = {"text": "Save", "within": {"content_desc": "Personal profile"}}
        selector = validate_selector(raw)
        _, query = _locator(selector)

        self.assertEqual(selector_mapping(selector), raw)
        self.assertIn("@text='Save'", query)
        self.assertIn("ancestor::*[@content-desc='Personal profile']", query)

    def test_context_cannot_be_nested_or_replace_the_target(self) -> None:
        invalid = (
            {"within": {"text": "Profile"}},
            {"text": "Save", "within": {"text": "Profile", "within": {"text": "Root"}}},
        )
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(HarnessError) as raised:
                validate_selector(raw)
            self.assertEqual(raised.exception.code.value, "INVALID_SELECTOR")

class LayoutAuditTests(unittest.TestCase):
    """Position is reported so layout can be checked, never so it can be aimed at."""

    def setUp(self) -> None:
        # 420 dpi, so Android's 48 dp minimum touch target is 126 px.
        self.summary = summarize_ui_tree(SCREEN, density=420)

    def test_position_is_reported_for_auditing(self) -> None:
        calendar = next(a for a in self.summary["actions"] if a["label"] == "Calendar")
        self.assertEqual(
            calendar["bounds"], {"left": 0, "top": 200, "width": 1080, "height": 200}
        )
        self.assertEqual(self.summary["screen"], {"width": 1080, "height": 2400})

    def test_position_is_never_accepted_back_as_a_selector(self) -> None:
        for action in self.summary["actions"]:
            self.assertNotIn("bounds", action["selector"])

    def test_a_control_smaller_than_a_fingertip_is_reported(self) -> None:
        tiny = summarize_ui_tree(
            SCREEN.replace('text="Wi-Fi" bounds="[0,800][1080,900]"',
                           'text="Wi-Fi" bounds="[0,800][40,840]"'),
            density=420,
        )
        issues = [f for f in tiny["layout_findings"] if f["issue"] == "touch_target_too_small"]
        self.assertEqual([f["selector"] for f in issues], [{"text": "Wi-Fi"}])

    def test_a_wide_row_clipped_by_scrolling_is_not_called_tiny(self) -> None:
        """The objective is zero false positives, so only the unambiguous counts."""

        clipped = summarize_ui_tree(
            SCREEN.replace('bounds="[0,200][1080,400]"', 'bounds="[0,200][1080,284]"'),
            density=420,
        )
        self.assertEqual(
            [f for f in clipped["layout_findings"] if f["issue"] == "touch_target_too_small"],
            [],
        )

    def test_an_element_outside_the_display_is_reported(self) -> None:
        outside = summarize_ui_tree(
            SCREEN.replace('bounds="[0,400][1080,600]"', 'bounds="[0,2500][1080,2700]"'),
            density=420,
        )
        self.assertIn("off_screen", [f["issue"] for f in outside["layout_findings"]])

    def test_a_healthy_screen_reports_nothing(self) -> None:
        self.assertEqual(self.summary["layout_findings"], [])

    def test_without_density_sizes_are_not_judged(self) -> None:
        """Guessing dp from pixels would invent findings, so it is not attempted."""

        blind = summarize_ui_tree(SCREEN)
        self.assertEqual(
            [f for f in blind["layout_findings"] if f["issue"] == "touch_target_too_small"],
            [],
        )


class InputHintLocatorTests(unittest.TestCase):
    """A field's hint lives in a different place on each Android release.

    Found by looking at the failure evidence from a CI run on API 34: the search
    bar was open and drawing "Search...", but the locator only accepted a Compose
    style child carrying content-desc, so it matched nothing.
    """

    def setUp(self) -> None:
        from logica.navegacion.semantica import _locator

        self.by, self.query = _locator(validate_selector({"input_hint": "Search"}))

    def test_it_looks_where_every_android_toolkit_puts_the_hint(self) -> None:
        for attribute in ("@hint", "@content-desc", "@text"):
            with self.subTest(attribute=attribute):
                self.assertIn(f"contains({attribute}, 'Search')", self.query)
        self.assertIn(".//*[contains(@content-desc, 'Search')", self.query)

    def test_it_matches_a_text_field_by_suffix_not_by_exact_class(self) -> None:
        """AppCompatEditText is still an edit text; demanding equality was a bug."""

        self.assertIn("string-length(@class) - 7) = 'EditText'", self.query)

    def test_hint_attribute_falls_back_to_element_inspection_when_xpath_cannot_read_it(self) -> None:
        """UiAutomator2 renders hint but does not always XPath-index it."""

        from logica.navegacion.semantica import _find_input_hint

        class Element:
            def __init__(self, attributes: dict[str, str], children: list[object] | None = None) -> None:
                self.attributes = attributes
                self.children = children or []

            def get_attribute(self, attribute: str) -> str:
                return self.attributes.get(attribute, "")

            def find_elements(self, _by: str, _query: str) -> list[object]:
                return self.children

        field = Element({"hint": "¿Qué necesitas comprar?"})

        class Driver:
            def find_elements(self, _by: str, _query: str) -> list[object]:
                return [field]

        self.assertIs(_find_input_hint(Driver(), "¿Qué necesitas"), field)

    def test_a_hostile_hint_stays_a_quoted_literal(self) -> None:
        from logica.navegacion.semantica import _locator

        _, query = _locator(validate_selector({"input_hint": "']|//*|//*['"}))
        self.assertIn('"\']|//*|//*[\'"', query)


class NotFoundIsActionableTests(unittest.TestCase):
    """A dead end that names the alternatives is a retry, not a dead end."""

    class _Driver:
        def __init__(self, source: str) -> None:
            self.page_source = source

    def test_the_message_names_what_the_screen_does_offer(self) -> None:
        from logica.navegacion.semantica import _offered_instead

        offered = _offered_instead(self._Driver(SCREEN))

        self.assertIn("'Calendar' (button)", offered)
        self.assertIn("'Search' (input)", offered)

    def test_a_broken_page_source_never_masks_the_real_error(self) -> None:
        from logica.navegacion.semantica import _offered_instead

        self.assertEqual(_offered_instead(self._Driver("<not xml")), "")

    def test_the_list_stays_bounded(self) -> None:
        from logica.navegacion.semantica import _offered_instead

        rows = "".join(
            f'<node class="android.widget.Button" clickable="true" text="Item {i}" '
            f'bounds="[0,{i * 10}][100,{i * 10 + 9}]"/>'
            for i in range(40)
        )
        crowded = f'<hierarchy><node package="x" bounds="[0,0][100,999]">{rows}</node></hierarchy>'

        self.assertIn("and 30 more", _offered_instead(self._Driver(crowded)))


APPIUM_SOURCE = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy rotation="0" width="1080" height="2400">
  <android.widget.FrameLayout package="com.android.settings" bounds="[0,0][1080,2400]">
    <android.widget.EditText content-desc="Search settings" bounds="[0,100][1080,220]"/>
    <android.widget.LinearLayout clickable="true" bounds="[0,300][1080,500]">
      <android.widget.TextView text="Calendar" bounds="[50,340][400,460]"/>
    </android.widget.LinearLayout>
  </android.widget.FrameLayout>
</hierarchy>
"""


class BothDumpShapesTests(unittest.TestCase):
    """uiautomator names every element <node>; Appium names it after its class.

    The diagnostic that lists what a screen offers came back empty in CI for
    exactly this reason: it was reading Appium's page source with a parser that
    only ever looked for <node>.
    """

    def setUp(self) -> None:
        self.summary = summarize_ui_tree(APPIUM_SOURCE)

    def test_appium_page_source_is_understood(self) -> None:
        self.assertEqual(self.summary["foreground_package"], "com.android.settings")
        self.assertIn("Calendar", self.summary["texts"])

    def test_roles_survive_the_other_shape(self) -> None:
        roles = {a["label"]: a["role"] for a in self.summary["actions"]}
        self.assertEqual(roles["Search settings"], "input")
        self.assertEqual(roles["Calendar"], "button")

    def test_the_uiautomator_shape_still_wins_when_present(self) -> None:
        self.assertEqual(summarize_ui_tree(SCREEN)["foreground_package"], "com.android.settings")


class LocatorAgreesWithTheSummaryTests(unittest.TestCase):
    """The summary must never offer a target the locator then cannot find.

    On API 34 the summary listed 'Search...' as an input while the locator
    matched nothing, because the summary reads a descendant's text and the
    locator only read a descendant's content-desc. Advertising a door and then
    denying it exists is the worst failure this harness can produce.
    """

    FIELD = """<?xml version='1.0' encoding='UTF-8'?>
    <hierarchy>
      <node class="android.widget.FrameLayout" package="com.x" bounds="[0,0][1080,2400]">
        <node class="androidx.appcompat.widget.AppCompatEditText" bounds="[0,0][1080,120]">
          <node class="android.widget.TextView" text="Search&#8230;" bounds="[10,10][500,110]"/>
        </node>
      </node>
    </hierarchy>
    """

    def test_the_summary_calls_it_an_input(self) -> None:
        actions = summarize_ui_tree(self.FIELD)["actions"]
        self.assertEqual([a["role"] for a in actions], ["input"])

    def test_the_locator_looks_where_the_summary_looked(self) -> None:
        from logica.navegacion.semantica import _locator

        _, query = _locator(validate_selector({"input_hint": "Search"}))

        self.assertIn("contains(@text, 'Search')])]", query)
        self.assertIn("string-length(@class) - 7) = 'EditText'", query)


class KeyboardCoverageTests(unittest.TestCase):
    """A target hidden behind the keyboard is there, and is not reachable.

    Found driving a real app: ui.get_tree listed the bottom navigation while
    ui.tap could not touch it, because the dump describes the app window as if
    the keyboard were not over it. Removing those targets would be a lie of
    omission; saying nothing was the bug. They are reported, and flagged.
    """

    # The real inset Android reported while the bug was being reproduced, scaled
    # to this fixture so that it covers its lower rows and nothing else.
    KEYBOARD = (0, 550, 1080, 2400)

    def test_a_target_under_the_keyboard_is_flagged_not_hidden(self) -> None:
        summary = summarize_ui_tree(SCREEN, density=420, keyboard=self.KEYBOARD)
        covered = [a for a in summary["actions"] if a.get("covered_by_keyboard")]
        visible = [a for a in summary["actions"] if not a.get("covered_by_keyboard")]

        self.assertTrue(covered, "nothing was flagged as covered")
        self.assertTrue(visible, "everything was flagged as covered")
        self.assertEqual(summary["keyboard"], {"open": True, "top": 550})

    def test_the_wi_fi_switch_at_the_bottom_is_the_one_covered(self) -> None:
        summary = summarize_ui_tree(SCREEN, density=420, keyboard=(0, 850, 1080, 2400))
        covered = {a["label"] for a in summary["actions"] if a.get("covered_by_keyboard")}

        self.assertIn("Wi-Fi", covered)
        self.assertNotIn("Search", covered)

    def test_without_a_keyboard_nothing_is_flagged(self) -> None:
        summary = summarize_ui_tree(SCREEN, density=420)

        self.assertEqual(summary["keyboard"], {"open": False, "top": None})
        self.assertFalse(any(a.get("covered_by_keyboard") for a in summary["actions"]))
