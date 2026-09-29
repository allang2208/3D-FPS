"""Reimport the three revised mesh assets at their existing map reference paths."""
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT / 'Scripts/import_assets.py'), run_name='__main__')
receipt = dict(
    stage='window_reveal_assets_v8_saved',
    revision='isolation_ward_window_reveals_v8_20260929',
    mesh_paths=['/Game/Dungeons/IsolationWard20260929/Meshes/SM_Ward_' + kind
                for kind in ('Walls', 'Frames', 'WindowGaskets')],
    window_count=5, window_edges_corrected=20,
    masonry_reveal_recess_mm=5, gasket_cap_embed_mm=3, mullion_cap_embed_mm=3,
    finished_window_size_m=[3.4, 1.33],
    map='/Game/GameMaps/Design/L_AbandonedIsolationWard_Subject',
    existing_map_references_preserved=True, map_rewritten=False,
    native_build_required=False, gameplay_tested=False, rendered=False,
)
(ROOT / 'Receipts/window-reveals-v8.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('WARD_WINDOW_REVEALS_V8_SAVED', json.dumps(receipt), flush=True)
