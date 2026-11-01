"""Requested read-only saved asset audit. No gameplay, actor spawning, saves or settings changes."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[3]
config=json.loads((R/'Content/ColdSteelData/thunder-god-hammer-modules.json').read_text(encoding='utf-8-sig'))
saved=json.loads((P.parent/'import_receipt.json').read_text(encoding='utf-8'))
loaded_textures=[u.load_asset(path) for path in saved['textures']]
u.SystemLibrary.execute_console_command(None,'Editor.AsyncTextureCompilationFinishAll')
report=dict(complete=False,modified=False,gameplay_tested=False,meshes=[],textures=[],materials=[],console={})
def record(): (P/'saved_asset_readback.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def prop(obj,key):
    try:return str(obj.get_editor_property(key))
    except Exception as e:return 'unavailable: '+str(e)[:130]
for name,path in [('grip_v2',config['slots']['grip']['static_field_grip']['mesh']),('grip_v1','/Game/Weapons/ThunderGodHammer20261028/StaticFieldGripV1/Meshes/SM_ThunderGodHammer_grip_static_field.SM_ThunderGodHammer_grip_static_field'),('factory_grip',config['slots']['grip']['factory']['mesh'])]:
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing mesh: '+path)
    ns=mesh.get_editor_property('nanite_settings')
    row=dict(id=name,asset=path,lods=[dict(lod=i,triangles=mesh.get_num_triangles(i),vertices=mesh.get_num_vertices(i)) for i in range(mesh.get_num_lods())],materials=[str(s.material_slot_name) for s in mesh.get_editor_property('static_materials')],nanite={k:prop(ns,k) for k in ['enabled','explicit_tangents','position_precision','normal_precision','tangent_precision','keep_percent_triangles','trim_relative_error','fallback_target','fallback_percent_triangles','fallback_relative_error']})
    row['nanite_triangles']=mesh.get_num_nanite_triangles()
    row['nanite_vertices']=mesh.get_num_nanite_vertices()
    report['meshes'].append(row);record()
for path in saved['textures']:
    t=u.load_asset(path)
    row=dict(asset=path,size=[t.blueprint_get_size_x(),t.blueprint_get_size_y()],properties={k:prop(t,k) for k in ['compression_settings','srgb','flip_green_channel','never_stream','lod_group','lod_bias','max_texture_size','virtual_texture_streaming']})
    report['textures'].append(row);record()
for row in saved['materials']:
    m=u.load_asset(row['asset'])
    report['materials'].append(dict(asset=row['asset'],properties={k:prop(m,k) for k in ['blend_mode','two_sided','used_with_skeletal_mesh','used_with_nanite']}));record()
for c in ['r.Nanite','r.RayTracing','r.RayTracing.Nanite.Mode','r.Lumen.HardwareRayTracing','r.Streaming.PoolSize']:
    report['console'][c]=u.SystemLibrary.get_console_variable_int_value(c)
report['complete']=True;record()
# Resource-size console output is a cold commandlet inventory, not game GPU residency.
u.SystemLibrary.execute_console_command(None,'obj list class=StaticMesh name=SM_ThunderGodHammer_grip_static_field_V2 -alphasort')
u.SystemLibrary.execute_console_command(None,'listtextures name=T_StaticField')
print('STATIC_FIELD_READ_ONLY_AUDIT_COMPLETE')
