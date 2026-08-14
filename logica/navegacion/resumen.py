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

import xml.etree.ElementTree as element_tree
from collections import Counter
from typing import Any

from contratos.mcp import HarnessError, McpErrorCode


MAX_ACTIONS = 120
MAX_TEXTS = 200

_EMPTY_BOUNDS = "[0,0][0,0]"


def _is_true(node: element_tree.Element, attribute: str) -> bool:
    return node.attrib.get(attribute) == "true"


def _visible(node: element_tree.Element) -> bool:
    """Skip nodes Android draws nowhere: they cannot be read nor pressed."""

    return node.attrib.get("bounds", _EMPTY_BOUNDS) != _EMPTY_BOUNDS


def _role(node: element_tree.Element) -> str | None:
    """Name what a target is for, using Android's own flags rather than pixels."""

    class_name = node.attrib.get("class", "")
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

    for child in node.iter("node"):
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


def summarize_ui_tree(ui_xml: str) -> dict[str, Any]:
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

    nodes = [node for node in root.iter("node") if _visible(node)]
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
        attribute = {"resource_id": "resource-id", "content_desc": "content-desc"}.get(
            next(iter(selector)), "text"
        )
        entry: dict[str, Any] = {
            "selector": selector,
            "label": label or _descendant_label(node) or value,
            "role": role,
            "enabled": node.attrib.get("enabled", "true") == "true",
        }
        if seen[f"{attribute}={value}"] > 1:
            # Better to admit the ambiguity than to let the caller tap blind.
            entry["ambiguous"] = True
        if entry not in actions:
            actions.append(entry)

    truncated = len(actions) > MAX_ACTIONS or len(texts) > MAX_TEXTS
    return {
        "foreground_package": foreground,
        "actions": actions[:MAX_ACTIONS],
        "texts": texts[:MAX_TEXTS],
        # ui.scroll works on the screen, so this is a screen-level fact.
        "can_scroll": any(_is_true(node, "scrollable") for node in nodes),
        "counts": {"actions": len(actions), "texts": len(texts)},
        "truncated": truncated,
    }
