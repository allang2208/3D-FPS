"""Save corrected wall/frame assets in place; no map load or gameplay execution."""
import json,runpy
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'Scripts/import_assets.py'),run_name='__main__')
receipt=dict(stage='rear_door_assets_v7_saved',revision='isolation_ward_rear_door_reveal_v7_20260929',
    mesh_paths=['/Game/Dungeons/IsolationWard20260929/Meshes/SM_Ward_Walls',
                '/Game/Dungeons/IsolationWard20260929/Meshes/SM_Ward_Frames'],
    masonry_reveal_recess_mm=5,continuous_fixed_door_frames=True,
    map='/Game/GameMaps/Design/L_AbandonedIsolationWard_Subject',existing_map_references_preserved=True,
    native_build_required=False,gameplay_tested=False,rendered=False)
(ROOT/'Receipts/rear-door-v7.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('WARD_REAR_DOOR_V7_SAVED',json.dumps(receipt),flush=True)
