"""Capture current saved native body/garments for the sling gravity fit."""
import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SimpleSlingBag20261022/GravityFitR3/BodyInputs';R.mkdir(parents=True,exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
items=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))['items']
sources={'body':cfg['body_mesh']}
for key in ['ue_field_sweater_charcoal','ue_field_sweater','ue_chainmail_shirt','ue_blue_mage_robe','ue_st6_sleeves']:
    sources[key]=items[key]['rig_meshes']['Jason']
G,Q,L,B=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List,u.GeometryScript_BoneWeights
vec=lambda v:[v.x,v.y,v.z]
for key,path in sources.items():
    mesh=u.load_asset(path)
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native fit input '+path)
    _,v,_=Q.get_all_vertex_positions(dm,False);_,t,_=Q.get_all_triangle_indices(dm,False);_,bones=B.get_all_bones_info(dm)
    v=L.convert_vector_list_to_array(v);t=L.convert_triangle_list_to_array(t)
    data=dict(source=path,positions=[vec(p) for p in v],triangles=[vec(p) for p in t],
        materials=[dict(slot=str(m.material_slot_name),asset=m.material_interface.get_path_name()) for m in mesh.materials],
        triangle_materials=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(t))],
        bones=[dict(index=b.index,name=str(b.name),parent=b.parent_index) for b in bones],
        reference={str(b.name):vec(b.world_transform.translation)+[getattr(b.world_transform.rotation,c) for c in 'xyzw']+vec(b.world_transform.scale3d) for b in bones},weights=[])
    for i in range(len(v)):
        _,pairs,valid=B.get_vertex_bone_weights(dm,i)
        if not valid:raise RuntimeError('Missing source skin weights')
        data['weights'].append([[p.bone_index,p.weight] for p in pairs if p.weight>0])
    (R/(key+'.json')).write_text(json.dumps(data,separators=(',',':')))
    print('SLING_GRAVITY_BODY_INPUT',key,len(v),flush=True)
    del data,dm;u.SystemLibrary.collect_garbage()
