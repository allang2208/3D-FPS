"""Persist the twelve material usage flags reported by the user's map warning.

Only the named material assets are modified/saved. Does not load/save a map,
change material graphs, start PIE, or run map checks.
"""
from pathlib import Path
import json,shutil,traceback
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
PATHS=[
 '/Game/Dungeons/StationWorkshop20261003/Materials/M_Workshop_OfficePlastic',
 '/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_KettleRubber_V6',
 '/Game/Dungeons/StationWorkshop20261003/Materials/M_Workshop_Screen',
 '/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_Stainless_V6',
 '/Game/Dungeons/StationWorkshop20261003/RefineV2/Materials/M_Office_Keycaps',
 '/Game/Dungeons/StationWorkshop20261003/RefineV2/Materials/M_Office_Legends',
 '/Game/Dungeons/StationWorkshop20261003/Materials/M_Workshop_Lamp',
 '/Game/Dungeons/StationWorkshop20261003/RefineV2/Materials/M_Office_Display',
 '/Game/Dungeons/StationWorkshop20261003/Materials/M_Workshop_Print',
 '/Game/Dungeons/WarehouseContainers20261002/Materials/M_Warehouse_ToolPaint',
 '/Game/Dungeons/IncineratorContainers20261003/Materials/M_Treatment_Gray',
 '/Game/Dungeons/IncineratorContainers20261003/Materials/M_Treatment_Charcoal',
]
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
receipt=ROOT/'Receipts/shared-material-usage.json'
report=dict(stage='preparing',requested_materials=PATHS,materials=[],map_saved=False,tests_run=False,rendered=False)
def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
try:
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Unexpected UE project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('PIE_ACTIVE: UE cannot save these materials while play mode is active')
    # Keep disk recovery copies; all edits run through the current editor batch.
    pending=[]
    for path in PATHS:
        mat=u.load_asset(path)
        if not isinstance(mat,u.Material):raise RuntimeError('Expected existing Material: '+path)
        rel=Path(path.removeprefix('/Game/')).with_suffix('.uasset')
        snapshot=ROOT/'Snapshots/shared-material-usage'/rel
        if not snapshot.exists():
            snapshot.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(PROJECT/'Content'/rel,snapshot)
        pending.append((path,mat))
    for path,mat in pending:
        before=bool(mat.get_editor_property('used_with_instanced_static_meshes'))
        mat.modify()
        if not before:mat.set_editor_property('used_with_instanced_static_meshes',True)
        # A map check may have enabled usage only in memory; save even when already true.
        errors=list(M.recompile_material(mat))
        if errors:raise RuntimeError('Material compilation failed '+path+': '+str(errors))
        if not E.save_loaded_asset(mat,False):raise RuntimeError('Material save failed '+path)
        report['materials'].append(dict(path=path,previous_loaded_flag=before,used_with_instanced_static_meshes=True,saved=True))
        record()
    report['stage']='materials_saved';record()
    print('RECEPTION_SHARED_MATERIAL_USAGE_SAVED',len(report['materials']),flush=True)
except Exception:
    report['error']=traceback.format_exc();record();raise
