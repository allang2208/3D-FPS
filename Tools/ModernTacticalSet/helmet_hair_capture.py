"""Read current male/female helmet and scalp-hair sources; do not change assets or PIE."""
import json,hashlib
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/ModernTacticalSet20261113/HelmetHairFitR1'
R.mkdir(parents=True,exist_ok=True)
(R/'Inputs').mkdir(exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
KEY='ue_modern_tactical_helmet'
def value(v):
    if v is None or isinstance(v,(str,int,float,bool)):return v
    if hasattr(v,'get_path_name'):return v.get_path_name()
    if hasattr(v,'export_text'):return v.export_text()
    return [value(x) for x in v]
def prop(o,k):
    try:return value(o.get_editor_property(k))
    except Exception as e:return {'unavailable':str(e)}

G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List
xyz=lambda v:[v.x,v.y,v.z]
def geometry(mesh,file,skeletal=False,bones_only=False):
    fn=G.copy_mesh_from_skeletal_mesh if skeletal else G.copy_mesh_from_static_mesh
    dm,status=fn(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+mesh.get_path_name())
    d={'source':mesh.get_path_name()}
    if not bones_only:
        _,ps,_=Q.get_all_vertex_positions(dm,False);_,ts,_=Q.get_all_triangle_indices(dm,False)
        d.update(positions=[xyz(v) for v in L.convert_vector_list_to_array(ps)],triangles=[xyz(v) for v in L.convert_triangle_list_to_array(ts)])
    if skeletal:
        _,bs=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
        d['bones']={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in [u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1)]]) for b in bs}
    source=P/'Content'/(mesh.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
    d['sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    file.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
    return {'file':str(file),'source':d['source'],'sha256':d['sha256'],'vertices':len(d.get('positions',[]))}

report={'completed':False,'read_only':True,'profiles':{},'instances':[],'geometry_basis':'native groom card/mesh LOD sources, not live simulated strands'}
paths=set()
for rig,profile in [('Jason',cfg),('Kaitlin',cfg['body_variants']['kaitlin'])]:
    head=profile['heads'][profile['default_head']]
    row={'helmet':profile['head_equipment'][KEY],'head':head['mesh'],'hair_styles':{}}
    row['head_geometry']=geometry(u.load_asset(head['mesh']),R/'Inputs'/f'{rig}_Head.json',True)
    row['body_frame']=geometry(u.load_asset(profile['body_mesh']),R/'Inputs'/f'{rig}_Body.json',True,True)
    row['helmet_geometry']=geometry(u.load_asset(row['helmet']['static_mesh']),R/'Inputs'/f'{rig}_Helmet.json')
    for style,recipe in head['hair_styles'].items():
        hair=[]
        for entry in recipe.get('grooms',[]):
            asset=u.load_asset(entry['asset'])
            if not asset:raise RuntimeError('Missing groom '+entry['asset'])
            paths.add(entry['asset'])
            item={'recipe':entry,'settings':{k:prop(asset,k) for k in ('hair_groups_info','hair_groups_lod','hair_groups_cards','hair_groups_meshes','hair_groups_materials','hair_groups_physics')}}
            binding=u.load_asset(entry['binding']);item['binding']={k:prop(binding,k) for k in ('groom','source_skeletal_mesh','target_skeletal_mesh')};item['geometry']=[]
            for kind in ['cards','meshes']:
                for i,desc in enumerate(asset.get_editor_property('hair_groups_'+kind)):
                    mesh=desc.get_editor_property('imported_mesh')
                    if not mesh:continue
                    out=geometry(mesh,R/'Inputs'/f'{rig}_{style}_{kind}_{i}.json')
                    out.update(kind=kind,group=desc.get_editor_property('group_index'),groom_lod=desc.get_editor_property('lod_index'))
                    item['geometry'].append(out)
            hair.append(item)
        row['hair_styles'][style]=hair
    report['profiles'][rig]=row
for obj in u.ObjectIterator(u.GroomComponent):
    asset=obj.get_editor_property('groom_asset')
    if not asset or asset.get_path_name() not in paths or not obj.get_world():continue
    owner=obj.get_owner()
    report['instances'].append({'component':obj.get_path_name(),'owner':owner.get_path_name() if owner else None,
        'asset':asset.get_path_name(),'visible':obj.is_visible(),
        'properties':{k:prop(obj,k) for k in ('component_tags','binding_asset','simulation_settings','lod_bias','forced_lod','use_cards','hidden_in_game')},
        'materials':[value(obj.get_material(i)) for i in range(obj.get_num_materials())]})
report['completed']=True
(R/'capture.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('HELMET_HAIR_CAPTURED',list(report['profiles']),len(report['instances']),flush=True)
