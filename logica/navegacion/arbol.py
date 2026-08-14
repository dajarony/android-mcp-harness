"""
SUME DOCBLOCK

Nombre: arbol
Tipo: Lógica

Entradas:
- XML de accesibilidad Android en formato UiAutomator o Appium.

Acciones:
- Parsea nodos visibles y conserva sus relaciones estructurales.

Salidas:
- Nodos, etiquetas, rectángulos y ancestros sin decidir acciones ni diseño.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as element_tree

from contratos.mcp import HarnessError, McpErrorCode


Rectangle = tuple[int, int, int, int]

_EMPTY_BOUNDS = "[0,0][0,0]"
_BOUNDS = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


def parse_ui_tree(ui_xml: str) -> element_tree.Element:
    """Parse Android XML and turn malformed hierarchies into a typed error."""

    try:
        return element_tree.fromstring(ui_xml)
    except element_tree.ParseError as exc:
        raise HarnessError(
            McpErrorCode.UI_TREE_UNAVAILABLE,
            "Android returned a UI hierarchy that could not be parsed.",
        ) from exc


def rectangle(node: element_tree.Element) -> Rectangle | None:
    """Read a node's rectangle as left, top, right, bottom."""

    match = _BOUNDS.fullmatch(node.attrib.get("bounds", ""))
    if match is None:
        return None
    left, top, right, bottom = (int(value) for value in match.groups())
    return left, top, right, bottom


def is_true(node: element_tree.Element, attribute: str) -> bool:
    """Read one Android boolean attribute."""

    return node.attrib.get(attribute) == "true"


def is_visible(node: element_tree.Element) -> bool:
    """Skip nodes Android draws nowhere: they cannot be read nor pressed."""

    return node.attrib.get("bounds", _EMPTY_BOUNDS) != _EMPTY_BOUNDS


def class_name(node: element_tree.Element) -> str:
    """Read a widget class from either UiAutomator or Appium dump shapes."""

    return node.attrib.get("class") or node.tag


def visible_elements(root: element_tree.Element) -> list[element_tree.Element]:
    """Walk every visible widget, whichever Android XML shape produced it."""

    nodes = [node for node in root.iter("node") if is_visible(node)]
    if nodes:
        return nodes
    return [node for node in root.iter() if node is not root and is_visible(node)]


def own_label(node: element_tree.Element) -> str:
    """Return the first visible semantic label native to one node."""

    return (
        node.attrib.get("text")
        or node.attrib.get("content-desc")
        or node.attrib.get("hint")
        or ""
    ).strip()


def descendant_label(node: element_tree.Element) -> str:
    """Find words nested beneath a pressable Android container."""

    for child in node.iter():
        if child is node or not is_visible(child):
            continue
        label = own_label(child)
        if label:
            return label
    return ""


def parent_map(
    root: element_tree.Element,
) -> dict[element_tree.Element, element_tree.Element]:
    """Build the parent axis ElementTree intentionally does not expose."""

    return {child: parent for parent in root.iter() for child in parent}
