"""Read the installed M249 surfaces and fitting sources for production."""
import unreal as u, json, hashlib
from pathlib import Path
r=Path(__file__).resolve().parent
E=u.EditorAssetLibrary; L=u.MaterialEditingLibrary
out={'meshes':{},'materials':{},'hashes':{}}
def path(a):return a.get_path_name() if a else None
def material(a):
    if not a or path(a) in out['materials']:return
    base=a.get_base_material();row={'base':path(base),'blend':str(base.blend_mode)}
    if isinstance(a,u.MaterialInstanceConstant):
        row['parent']=path(a.parent)
        row['scalars']={str(n):L.get_material_instance_scalar_parameter_value(a,n) for n in L.get_scalar_parameter_names(a)}
        row['vectors']={str(n):list(L.get_material_instance_vector_parameter_value(a,n).to_tuple()) for n in L.get_vector_parameter_names(a)}
        row['textures']={str(n):path(L.get_material_instance_texture_parameter_value(a,n)) for n in L.get_texture_parameter_names(a)}
    row['customs']=[dict(name=n.get_name(),description=str(n.get_editor_property('description')),code=n.get_editor_property('code'),inputs=[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]) for n in L.get_material_expressions(base) if isinstance(n,u.MaterialExpressionCustom)]
    row['outputs']={}
    for prop in ('BASE_COLOR','ROUGHNESS','METALLIC','NORMAL','AMBIENT_OCCLUSION'):
        n=L.get_material_property_input_node(base,getattr(u.MaterialProperty,'MP_'+prop))
        row['outputs'][prop]=dict(name=n.get_name(),type=n.get_class().get_name(),description=str(n.get_editor_property('desc')),inputs=[dict(name=x.get_name(),type=x.get_class().get_name()) if x else None for x in L.get_inputs_for_material_expression(base,n)]) if n else None
    out['materials'][path(a)]=row
for p in E.list_assets('/Game/Weapons/M249',True,False):
    p=p.split('.')[0]
    a=u.load_asset(p)
    if not isinstance(a,(u.StaticMesh,u.SkeletalMesh)):continue
    slots=a.static_materials if isinstance(a,u.StaticMesh) else a.materials
    out['meshes'][p]=[dict(slot=str(s.material_slot_name),material=path(s.material_interface)) for s in slots]
    for s in slots:material(s.material_interface)
    f=Path(u.Paths.project_content_dir())/(p.removeprefix('/Game/')+'.uasset')
    out['hashes'][p]=hashlib.sha256(f.read_bytes()).hexdigest()
material(u.load_asset('/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanSatinSteel'))
(r/'current_assets.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('M249_FINISH_INPUTS',len(out['meshes']),len(out['materials']),flush=True)
