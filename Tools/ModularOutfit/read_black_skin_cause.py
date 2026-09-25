"""Read the failing hand asset and current component data for the reported black surface."""
import json,math
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924')
inputs=json.loads((ROOT/'inputs.json').read_text())
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils
report={};sleeve_normals={};sleeve_compare=[]
for label,path in [('source',inputs['RuneSword']['mesh']),('bare','/Game/Characters/ModularOutfit20260924/NativeSkin/SK_RuneSword_NativeBareSkin')]:
    asset=u.load_asset(path)
    dm,outcome=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _,tri_list,_=Q.get_all_triangle_indices(dm,False)
    triangles=u.GeometryScript_List.convert_triangle_list_to_array(tri_list)
    stats=[]
    for i,t in enumerate(triangles):
        mid,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,i)
        if mid!=(1 if label=='source' else 0):continue
        if i%7:continue
        _,a,b,c,valid=Q.get_triangle_normals(dm,i)
        face,valid=Q.get_triangle_face_normal(dm,i)
        for vi,n in zip((t.x,t.y,t.z),(a,b,c)):
            p,valid=Q.get_vertex_position(dm,vi);identity=tuple(round(v,3) for v in (p.x,p.y,p.z))
            if label=='source':sleeve_normals[identity]=(n,face)
            elif identity in sleeve_normals:
                original,original_face=sleeve_normals[identity]
                sleeve_compare.append([n.dot(original),face.dot(original_face)])
    for i in range(0,len(triangles),max(1,len(triangles)//120)):
        face,valid=Q.get_triangle_face_normal(dm,i)
        _,a,b,c,valid=Q.get_triangle_normals(dm,i)
        stats.append({'face':[face.x,face.y,face.z],'normal':[a.x,a.y,a.z],
           'normal_length':a.length(),'dot':face.dot(a),'material':u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0]})
    report[label]={'materials':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else ''} for s in asset.materials],'normals':stats}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
    actor=u.GameplayStatics.get_player_character(world,0)
    report['components']=[]
    if actor:
        for c in actor.get_components_by_class(u.SkeletalMeshComponent):
            if not c.is_visible() or not c.skeletal_mesh_asset:continue
            if 'RuneSword' not in c.skeletal_mesh_asset.get_path_name():continue
            entry={'name':c.get_name(),'mesh':c.skeletal_mesh_asset.get_path_name(),'materials':[m.get_path_name() if m else '' for m in c.get_materials()]}
            for name in ('first_person_primitive_type','cast_shadow','cast_hidden_shadow','cast_dynamic_shadow','visible_in_ray_tracing','render_in_main_pass','lighting_channels','bounds_scale'):
                try:entry[name]=str(c.get_editor_property(name))
                except Exception:pass
            report['components'].append(entry)
(ROOT/'black-skin-cause.json').write_text(json.dumps(report,indent=2))
for key in ('source','bare'):
    s=report[key]['normals']
    print(key,'normal_length',sum(v['normal_length'] for v in s)/len(s),'normal_face_dot',sum(v['dot'] for v in s)/len(s),'materials',report[key]['materials'])
print('components',report.get('components',[]))
print('Native sleeve normal/face alignment',len(sleeve_compare),[sum(v[i] for v in sleeve_compare)/len(sleeve_compare) for i in (0,1)] if sleeve_compare else [])
