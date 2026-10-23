"""Read current native body/clothes for authoring this backpack's worn fit."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ExpeditionBackpack20261022';out=R/'BodyInputs';out.mkdir(exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
outfits=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))['items']
sources={'body':cfg['body_mesh']}
for key in ['ue_field_sweater_charcoal','ue_field_sweater','ue_chainmail_shirt','ue_blue_mage_robe','ue_st6_sleeves']:
    sources[key]=outfits[key]['rig_meshes']['Jason']
G,Q,L,B=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List,u.GeometryScript_BoneWeights
vec=lambda v:[v.x,v.y,v.z]
receipts=[]
for key,path in sources.items():
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing actual fit input '+path)
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
    _,vertices,_=Q.get_all_vertex_positions(dm,False);_,faces,_=Q.get_all_triangle_indices(dm,False)
    vertices=L.convert_vector_list_to_array(vertices);faces=L.convert_triangle_list_to_array(faces);_,bones=B.get_all_bones_info(dm)
    data={'source':path,'positions':[vec(v) for v in vertices],'triangles':[vec(t) for t in faces],
          'materials':[{'slot':str(m.material_slot_name),'asset':m.material_interface.get_path_name() if m.material_interface else None} for m in asset.materials],
          'triangle_materials':[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(faces))],
          'bones':[{'index':b.index,'name':str(b.name),'parent':b.parent_index} for b in bones],
          'reference':{str(b.name):vec(b.world_transform.translation)+[getattr(b.world_transform.rotation,c) for c in 'xyzw']+vec(b.world_transform.scale3d) for b in bones},
          'weights':[]}
    for vi in range(len(vertices)):
        _,pairs,valid=B.get_vertex_bone_weights(dm,vi)
        if not valid:raise RuntimeError('Missing native fit weights')
        data['weights'].append([[p.bone_index,p.weight] for p in pairs if p.weight>0])
    (out/(key+'.json')).write_text(json.dumps(data,separators=(',',':')))
    receipts.append({'key':key,'asset':path,'vertices':len(vertices),'triangles':len(faces)})
    print('EXPEDITION_FIT_INPUT',key,len(vertices),flush=True)
    del dm,data
    u.SystemLibrary.collect_garbage()
(out/'manifest.json').write_text(json.dumps(receipts,indent=2))
print('EXPEDITION_FIT_INPUTS_READY',flush=True)
