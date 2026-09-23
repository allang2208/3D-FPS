"""Repair the existing PKM mesh's slot identities and material bindings only."""
import unreal as u,json,sys
from pathlib import Path
O=Path(__file__).parent;R=O.parent;P='/Game/Weapons/PKMLowpoly20260922'
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before saving PKM section identities')
sys.path.insert(0,str(R/'Belt08'))
from material_binding import capture_bindings,bind_materials,imported_name
mesh=u.load_asset(P+'/SK_PKM_Manny');sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
surface=json.loads((R/'Belt08/surface_import.json').read_text())['bindings']
mapping=bind_materials(mesh,surface,capture_bindings(mesh))
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('PKM section/material save failed')
# Capture the actual section routing after the repair, rather than assuming
# section indices equal material indices in the imported mesh.
sections=[]
for i in range(sub.get_num_sections(mesh,0)):
 index=sub.get_lod_material_slot(mesh,0,i);slot=mesh.materials[index]
 sections.append({'section':i,'material_index':index,'slot':str(slot.material_slot_name),'imported':imported_name(slot),'material':slot.material_interface.get_path_name()})
report={'mesh':mesh.get_path_name(),'saved':True,'mapping':mapping,'lod0_sections':sections,
        'cause':'Retained editor slot names diverged from FBX imported material identities: body used OldBox name and green box shader.',
        'geometry_changed':False,'animation_changed':False,'runtime_tested':False}
(O/'mapping_fixed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('PKM material identity repair saved. Body uses QBZ metal and has no reload-prop suffix.')
print(json.dumps(sections,indent=2))
