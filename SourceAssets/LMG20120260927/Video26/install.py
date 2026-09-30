"""Replace only identified lid/rail/sight surfaces on the installed 201."""
import unreal as u,json,hashlib,shutil,math
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2]
P='/Game/Weapons/LMG201/Video26';PROD='/Game/Weapons/LMG201/Production20260927'
BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
WET='/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
M=u.GeometryScript_Materials;B=u.GeometryScript_BoneWeights;Ed=u.GeometryScript_MeshEdits
Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; no 201 package was changed')
targets=[BODY,PROD+'/SM_LMG201_FrontSight',PROD+'/SM_LMG201_RearSight',WET]
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in targets):raise RuntimeError('A target 201 package has unsaved edits; preserve it')
source=json.loads((O/'source_package.json').read_text())
package=Path(source['path'])
prior_receipt=json.loads((O/'delivery.json').read_text()) if (O/'delivery.json').exists() else {}
body_done=prior_receipt.get('meshes',{}).get(BODY,{})
expected_hash=body_done.get('sha256',source['sha256'])
if hashlib.sha256(package.read_bytes()).hexdigest()!=expected_hash:
    raise RuntimeError('Current 201 package changed since geometry authoring; preserve the new package')
materials=json.loads((O/'materials_receipt.json').read_text())
if materials.get('status')!='materials_compiled_and_saved':raise RuntimeError('PBR material authoring not complete')
receipt=prior_receipt or {'revision':'Video26','status':'installing','backup':{},'meshes':{},
         'materials':materials['materials'],'tests_run':False,'rendered':False,'game_started':False}
def record():(O/'delivery.json').write_text(json.dumps(receipt,indent=2))
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def backup(path):
    file=PROJECT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    dest=O/'Before'/file.relative_to(PROJECT/'Content')
    if file.exists() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,dest)
    receipt['backup'][path]=str(dest)
def dynamic(mesh):
    fn=G.copy_mesh_from_skeletal_mesh if isinstance(mesh,u.SkeletalMesh) else G.copy_mesh_from_static_mesh
    dm,result=fn(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read surface '+mesh.get_path_name())
    return dm
for p in targets:backup(p)
record();body_asset=u.load_asset(BODY);slots=[s.copy() for s in body_asset.materials]

def import_part(name,skeletal=False):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_animations=False
    opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
    opt.set_editor_property('reset_to_fbx_on_material_conflict',True)
    if skeletal:
        opt.skeleton=body_asset.skeleton;data=opt.skeletal_mesh_import_data
        data.set_editor_property('update_skeleton_reference_pose',False)
        data.set_editor_property('use_t0_as_ref_pose',False)
        data.set_editor_property('preserve_smoothing_groups',True)
    else:
        data=opt.static_mesh_import_data;data.combine_meshes=True
        data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
    task=u.AssetImportTask();task.filename=str(O/'Exports'/(name+'.fbx'))
    task.destination_path=P+'/Parts';task.destination_name=name;task.factory=u.FbxFactory();task.options=opt
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    A.import_asset_tasks([task]);asset=u.load_asset(task.destination_path+'/'+name)
    if not asset or not task.imported_object_paths:raise RuntimeError('Part import failed '+name)
    return asset

flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
bindings={body_asset.get_path_name():{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}}
try:
    if not body_done.get('saved'):
        new_asset=import_part('SK_LMG201_Video26_Parts',True)
        mat=u.load_asset(materials['materials']['Body'])
        source_slots=[s.copy() for s in new_asset.materials]
        for s in source_slots:s.material_interface=mat
        new_asset.materials=source_slots;save(new_asset)
        body=dynamic(body_asset);part=dynamic(new_asset)
        # Ownership comes from the named prior objects and their exact source
        # surface positions. Do not slice the receiver using a spatial box.
        regions=json.loads((O/'replace_regions.json').read_text())['vertices_by_slot']
        region_grids={}
        def cell(p):return tuple(math.floor(float(x)*100) for x in p)
        for name,positions in regions.items():
            grid={}
            for p in positions:grid.setdefault(cell(p),[]).append(p)
            region_grids[name]=grid
        _,vlist,_=Q.get_all_vertex_positions(body,False);positions=L.convert_vector_list_to_array(vlist)
        _,tlist,_=Q.get_all_triangle_indices(body,False);triangles=L.convert_triangle_list_to_array(tlist)
        inside_cache={};delete=[];counts={}
        def owned(mid,vi):
            key=(mid,vi)
            if key in inside_cache:return inside_cache[key]
            grid=region_grids.get(str(slots[mid].material_slot_name))
            if grid is None:inside_cache[key]=False;return False
            p=positions[vi];xyz=(p.x,p.y,p.z);base=cell(xyz)
            for x in [-1,0,1]:
                for y in [-1,0,1]:
                    for z in [-1,0,1]:
                        for q in grid.get((base[0]+x,base[1]+y,base[2]+z),[]):
                            if sum((xyz[k]-q[k])**2 for k in range(3))<.003**2:
                                inside_cache[key]=True;return True
            inside_cache[key]=False;return False
        for ti,t in enumerate(triangles):
            mid,valid=M.get_triangle_material_id(body,ti)
            if valid and all(owned(mid,vi) for vi in (t.x,t.y,t.z)):
                delete.append(ti);name=str(slots[mid].material_slot_name);counts[name]=counts.get(name,0)+1
        if not delete:raise RuntimeError('Prior named surfaces were not found; replacement was not applied')
        ids=L.convert_array_to_index_list(delete,u.GeometryScriptIndexType.TRIANGLE)
        _,num_deleted=Ed.delete_triangles_from_mesh(body,ids,True)
        # The current native bone hierarchy is authoritative. Reindex only new parts.
        B.copy_bones_from_mesh(part,body,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
        new_slot=source_slots[0].copy()
        new_slot.material_interface=mat
        new_slot.material_slot_name='M_LMG201_Video26_Body'
        new_mid=len(slots);slots.append(new_slot)
        for i in range(len(source_slots)):M.remap_material_i_ds(part,i,new_mid)
        Ed.append_mesh(body,part,u.Transform(),True)
        # BodyRollback27 restores the pre-Video26 factory barrel/body finish.
        # Historical Video26 receipts must not reapply those finish clones.
        finish={}
        for i,s in enumerate(slots):
            path=finish.get(str(s.material_slot_name))
            if path:s.material_interface=u.load_asset(path);slots[i]=s
        options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
            new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],
            enable_recompute_normals=False,enable_recompute_tangents=True,
            bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _,result=G.copy_mesh_to_skeletal_mesh(body,body_asset,options,u.GeometryScriptMeshWriteLOD())
        if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('201 assembly failed')
        body_asset.materials=slots
        E.set_metadata_tag(body_asset,'201CoverRevision','Video26: video-led closed formed lid and interior, high-poly bake')
        E.set_metadata_tag(body_asset,'201BodySurfaceRevision','Surface25 body retained; native arms and Magazine24 not reimported')
        save(body_asset)
        bindings[body_asset.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}
        receipt['meshes'][BODY]={'saved':True,'replaced_triangle_count':num_deleted,'source_regions':counts,
            'material_slots':len(slots),'new_parts_asset':new_asset.get_path_name(),
            'sha256':hashlib.sha256(package.read_bytes()).hexdigest()};record()
        print('VIDEO26_BODY_SAVED',num_deleted,flush=True)

    for group in ['FrontSight','RearSight']:
        name='SM_LMG201_'+group;candidate=import_part(name)
        material=u.load_asset(materials['materials'][group])
        new_slot=candidate.static_materials[0].copy()
        new_slot.material_interface=material
        new_slot.material_slot_name='M_LMG201_Video26_'+group
        new_slots=[new_slot]
        candidate.static_materials=new_slots;save(candidate)
        dest=u.load_asset(PROD+'/'+name);dm=dynamic(candidate)
        opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[material],
            new_material_slot_names=[u.Name('M_LMG201_Video26_'+group)],enable_recompute_normals=False,enable_recompute_tangents=True)
        _,result=G.copy_mesh_to_static_mesh(dm,dest,opts,u.GeometryScriptMeshWriteLOD())
        if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Sight copy failed '+name)
        dest.static_materials=new_slots
        dest.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports'/(name+'.fbx')),0,'Video26')
        E.set_metadata_tag(dest,'201SightRevision','Video26: original pivot and aim axis; high-poly PBR baked')
        save(dest);bindings[dest.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() for s in new_slots}
        receipt['meshes'][dest.get_path_name()]={'saved':True,'candidate':candidate.get_path_name(),'pivot':'existing hinge, unchanged'};record()
        print('VIDEO26_SIGHT_SAVED',group,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))

for path,info in materials['bindings'].items():
    if path==body_asset.get_path_name():continue
    mesh=u.load_asset(path);backup(path);slots=mesh.static_materials
    for i,s in enumerate(slots):
        dest=info.get(str(s.material_slot_name))
        if dest:s.material_interface=u.load_asset(dest);slots[i]=s
    mesh.static_materials=slots;save(mesh)
    bindings[path]={str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}
    receipt['meshes'][path]={'saved':True,'geometry_changed':False,'finish':'Video26 satin'};record()

# Extend the existing wetness catalog without replacing attachment mappings.
table=u.load_asset(WET);wet=dict(table.get_editor_property('wet_materials'))
for path in list(materials['materials'].values())+list(materials['finish_clones'].values()):wet[path]=u.load_asset(path)
table.set_editor_property('wet_materials',wet);save(table)
receipt['wet_mapping_additions']=len(materials['materials'])+len(materials['finish_clones'])

# Older import stages already use this binding manifest. Keep its existing
# entries, and teach that hook the final new UV/material identities.
manifest=O.parent/'Material21/bindings.json';backup_manifest=O/'Before/Material21_bindings.json'
if not backup_manifest.exists():shutil.copy2(manifest,backup_manifest)
data=json.loads(manifest.read_text())
for path,info in bindings.items():data['meshes'][path]=info
manifest.write_text(json.dumps(data,indent=2),encoding='utf8')
(O/'bindings.json').write_text(json.dumps({'meshes':bindings},indent=2))
receipt['status']='meshes_materials_and_wet_catalog_saved';record()
print('VIDEO26_INSTALL_SAVED',len(receipt['meshes']),flush=True)
