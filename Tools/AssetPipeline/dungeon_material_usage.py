"""Persist render usages required by authored dungeon instances at asset production time."""
import unreal as u

_changed_bases=set()
_updated_instances=set()

def ensure_material_usage(material, before_change=None):
    if not material:return None
    base=material.get_base_material()
    desired={'used_with_instanced_static_meshes':True}
    if base.get_editor_property('blend_mode') in (u.BlendMode.BLEND_OPAQUE,u.BlendMode.BLEND_MASKED):
        desired['used_with_nanite']=True
    previous={key:bool(base.get_editor_property(key)) for key in desired}
    changed=any(previous[key]!=value for key,value in desired.items())
    key=base.get_path_name()
    if changed:
        if before_change:before_change(base)
        base.modify()
        for name,value in desired.items():base.set_editor_property(name,value)
        if u.MaterialEditingLibrary.recompile_material(base):raise RuntimeError('Material compile failed '+key)
        if not u.EditorAssetLibrary.save_loaded_asset(base,False):raise RuntimeError('Material save failed '+key)
        _changed_bases.add(key)
    if isinstance(material,u.MaterialInstanceConstant) and key in _changed_bases and material.get_path_name() not in _updated_instances:
        if before_change:before_change(material)
        u.MaterialEditingLibrary.update_material_instance(material)
        if not u.EditorAssetLibrary.save_loaded_asset(material,False):raise RuntimeError('Material instance save failed '+material.get_path_name())
        _updated_instances.add(material.get_path_name())
    return dict(base=key,previous=previous,changed=changed)

def ensure_mesh_material_usage(mesh):
    for slot in mesh.get_editor_property('static_materials'):
        ensure_material_usage(slot.material_interface)
