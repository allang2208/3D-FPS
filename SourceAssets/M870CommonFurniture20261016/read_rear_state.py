import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;R={}
for key in ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'):
    m=u.load_asset('/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_'+key)
    R[key]=[{'name':str(s.material_slot_name),'imported':str(s.get_editor_property('imported_material_slot_name')),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in m.static_materials]
ed=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
R['lods']={}
for key in ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'):
 m=u.load_asset('/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_'+key);n=ed.get_lod_count(m)
 R['lods'][key]={'count':n,'settings':[str(ed.get_lod_build_settings(m,i)) for i in range(n)]}
R['dirty']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
(O/'RearGripFinish/ue_material_slots.json').write_text(json.dumps(R,indent=2))
print(json.dumps(R),flush=True)
