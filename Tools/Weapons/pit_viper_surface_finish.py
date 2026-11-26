"""Restore the saved VIPER-only surface revision after any older author import."""
import json,re
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parents[2]
O=P/'SourceAssets/PitViperSurfaceRepair20261030'

def apply_saved_finish(save=None,require_complete=True):
    contract=O/'production-contract.json';receipt=O/'import-receipt.json'
    if not contract.exists() or (require_complete and (not receipt.exists() or not json.loads(receipt.read_text(encoding='utf8')).get('complete'))):return
    data=json.loads(contract.read_text(encoding='utf8'));L=u.MaterialEditingLibrary
    # Engine DefaultNormal is a textured tile normal, NOT a neutral normal.
    # Keep the VIPER-specific replacement after any older authoring reimport.
    normal_contract=P/'SourceAssets/PitViperSurfaceFollowup20261030/normal-contract.json'
    texture_instances=json.loads(normal_contract.read_text(encoding='utf8'))['texture_instances'] if normal_contract.exists() else {}
    def load(path):
        obj=u.load_asset(path)
        if obj is None:raise RuntimeError('Missing saved VIPER finish '+path)
        return obj
    def persist(obj):
        if save:save(obj)
        elif not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('VIPER finish save failed '+obj.get_path_name())
    targets=set(data['instances'])|set(data['mesh_bindings'])|set(texture_instances)
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if not save and targets&dirty:raise RuntimeError('Unsaved VIPER target packages '+str(sorted(targets&dirty)))
    for path in sorted(set(data['instances'])|set(texture_instances)):
        material=load(path)
        for key,value in data['instances'].get(path,{}).items():L.set_material_instance_scalar_parameter_value(material,key,value)
        for key,value in texture_instances.get(path,{}).items():L.set_material_instance_texture_parameter_value(material,key,load(value))
        L.update_material_instance(material);persist(material)
    ed=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.get_default_object(u.StaticMeshEditorSubsystem)
    for path,bindings in data['mesh_bindings'].items():
        mesh=load(path);slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            key=re.sub(r'[._]\d{3}$','',str(slot.material_slot_name))
            if key in bindings:slot.material_interface=load(bindings[key]);slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        # Precision only. Preserve source split normals, tangent algorithm,
        # UV coordinates, geometry, slot order and all attachment sockets.
        settings=ed.get_lod_build_settings(mesh,0)
        settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
        ed.set_lod_build_settings(mesh,0,settings)
        persist(mesh)
    path=P/'Content/ColdSteelData/gunsmith.json';text=path.read_text(encoding='utf-8-sig')
    pos=text.index('"ue_pit_viper2011"',text.index('"weapons"'));start=text.rfind('{',0,pos)
    weapon,size=json.JSONDecoder().raw_decode(text[start:]);variants=weapon['pistol_grip_surface']['variants']
    for key,material in data['grip_variants'].items():variants[key]['material']=material
    updated=text[:start]+json.dumps(weapon,ensure_ascii=False,indent=2)+text[start+size:]
    if path.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Catalog changed during VIPER surface publication')
    if updated!=text:path.write_text(updated,encoding='utf8')
    return data

if __name__=='__main__':apply_saved_finish()
