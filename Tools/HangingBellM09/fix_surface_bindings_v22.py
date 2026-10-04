"""Restore the two diagnosed M09 torso bindings; save only the production mesh."""
import unreal as u,json,shutil,traceback
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/SurfaceBindingV22')
BASE='/Game/Monsters/HangingBellM09/V04';PATH=BASE+'/SK_M09'
A=u.EditorAssetLibrary
report={'complete':False,'saved':[],'changed_slots':[],'game_tested':False,'rendered':False,'native_build_required':False}
def receipt():(ROOT/'Records/saved.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
try:
    if not globals().get('M09_COMMANDLET',False) and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Preserve running PIE before saving M09 mesh bindings')
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if PATH in dirty:raise RuntimeError('Preserve unsaved M09 mesh changes')
    mesh=u.load_asset(PATH);material=u.load_asset(BASE+'/Materials/M_M09_Body')
    if not mesh or not material:raise RuntimeError('Required production mesh/material is unavailable')
    backup=ROOT/'Before/SK_M09.uasset'
    if not backup.exists():shutil.copy2(Path('D:/FPS3D/FPSGAME/Content/Monsters/HangingBellM09/V04/SK_M09.uasset'),backup)
    slots=list(mesh.materials)
    targets={'M09_Body_SourcePBR_001','M09_Closure_SourcePBR_001'}
    report['before']=[{'index':i,'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for i,s in enumerate(slots)]
    for i,slot in enumerate(slots):
        if str(slot.material_slot_name) not in targets:continue
        if slot.material_interface not in (None,material):raise RuntimeError('Preserve changed material in '+str(slot.material_slot_name))
        slot.material_interface=material
        report['changed_slots'].append({'index':i,'name':str(slot.material_slot_name),'material':material.get_path_name()})
    if len(report['changed_slots'])!=2:raise RuntimeError('Diagnosed torso slot layout has changed')
    mesh.set_editor_property('materials',slots)
    A.set_metadata_tag(mesh,'M09MaterialRevision','V22 restored torso and closure duplicate-slot PBR bindings')
    if not A.save_loaded_asset(mesh,False):raise RuntimeError('Could not save the production mesh')
    report['saved'].append(mesh.get_path_name())
    report.update({'complete':True,'mesh_geometry_weights_uv_skeleton_physics_unchanged':True,'animations_AI_speed_unchanged':True})
    receipt();print('M09_SURFACE_BINDINGS_V22_SAVED '+json.dumps(report))
except Exception:
    report['error']=traceback.format_exc();receipt();raise
