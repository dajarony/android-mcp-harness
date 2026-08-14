"""
SUME DOCBLOCK

Nombre: resumen
Tipo: Lógica

Entradas:
- XML Android, densidad y marco opcional del teclado.

Acciones:
- Orquesta árbol, objetivos y maqueta en una vista semántica acotada.

Salidas:
- Resumen serializable compatible con las herramientas MCP públicas.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from logica.navegacion.arbol import (
    Rectangle,
    descendant_label,
    is_true,
    own_label,
    parent_map,
    parse_ui_tree,
    rectangle,
    visible_elements,
)
from logica.navegacion.maqueta import layout_findings, overlaps
from logica.navegacion.objetivos import (
    candidate_selector,
    role,
    selector_attribute,
    semantic_context,
)


MAX_ACTIONS = 120
MAX_TEXTS = 200


def summarize_ui_tree(
    ui_xml: str,
    density: int | None = None,
    keyboard: Rectangle | None = None,
) -> dict[str, Any]:
    """Turn raw Android XML into what a model can actually act on."""

    root = parse_ui_tree(ui_xml)
    nodes = visible_elements(root)
    parents = parent_map(root)
    foreground = next(
        (node.attrib["package"] for node in nodes if node.attrib.get("package")), ""
    )

    seen: Counter[str] = Counter()
    for node in nodes:
        for attribute in ("resource-id", "content-desc", "text", "hint"):
            value = (node.attrib.get(attribute) or "").strip()
            if value:
                seen[f"{attribute}={value}"] += 1

    actions: list[dict[str, Any]] = []
    placed: list[tuple[dict[str, Any], Rectangle]] = []
    texts: list[str] = []
    for node in nodes:
        label = own_label(node)
        if label and label not in texts:
            texts.append(label)

        target_role = role(node)
        if target_role is None:
            continue
        resolved = candidate_selector(node, label or descendant_label(node))
        if resolved is None:
            continue
        selector, value = resolved
        attribute = selector_attribute(selector)
        entry: dict[str, Any] = {
            "selector": selector,
            "label": label or descendant_label(node) or value,
            "role": target_role,
            "enabled": node.attrib.get("enabled", "true") == "true",
        }
        if seen[f"{attribute}={value}"] > 1:
            context = semantic_context(node, selector, nodes, parents)
            if context is None:
                entry["ambiguous"] = True
            else:
                entry["selector"] = {**selector, "within": context}
                entry["disambiguated"] = True
        bounds = rectangle(node)
        if bounds is not None:
            entry["bounds"] = {
                "left": bounds[0],
                "top": bounds[1],
                "width": bounds[2] - bounds[0],
                "height": bounds[3] - bounds[1],
            }
        if keyboard is not None and bounds is not None and overlaps(bounds, keyboard):
            entry["covered_by_keyboard"] = True
        if entry not in actions:
            actions.append(entry)
            if bounds is not None:
                placed.append((entry, bounds))

    screen = next(
        (bounds for bounds in (rectangle(node) for node in nodes) if bounds is not None),
        (0, 0, 0, 0),
    )
    findings = layout_findings(placed, screen, density)
    truncated = len(actions) > MAX_ACTIONS or len(texts) > MAX_TEXTS
    return {
        "foreground_package": foreground,
        "actions": actions[:MAX_ACTIONS],
        "texts": texts[:MAX_TEXTS],
        "can_scroll": any(is_true(node, "scrollable") for node in nodes),
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
