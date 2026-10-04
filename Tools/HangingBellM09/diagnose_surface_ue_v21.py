"""Inspect production references only; never edit, recompile or save UE assets."""
import unreal as u,json,traceback
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/SurfaceDiagnosisV21/Records')
BASE='/Game/Monsters/HangingBellM09/V04'
report={'asset_writes':False,'game_started':False,'errors':[]}
def path(x):return x.get_path_name() if x else None
def prop(x,key):
    try:return x.get_editor_property(key)
    except Exception:return None
def inspect():
    mesh=u.load_asset(BASE+'/SK_M09')
    report['mesh']=path(mesh)
    report['skin_revision']=u.EditorAssetLibrary.get_metadata_tag(mesh,'M09SkinRevision')
    report['mesh_slots']=[{'index':i,'slot':str(s.material_slot_name),'imported':str(prop(s,'imported_material_slot_name')),'material':path(s.material_interface)} for i,s in enumerate(mesh.materials)]
    textures=[]
    for name in ('Base','ORM','Normal'):
        tex=u.load_asset(BASE+'/Textures/T_M09_'+name)
        row={'path':path(tex),'srgb':prop(tex,'srgb'),'compression':str(prop(tex,'compression_settings')),'flip_green':prop(tex,'flip_green_channel')}
        if tex:
            try:row['size']=[tex.blueprint_get_size_x(),tex.blueprint_get_size_y()]
            except Exception as e:row['size_error']=str(e)
        textures.append(row)
    report['textures']=textures
    body=u.load_asset(BASE+'/Materials/M_M09_Body');ME=u.MaterialEditingLibrary
    report['body_material']={'path':path(body),'skeletal_usage':prop(body,'used_with_skeletal_mesh'),'two_sided':prop(body,'two_sided'),'used_textures':[path(t) for t in ME.get_used_textures(body)]}
    graph={};seen=set()
    def node(n):
        if not n:return None
        key=path(n)
        if key in seen:return key
        seen.add(key)
        graph[key]={'class':n.get_class().get_name(),'texture':path(prop(n,'texture'))}
        try:graph[key]['inputs']=[node(x) for x in ME.get_inputs_for_material_expression(body,n)]
        except Exception as e:graph[key]['error']=str(e)
        return key
    report['material_roots']={name:node(ME.get_material_property_input_node(body,getattr(u.MaterialProperty,name))) for name in ['MP_FRONT_MATERIAL','MP_BASE_COLOR','MP_NORMAL','MP_ROUGHNESS','MP_METALLIC']}
    report['material_graph']=graph
    cdo=u.get_default_object(u.HangingBellM09)
    components=cdo.get_components_by_class(u.SkeletalMeshComponent)
    report['native_components']=[{'name':c.get_name(),'mesh':path(c.skeletal_mesh_asset),'overrides':[path(m) for m in (prop(c,'override_materials') or [])]} for c in components]
    report['complete']=True
try:inspect()
except Exception:report['errors'].append(traceback.format_exc())
(OUT/'ue_surface.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M09_SURFACE_ASSET_DIAGNOSIS '+json.dumps(report))
