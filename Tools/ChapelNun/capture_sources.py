import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/ProductionR1'
(R/'Inputs').mkdir(parents=True,exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))['body_variants']['kaitlin']
outfit=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))['body_variants']['kaitlin']['items']['ue_blue_mage_robe']
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights;L=u.GeometryScript_List
xyz=lambda v:[v.x,v.y,v.z]
def capture(name,path):
 asset=u.load_asset(path)
 dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
 _,points,_=Q.get_all_vertex_positions(dm,False);_,faces,_=Q.get_all_triangle_indices(dm,False);_,bones=B.get_all_bones_info(dm)
 points=L.convert_vector_list_to_array(points);faces=L.convert_triangle_list_to_array(faces)
 d=dict(source=path,skeleton=asset.skeleton.get_path_name(),positions=[xyz(v) for v in points],triangles=[xyz(t) for t in faces],uv=[],normals=[],triangle_materials=[],weights=[],bones=[dict(name=str(b.name),index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in [u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1)]]) for b in bones],materials=[dict(slot=str(m.material_slot_name),asset=m.material_interface.get_path_name() if m.material_interface else '') for m in asset.materials])
 for i in range(len(points)):
  _,weights,valid=B.get_vertex_bone_weights(dm,i)
  d['weights'].append([[w.bone_index,w.weight] for w in weights])
 for i in range(len(faces)):
  a,b,c,_=Q.get_triangle_u_vs(dm,0,i);_,na,nb,nc,_=Q.get_triangle_normals(dm,i)
  d['uv'].append([[v.x,v.y] for v in (a,b,c)]);d['normals'].append([xyz(v) for v in (na,nb,nc)]);d['triangle_materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
 (R/'Inputs'/(name+'.json')).write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
 print('NUN_SOURCE_CAPTURED',name,len(points),len(faces),flush=True)
 return asset
head=capture('native_head',cfg['heads'][cfg['default_head']]['mesh'])
robe=capture('native_robe',outfit['rig_meshes']['Kaitlin'])
body_path=outfit['underlayer_meshes'][cfg['body_mesh']]
capture('native_body',body_path)
meta=dict(body=body_path,base_body=cfg['body_mesh'],head=head.get_path_name(),robe=robe.get_path_name(),idle=cfg['clips']['Unarmed.Idle'],covers=outfit['rig_world_covers']['Kaitlin'],underlayers=outfit['underlayer_meshes'],cloth_assets=len(robe.mesh_clothing_assets),robe_physics=robe.physics_asset.get_path_name() if robe.physics_asset else None)
groom=u.load_asset(cfg['heads'][cfg['default_head']]['hair_styles']['long_straight']['grooms'][0]['asset'])
meta['hair_reference']=groom.get_path_name()
meta['groom_settings']={k:[x.export_text() for x in groom.get_editor_property(k)] for k in ['hair_groups_physics','hair_groups_rendering','hair_groups_interpolation','hair_groups_lod']}
(R/'Inputs/native_recipe.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print('NUN_SOURCES_READY',flush=True)
