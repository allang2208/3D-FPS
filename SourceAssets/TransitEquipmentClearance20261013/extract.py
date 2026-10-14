"""Read the saved transit layout and source geometry for the requested clearance review."""
from pathlib import Path
import json,gzip
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_Dungeon_Randomized')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Missing production generator')
catalog=json.loads(generators[0].get_editor_property('module_catalog_json'))
(ROOT/'Receipts/catalog-before.json').write_text(json.dumps(catalog,ensure_ascii=False),encoding='utf8')
module=next(m for m in catalog['modules'] if m['id']=='FacilityTransit')
rows=[]
for i,p in enumerate(module['parts']):rows.append(dict(key='part:'+str(i),**p))
for route,variants in catalog['facility_flow']['route_portal_variants'].items():
    for theme,parts in variants.items():
        for i,p in enumerate(parts):rows.append(dict(key=route+':'+theme+':'+str(i),**p))
for i,a in enumerate(module['runtime_actors']):
    for field in ('body','door','leaf'):
        if field not in a:continue
        p=dict(a);p['mesh']=a[field];p['key']='actor:'+str(i)+':'+field
        if field=='door':p['child_position']=a.get('hinge',[0,0,0])
        rows.append(p)
meshes={}
def vector(v):return list(v.to_tuple())
for row in rows:
    rotation=u.Rotator(pitch=row.get('pitch',0),yaw=row.get('yaw',0),roll=row.get('roll',0))
    tr=u.Transform(location=u.Vector(*row.get('position',[0,0,0])),rotation=rotation,scale=u.Vector(*row.get('scale',[1,1,1])))
    child=u.Vector(*row.get('child_position',[0,0,0]))
    origin=tr.transform_location(child)
    row['origin']=vector(origin)
    row['axes']=[vector(tr.transform_location(child+v)-origin) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]
    path=row['mesh']
    if path in meshes:continue
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing mesh '+path)
    bounds=mesh.get_bounding_box()
    data=dict(min=vector(bounds.min),max=vector(bounds.max));meshes[path]=data
    name=path.split('/')[-1]
    skip=any(s in name for s in ('tropicalPlant','SM_Tree','Paper','Signs','Diffuser','Fixture','Hanger','Roof','Crown','Soil','Fastener','Hardware','HighServices','ServiceBrackets','FootTrim','BaseTrim','GlazingShoe','PaneSeats','Irrigation','PipeClips','Drippers','LabelSupports','Light','DetailPlates','EquipmentLabels'))
    if skip:continue
    lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL;lod.lod_index=0
    dm,outcome=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh,u.new_object(u.DynamicMesh),u.GeometryScriptCopyMeshFromAssetOptions(),lod)
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read source LOD0 '+path)
    _,vs,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
    _,ts,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,True)
    data['vertices']=[vector(v) for v in u.GeometryScript_List.convert_vector_list_to_array(vs)]
    data['triangles']=[list(v.to_tuple()) for v in u.GeometryScript_List.convert_triangle_list_to_array(ts)]
with gzip.open(ROOT/'Receipts/geometry-before.json.gz','wt',encoding='utf8') as f:json.dump(dict(rows=rows,meshes=meshes),f)
print('TRANSIT_SOURCE_GEOMETRY_EXPORTED',len(rows),'placements',len(meshes),'unique meshes',sum('vertices' in m for m in meshes.values()),'source models')
