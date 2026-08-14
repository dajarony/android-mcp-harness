"""
SUME DOCBLOCK

Nombre: objetivos
Tipo: Lógica

Entradas:
- Nodos visibles del árbol Android y sus ancestros.

Acciones:
- Clasifica objetivos y construye selectores semánticos inequívocos.

Salidas:
- Roles, selectores públicos y contexto `within` cuando es necesario.
"""

from __future__ import annotations

import xml.etree.ElementTree as element_tree

from logica.navegacion.arbol import (
    class_name,
    is_true,
    is_visible,
    own_label,
)


def role(node: element_tree.Element) -> str | None:
    """Name what a target is for, using Android flags rather than pixels."""

    if class_name(node).endswith("EditText"):
        return "input"
    if is_true(node, "checkable"):
        return "toggle"
    if is_true(node, "clickable"):
        return "button"
    if is_true(node, "long-clickable"):
        return "long-press"
    return None


def candidate_selector(
    node: element_tree.Element, label: str
) -> tuple[dict[str, str], str] | None:
    """Offer the strongest locator on an action or its visible child."""

    for candidate in node.iter():
        if candidate is not node and not is_visible(candidate):
            continue
        resource_id = (candidate.attrib.get("resource-id") or "").strip()
        if resource_id:
            return {"resource_id": resource_id}, resource_id
        content_desc = (candidate.attrib.get("content-desc") or "").strip()
        if content_desc:
            return {"content_desc": content_desc}, content_desc
        text = (candidate.attrib.get("text") or "").strip()
        if text:
            return {"text": text}, text
        hint = (candidate.attrib.get("hint") or "").strip()
        if hint:
            return {"input_hint": hint}, hint

    if label:
        return {"text": label}, label
    return None


def selector_attribute(selector: dict[str, str]) -> str:
    """Map public selector vocabulary back to its XML attribute."""

    return {
        "resource_id": "resource-id",
        "content_desc": "content-desc",
        "input_hint": "hint",
    }.get(next(iter(selector)), "text")


def matches_selector(node: element_tree.Element, selector: dict[str, str]) -> bool:
    """Match the exact XML field the basic selector will read."""

    attribute = selector_attribute(selector)
    return (node.attrib.get(attribute) or "").strip() == next(iter(selector.values()))


def semantic_context(
    node: element_tree.Element,
    selector: dict[str, str],
    nodes: list[element_tree.Element],
    parents: dict[element_tree.Element, element_tree.Element],
) -> dict[str, str] | None:
    """Find an ancestor label that makes one repeated target unique."""

    targets = [candidate for candidate in nodes if matches_selector(candidate, selector)]
    represented = [
        candidate
        for candidate in targets
        if candidate is node or (node in parents and _is_ancestor(node, candidate, parents))
    ]
    for target in represented:
        ancestor = parents.get(target)
        while ancestor is not None:
            for kind, attribute in (
                ("resource_id", "resource-id"),
                ("content_desc", "content-desc"),
                ("text", "text"),
                ("input_hint", "hint"),
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
    current = parents.get(node)
    while current is not None:
        if matches_selector(current, context):
            return True
        current = parents.get(current)
    return False
