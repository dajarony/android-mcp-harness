"""
SUME DOCBLOCK

Nombre: resumen
Tipo: Lógica

Entradas:
- XML del volcado de accesibilidad de Android.

Acciones:
- Reduce la pantalla a lo accionable y a lo legible, con el selector que este
  mismo servidor aceptaría para cada objetivo.

Salidas:
- Estructura acotada y serializable, sin coordenadas ni XPath.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as element_tree
from collections import Counter
from typing import Any

from contratos.mcp import HarnessError, McpErrorCode


MAX_ACTIONS = 120
MAX_TEXTS = 200

# Android's own minimum touch target. Anything smaller is a defect, not a taste.
MIN_TOUCH_TARGET_DP = 48

_EMPTY_BOUNDS = "[0,0][0,0]"
_BOUNDS = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


def _rectangle(node: element_tree.Element) -> tuple[int, int, int, int] | None:
    """Read a node's rectangle as left, top, right, bottom."""

    match = _BOUNDS.fullmatch(node.attrib.get("bounds", ""))
    if match is None:
        return None
    left, top, right, bottom = (int(value) for value in match.groups())
    return left, top, right, bottom


def _is_true(node: element_tree.Element, attribute: str) -> bool:
    return node.attrib.get(attribute) == "true"


def _visible(node: element_tree.Element) -> bool:
    """Skip nodes Android draws nowhere: they cannot be read nor pressed."""

    return node.attrib.get("bounds", _EMPTY_BOUNDS) != _EMPTY_BOUNDS


def _class_name(node: element_tree.Element) -> str:
    """Read a widget's class from either dump format.

    `uiautomator dump` emits `<node class="android.widget.EditText">`, while
    Appium's page source names the element after the class itself. The two
    sources describe the same screen and this module has to read both.
    """

    return node.attrib.get("class") or node.tag


def _elements(root: element_tree.Element) -> list[element_tree.Element]:
    """Walk every widget, whichever of the two dump shapes this is."""

    nodes = [node for node in root.iter("node") if _visible(node)]
    if nodes:
        return nodes
    return [node for node in root.iter() if node is not root and _visible(node)]


def _role(node: element_tree.Element) -> str | None:
    """Name what a target is for, using Android's own flags rather than pixels."""

    class_name = _class_name(node)
    if class_name.endswith("EditText"):
        return "input"
    if _is_true(node, "checkable"):
        return "toggle"
    if _is_true(node, "clickable"):
        return "button"
    if _is_true(node, "long-clickable"):
        return "long-press"
    # Scrollables are deliberately absent: ui.scroll acts on the screen and takes
    # no selector, so listing a container here would offer a target that cannot
    # be aimed at, borrowing its first child's label and lying about what it is.
    return None


def _own_label(node: element_tree.Element) -> str:
    return (node.attrib.get("text") or node.attrib.get("content-desc") or "").strip()


def _descendant_label(node: element_tree.Element) -> str:
    """Android often puts the words in a child of the element that is pressable."""

    for child in node.iter():
        if child is node or not _visible(child):
            continue
        label = _own_label(child)
        if label:
            return label
    return ""


def _candidate_selector(
    node: element_tree.Element, label: str
) -> tuple[dict[str, str], str] | None:
    """Offer only selectors this server accepts, best identifier first."""

    resource_id = (node.attrib.get("resource-id") or "").strip()
    if resource_id:
        return {"resource_id": resource_id}, resource_id
    content_desc = (node.attrib.get("content-desc") or "").strip()
    if content_desc:
        return {"content_desc": content_desc}, content_desc
    text = (node.attrib.get("text") or "").strip() or label
    if text:
        return {"text": text}, text
    return None


def _selector_attribute(selector: dict[str, str]) -> str:
    """Map public selector vocabulary back to the one XML attribute it reads."""

    return {
        "resource_id": "resource-id",
        "content_desc": "content-desc",
    }.get(next(iter(selector)), "text")


def _parents(root: element_tree.Element) -> dict[element_tree.Element, element_tree.Element]:
    """ElementTree has no parent axis; retain it for semantic context discovery."""

    return {child: parent for parent in root.iter() for child in parent}


def _matches_selector(node: element_tree.Element, selector: dict[str, str]) -> bool:
    """Match the exact XML field that the locator's basic selector will read."""

    attribute = _selector_attribute(selector)
    return (node.attrib.get(attribute) or "").strip() == next(iter(selector.values()))


def _semantic_context(
    node: element_tree.Element,
    selector: dict[str, str],
    nodes: list[element_tree.Element],
    parents: dict[element_tree.Element, element_tree.Element],
) -> dict[str, str] | None:
    """Find an ancestor label that makes one repeated target uniquely reachable.

    The selector points at the actual text/resource node, which may be a child
    of the clickable row.  Context is therefore sought from every matching
    target's ancestry, and emitted only when it leaves exactly one match.
    """

    targets = [candidate for candidate in nodes if _matches_selector(candidate, selector)]
    represented = [
        candidate
        for candidate in targets
        if candidate is node or node in parents and _is_ancestor(node, candidate, parents)
    ]
    for target in represented:
        ancestor = parents.get(target)
        while ancestor is not None:
            for kind, attribute in (
                ("resource_id", "resource-id"),
                ("content_desc", "content-desc"),
                ("text", "text"),
            ):
                value = (ancestor.attrib.get(attribute) or "").strip()
                if not value:
                    continue
                context = {kind: value}
                matches = [
                    candidate
                    for candidate in targets
                    if _has_ancestor(candidate, context, parents)
                ]
                if matches == [target]:
                    return context
            ancestor = parents.get(ancestor)
    return None


def _is_ancestor(
    ancestor: element_tree.Element,
    node: element_tree.Element,
    parents: dict[element_tree.Element, element_tree.Element],
) -> bool:
    """Say whether a visible action contains the actual target node."""

    current = parents.get(node)
    while current is not None:
        if current is ancestor:
            return True
        current = parents.get(current)
    return False


def _has_ancestor(
    node: element_tree.Element,
    context: dict[str, str],
    parents: dict[element_tree.Element, element_tree.Element],
) -> bool:
    """Mirror the locator's ancestor axis using parsed Android XML."""

    current = parents.get(node)
    while current is not None:
        if _matches_selector(current, context):
            return True
        current = parents.get(current)
    return False


def _layout_findings(
    entries: list[tuple[dict[str, Any], tuple[int, int, int, int]]],
    screen: tuple[int, int, int, int],
    density: int | None,
) -> list[dict[str, Any]]:
    """Report layout defects a machine can prove, and only those.

    Whether a screen is beautiful is not checkable and is left alone. Whether a
    button sits outside the display, has no area, or is too small for a finger
    is arithmetic, and it is exactly what a screenshot review keeps missing.
    """

    minimum = round(MIN_TOUCH_TARGET_DP * density / 160) if density else None
    findings: list[dict[str, Any]] = []
    for entry, (left, top, right, bottom) in entries:
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            findings.append({"issue": "no_area", "selector": entry["selector"]})
            continue
        if left < screen[0] or top < screen[1] or right > screen[2] or bottom > screen[3]:
            findings.append({"issue": "off_screen", "selector": entry["selector"]})
        # Both axes, deliberately. A wide row only 84 px tall is not a tiny
        # button, it is a row the scroll container cut off, and reporting that
        # would be the false positive the objective forbids. A control smaller
        # than a fingertip in *both* directions is never anything but a defect.
        if minimum and width < minimum and height < minimum:
            findings.append(
                {
                    "issue": "touch_target_too_small",
                    "selector": entry["selector"],
                    "size_px": [width, height],
                    "minimum_px": minimum,
                }
            )
    return findings


def _overlaps(rectangle: tuple[int, int, int, int], region: tuple[int, int, int, int]) -> bool:
    """Whether two rectangles share any area at all."""

    left, top, right, bottom = rectangle
    return not (
        right <= region[0] or left >= region[2] or bottom <= region[1] or top >= region[3]
    )


def summarize_ui_tree(
    ui_xml: str,
    density: int | None = None,
    keyboard: tuple[int, int, int, int] | None = None,
) -> dict[str, Any]:
    """Turn a raw accessibility dump into what a model can actually act on.

    The dump is the truth, but handing it over whole makes the caller pay for
    thousands of tokens of layout to find one label.  This keeps two questions
    answerable — what does the screen say, and what can I press — and answers the
    second in the exact selector vocabulary `ui.tap` and `ui.type_text` accept.
    """

    try:
        root = element_tree.fromstring(ui_xml)
    except element_tree.ParseError as exc:
        raise HarnessError(
            McpErrorCode.UI_TREE_UNAVAILABLE,
            "Android returned a UI hierarchy that could not be parsed.",
        ) from exc

    nodes = _elements(root)
    parents = _parents(root)
    foreground = next(
        (node.attrib["package"] for node in nodes if node.attrib.get("package")), ""
    )

    # A selector that matches two things is a coin toss, so count first and say so.
    seen: Counter[str] = Counter()
    for node in nodes:
        for attribute in ("resource-id", "content-desc", "text"):
            value = (node.attrib.get(attribute) or "").strip()
            if value:
                seen[f"{attribute}={value}"] += 1

    actions: list[dict[str, Any]] = []
    placed: list[tuple[dict[str, Any], tuple[int, int, int, int]]] = []
    texts: list[str] = []
    for node in nodes:
        label = _own_label(node)
        if label and label not in texts:
            texts.append(label)

        role = _role(node)
        if role is None:
            continue
        resolved = _candidate_selector(node, label or _descendant_label(node))
        if resolved is None:
            continue
        selector, value = resolved
        attribute = _selector_attribute(selector)
        entry: dict[str, Any] = {
            "selector": selector,
            "label": label or _descendant_label(node) or value,
            "role": role,
            "enabled": node.attrib.get("enabled", "true") == "true",
        }
        if seen[f"{attribute}={value}"] > 1:
            context = _semantic_context(node, selector, nodes, parents)
            if context is None:
                # Better to admit the ambiguity than to let the caller tap blind.
                entry["ambiguous"] = True
            else:
                entry["selector"] = {**selector, "within": context}
                entry["disambiguated"] = True
        rectangle = _rectangle(node)
        if rectangle is not None:
            # Position is reported so layout can be audited. It is never accepted
            # back as input: reading where something is and aiming at a pixel are
            # different powers, and only the first one is safe to hand over.
            entry["bounds"] = {
                "left": rectangle[0],
                "top": rectangle[1],
                "width": rectangle[2] - rectangle[0],
                "height": rectangle[3] - rectangle[1],
            }
        if keyboard is not None and rectangle is not None and _overlaps(rectangle, keyboard):
            # The dump describes the app window as if the keyboard were not over
            # it, so these read as available and cannot be touched. Dropping them
            # would be a lie of omission; saying nothing was the bug.
            entry["covered_by_keyboard"] = True
        if entry not in actions:
            actions.append(entry)
            if rectangle is not None:
                placed.append((entry, rectangle))

    screen = next(
        (rect for rect in (_rectangle(node) for node in nodes) if rect is not None),
        (0, 0, 0, 0),
    )
    findings = _layout_findings(placed, screen, density)
    truncated = len(actions) > MAX_ACTIONS or len(texts) > MAX_TEXTS
    return {
        "foreground_package": foreground,
        "actions": actions[:MAX_ACTIONS],
        "texts": texts[:MAX_TEXTS],
        # ui.scroll works on the screen, so this is a screen-level fact.
        "can_scroll": any(_is_true(node, "scrollable") for node in nodes),
        # device.back closes the keyboard, so a caller can act on this.
        "keyboard": {
            "open": keyboard is not None,
            "top": keyboard[1] if keyboard is not None else None,
        },
        "screen": {"width": screen[2] - screen[0], "height": screen[3] - screen[1]},
        "layout_findings": findings,
        "counts": {
            "actions": len(actions),
            "texts": len(texts),
            "layout_findings": len(findings),
        },
        "truncated": truncated,
    }
