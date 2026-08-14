"""Keep the living SUME map aligned with the tracked logic modules.

The map is documentation with operational value: agents and maintainers use it
to discover boundaries before editing. A module absent from it is invisible to
that review; a deleted module left in it sends readers to a false boundary.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "mapa-global" / "arquitectura.yaml"
MODULE_FILE = re.compile(r"^\s*file:\s*(logica/[^\s#]+\.py)\s*$", re.MULTILINE)


def tracked_logic_modules() -> set[str]:
    """Ask Git for the whole logic tree, then keep its tracked Python modules."""

    listed = subprocess.run(
        ["git", "ls-files", "logica/"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return python_logic_paths(listed.stdout)


def python_logic_paths(git_output: str) -> set[str]:
    """Keep Python files at every depth, including directly below ``logica/``."""

    return {
        path
        for path in git_output.splitlines()
        if path.startswith("logica/") and path.endswith(".py")
    }


def mapped_logic_modules() -> list[str]:
    """Read module-owned paths, not route references, from the SUME map."""

    return MODULE_FILE.findall(MAP.read_text(encoding="utf-8"))


def map_drift(
    tracked: set[str], declared: list[str]
) -> tuple[set[str], set[str], set[str]]:
    """Return missing, stale and duplicated module declarations."""

    mapped = set(declared)
    duplicates = {path for path in declared if declared.count(path) > 1}
    return tracked - mapped, mapped - tracked, duplicates


class ArchitectureMapTests(unittest.TestCase):
    """The architecture map must name every tracked logic boundary exactly once."""

    def test_it_reports_a_new_module_missing_from_the_map(self) -> None:
        missing, stale, duplicates = map_drift({"logica/new.py"}, [])
        self.assertEqual(missing, {"logica/new.py"})
        self.assertFalse(stale)
        self.assertFalse(duplicates)

    def test_it_keeps_a_module_directly_under_the_logic_root(self) -> None:
        paths = python_logic_paths(
            "logica/root_module.py\nlogica/nested/module.py\nlogica/readme.md\n"
        )
        self.assertEqual(
            paths, {"logica/root_module.py", "logica/nested/module.py"}
        )

    def test_it_reports_a_map_entry_for_a_deleted_module(self) -> None:
        missing, stale, duplicates = map_drift(set(), ["logica/removed.py"])
        self.assertFalse(missing)
        self.assertEqual(stale, {"logica/removed.py"})
        self.assertFalse(duplicates)

    def test_it_reports_a_duplicate_module_declaration(self) -> None:
        missing, stale, duplicates = map_drift(
            {"logica/shared.py"}, ["logica/shared.py", "logica/shared.py"]
        )
        self.assertFalse(missing)
        self.assertFalse(stale)
        self.assertEqual(duplicates, {"logica/shared.py"})

    def test_the_current_map_covers_each_tracked_logic_module_once(self) -> None:
        missing, stale, duplicates = map_drift(
            tracked_logic_modules(), mapped_logic_modules()
        )
        self.assertFalse(
            missing,
            "Tracked logic modules missing from mapa-global/arquitectura.yaml: "
            + ", ".join(sorted(missing)),
        )
        self.assertFalse(
            stale,
            "Map entries without a tracked logic module: " + ", ".join(sorted(stale)),
        )
        self.assertFalse(
            duplicates,
            "Logic modules declared more than once in the map: "
            + ", ".join(sorted(duplicates)),
        )
