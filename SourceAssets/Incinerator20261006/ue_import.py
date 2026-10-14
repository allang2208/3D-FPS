import unreal as u, json, re, hashlib, math
from pathlib import Path
W=Path('C:/Users/allan/Documents/Codex/2026-10-04/task-2/incinerator_20261006')
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/Incinerator20261006/CloudModel'
DEST='/Game/Building/Incinerator20261006';TARGET=DEST+'/SM_Incinerator'
assert '-IncineratorAssetImport' in u.SystemLibrary.get_command_line()
assert Path(u.Paths.project_dir()).resolve()==P.resolve()
before=json.loads((W/'asset_backup.json').read_text())
assert hashlib.sha256(Path(before['palette_path']).read_bytes()).hexdigest()==before['palette_sha256'],'Concurrent palette change'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
assert not E.does_asset_exist(TARGET),'Incinerator destination already exists'
man=json.loads((S/'material_and_geometry_manifest.json').read_text())
pal=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette');entries=list(pal.components)
def normalized(e):return re.sub(r'0x[0-9A-Fa-f]+','POINTER',str(e))
old=[normalized(e) for e in entries]
assert all(str(e.id)!='incinerator' for e in entries),'Incinerator palette entry already exists'
report={'palette_entries_before':old,'created_or_saved':[],'source_zip_sha256':'27b74670d2316aef31d06cb89e27b5a3e6028dde435add3179162453a42af521'}
def save(obj):
    assert E.save_loaded_asset(obj,False),obj.get_path_name()
    report['created_or_saved'].append(obj.get_path_name())
def canon(name):return re.sub('[^a-z0-9]','',str(name).lower())
lookup={canon(m['name']):m for m in man['materials']}
task=u.AssetImportTask();task.filename=str(S/'SM_Incinerator_LOD0.fbx');task.destination_path=DEST;task.destination_name='SM_Incinerator'
task.automated=True;task.replace_existing=False;task.save=False;task.factory=u.FbxFactory()
opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True
d.generate_lightmap_u_vs=False;d.auto_generate_collision=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task.options=opt;A.import_asset_tasks([task]);mesh=u.load_asset(TARGET);assert isinstance(mesh,u.StaticMesh),task.imported_object_paths
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for lod in [1,2]:assert sub.import_lod(mesh,lod,str(S/f'SM_Incinerator_LOD{lod}.fbx'))==lod,f'LOD{lod} import failed'
assert sub.get_lod_count(mesh)==3
assert sub.set_lod_screen_sizes(mesh,[1.0,.45,.18])
for lod in range(3):
    b=sub.get_lod_build_settings(mesh,lod)
    for k,v in {'remove_degenerates':False,'recompute_normals':False,'recompute_tangents':False,'use_full_precision_u_vs':True,'use_high_precision_tangent_basis':True,'generate_lightmap_u_vs':False}.items():b.set_editor_property(k,v)
    sub.set_lod_build_settings(mesh,lod,b)
nan=mesh.get_editor_property('nanite_settings');nan.enabled=False;sub.set_nanite_settings(mesh,nan,True)
def constant(mat,value,prop):
    if isinstance(value,list):
        node=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector);node.constant=u.LinearColor(*value[:3],1)
    else:node=L.create_material_expression(mat,u.MaterialExpressionConstant);node.r=value
    assert L.connect_material_property(node,'',prop),(mat.get_name(),prop)
slots=list(mesh.static_materials)
report['imported_slot_names']=[str(s.material_slot_name) for s in slots]
# The LOD importer may append differently formatted copies of the same FBX slots.
# Remap every section by its material name before compacting those duplicates.
unique=[];indices={};remap={}
for i,s in enumerate(slots):
    k=canon(s.material_slot_name)
    assert k in lookup,('Unknown imported material',str(s.material_slot_name),report['imported_slot_names'])
    if k not in indices:indices[k]=len(unique);unique.append(s)
    remap[i]=indices[k]
assert len(unique)==13,report['imported_slot_names']
for lod in range(3):
    for section in range(mesh.get_num_sections(lod)):
        old_slot=sub.get_lod_material_slot(mesh,lod,section)
        assert old_slot in remap,(lod,section,old_slot)
        sub.set_lod_material_slot(mesh,remap[old_slot],lod,section)
mesh.set_editor_property('static_materials',unique);slots=list(mesh.static_materials)
assert canon(slots[0].material_slot_name)=='rubberandbelts',str(slots[0].material_slot_name)
report['materials']=[]
for i,slot in enumerate(slots):
    key=canon(slot.material_slot_name);assert key in lookup,('Unmatched material slot',str(slot.material_slot_name))
    m=lookup[key];name='M_'+re.sub('[^A-Za-z0-9_]','_',m['name'])
    assert not E.does_asset_exist(DEST+'/Materials/'+name),name
    mat=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew());assert mat,name
    constant(mat,m['base_color'],u.MaterialProperty.MP_BASE_COLOR)
    constant(mat,m['metallic'],u.MaterialProperty.MP_METALLIC);constant(mat,m['roughness'],u.MaterialProperty.MP_ROUGHNESS)
    if m['emission_strength']>0:constant(mat,[c*m['emission_strength'] for c in m['emission_color'][:3]],u.MaterialProperty.MP_EMISSIVE_COLOR)
    errors=L.recompile_material(mat);assert not errors,(name,errors)
    save(mat);mesh.set_material(i,mat)
    report['materials'].append({'index':i,'slot':str(slot.material_slot_name),'path':mat.get_path_name(),'source':m})
sub.remove_collisions(mesh)
assert sub.add_simple_collisions(mesh,u.ScriptCollisionShapeType.NDOP26)>=0
assert sub.get_convex_collision_count(mesh)==1
body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
b=mesh.get_bounds();dimensions=[2*b.box_extent.x,2*b.box_extent.y,2*b.box_extent.z]
expected=[(hi-lo)*100 for hi,lo in zip(man['bounds']['max'],man['bounds']['min'])]
assert all(abs(a-e)<.5 for a,e in zip(dimensions,expected)),('Unexpected engine dimensions',dimensions,expected)
footprint=[math.ceil(v/20) for v in dimensions];assert footprint==[6,6,11],footprint
offset_z=b.box_extent.z-footprint[2]*10
E.set_metadata_tag(mesh,'IncineratorSourceSHA256',hashlib.sha256((S/'SM_Incinerator_LOD0.fbx').read_bytes()).hexdigest())
E.set_metadata_tag(mesh,'IncineratorSource','Cloud ColdSteelIncinerator 20261006; no output/recipe; static asset')
save(mesh)
entry=u.VoxelBuildPrefab();entry.set_editor_property('id','incinerator');entry.set_editor_property('display_name',u.Text('焚化炉'))
entry.set_editor_property('mesh',mesh);entry.set_editor_property('footprint',u.IntVector(*footprint))
entry.set_editor_property('pivot_offset_cm',u.Vector(0,0,offset_z))
# Surface stays null so slot 0 keeps the model's rubber feet. ActorClass stays null.
entries.append(entry);pal.set_editor_property('components',entries)
assert [normalized(e) for e in pal.components][:-1]==old,'Unrelated palette entries changed'
assert hashlib.sha256(Path(before['palette_path']).read_bytes()).hexdigest()==before['palette_sha256'],'Concurrent palette modification before save'
save(pal)
report.update(mesh=mesh.get_path_name(),bounds_origin_cm=[b.origin.x,b.origin.y,b.origin.z],dimensions_cm=dimensions,footprint=footprint,pivot_offset_cm=[0,0,offset_z],triangles=[mesh.get_num_triangles(n) for n in range(3)],lod_screen_sizes=list(sub.get_lod_screen_sizes(mesh)),collision=str(body.get_editor_property('collision_trace_flag')),collision_count=sub.get_simple_collision_count(mesh),nanite_enabled=False,palette_entries_after=[normalized(e) for e in pal.components],maps_saved=False,gameplay_tested=False)
report['simple_primitive_count']=sub.get_simple_collision_count(mesh)
report['convex_collision_count']=sub.get_convex_collision_count(mesh)
report['collision_count']=report['simple_primitive_count']+report['convex_collision_count']
(W/'ue_import_receipt.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
(P/'SourceAssets/Incinerator20261006/import_receipt.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print('INCINERATOR_IMPORTED '+json.dumps({k:report[k] for k in ['mesh','dimensions_cm','footprint','pivot_offset_cm','triangles','collision_count']}))
