"""Offline access to F6 reports, including the deduplicated schema 15 layout.

No engine access or capture side effects. Missing detail is unknown, not zero.
"""

import json
from pathlib import Path


def load_report(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def encounter_windows(report):
    return report.get("encounter_diagnostics", {}).get("windows", [])


def resource_samples(report, window=None):
    """Return ordered rolling-history samples, or a specified combat window.

    Old reports embed window samples. Schema 15 stores the union once and
    references it; archived samples must not be dropped or counted twice.
    """
    history = report.get("render_resource_history", {})
    table = history.get("samples", [])
    if window is None:
        indices = history.get("history_sample_indices")
        return table if indices is None else [table[index] for index in indices]
    indices = window.get("completed_resource_sample_indices")
    if indices is not None:
        return [table[index] for index in indices]
    return window.get("completed_resource_samples", [])


def skinned_components(sample):
    """Prefer the complete list; return None when no component list was observed.

    A legacy staff-only list has narrower coverage, not complete crowd coverage.
    Never concatenate the complete list and its old subset.
    """
    if "skinned_components" in sample:
        return sample["skinned_components"]
    return sample.get("staff")


def staff_components(sample):
    if "staff" in sample:
        return sample["staff"]
    components = skinned_components(sample)
    if components is None:
        return None
    return [row for row in components if row.get("legacy_staff_body", False)]
