"""Replace only old/new cloth-box sections in the current body and prop source."""
from pathlib import Path
O=Path(__file__).parent
header=(O.parent/'Assembly40/install.py').read_text().split('if u.get_editor_subsystem')[0]
exec(compile(header.replace('Assembly40','ClothTop45').replace('A40','C45'),str(O/'install.py'),'exec'),globals())
materials=json.loads((O/'materials.json').read_text());sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if sub and sub.get_game_world():raise RuntimeError('PIE active; existing assets retained')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key,row in cap.items():
    p=row['asset'];expected=receipt['saved'].get(p,{}).get('sha256',row['sha256'])
    if p in dirty or sha(p)!=expected:raise RuntimeError('Concurrent target retained '+p)
def backup(p):
    if p in receipt['backups']:return
    target=O/'Before'/file(p).relative_to(PROJECT/'Content');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file(p),target);receipt['backups'][p]={'bytes':str(target),'sha256':sha(p)};record()
digest=hashlib.sha256(Path(model['fbx']).read_bytes()).hexdigest();sourcepath=P+'/Parts/SK_C45_Boxes_'+digest[:8];source=u.load_asset(sourcepath)
if not source:
    body=load(cap['Body']['asset']);opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=body.skeleton
    data=opt.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False);data.set_editor_property('preserve_smoothing_groups',True);data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task=u.AssetImportTask();task.filename=model['fbx'];task.destination_path=P+'/Parts';task.destination_name=sourcepath.rsplit('/',1)[1];task.factory=u.FbxFactory();task.options=opt;task.automated=True;task.save=False;flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
    try:A.import_asset_tasks([task])
    finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
    source=load(sourcepath)
partslots=[s.copy() for s in source.materials]
for i,s in enumerate(partslots):
    name=str(s.material_slot_name)
    if name not in model['roles']:raise RuntimeError('Unmapped '+name)
    s.material_interface=load(materials[model['roles'][name]]);partslots[i]=s
source.materials=partslots;save(source)
for key in ['Body','Props']:
    p=cap[key]['asset']
    if receipt['saved'].get(p,{}).get('source_sha256')==digest:continue
    current=load(p);native=dynamic(current);added=dynamic(source);slots=[s.copy() for s in current.materials];remove=[]
    _,tl,_=Q.get_all_triangle_indices(native,False)
    for ti in range(len(L.convert_triangle_list_to_array(tl))):
        mid,valid=M.get_triangle_material_id(native,ti)
        if valid and str(slots[mid].material_slot_name).startswith(('M_LMG201_Cloth33__OldBox','M_LMG201_Cloth33__NewBox')):remove.append(ti)
    if not remove:raise RuntimeError('No current cloth box '+p)
    Ed.delete_triangles_from_mesh(native,L.convert_array_to_index_list(remove,u.GeometryScriptIndexType.TRIANGLE),True);B.copy_bones_from_mesh(native,added,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True));names={str(s.material_slot_name):i for i,s in enumerate(slots)}
    for s in partslots:
        name=str(s.material_slot_name)
        if name not in names:names[name]=len(slots);slots.append(s.copy())
        else:t=slots[names[name]];t.material_interface=s.material_interface;slots[names[name]]=t
    for i in range(len(partslots)):M.remap_material_i_ds(added,i,1000+i)
    for i,s in enumerate(partslots):M.remap_material_i_ds(added,1000+i,names[str(s.material_slot_name)])
    Ed.append_mesh(native,added,u.Transform(),True)
    if key=='Body':
        candidate=u.load_asset(P+'/SK_C45_Installed') or E.duplicate_asset(p,P+'/SK_C45_Installed');copy_to(native,candidate,slots);save(candidate)
    backup(p);copy_to(native,current,slots);current.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports'/('After_'+key+'.fbx')),0,'ClothTop45: local fabric crown and reinforced belt outlet');E.set_metadata_tag(current,'201ClothTopRevision','ClothTop45: continuous upper rim, cloth UV transition, bounded outlet walls, old/new box contract preserved');E.set_metadata_tag(current,'201ClothTopSource',str(O/'LMG201_ClothTop45.blend'));save(current)
    receipt['saved'][p]={'sha256':sha(p),'source_sha256':digest,'removed_box_triangles':len(remove)};record();print('C45_MESH_SAVED',key,flush=True)
    del native,added
p=cap['Wet']['asset']
if p not in receipt['saved']:
    current=load(p);mapping=dict(current.get_editor_property('wet_materials'))
    for material in materials.values():mapping[material]=load(material)
    backup(p);current.set_editor_property('wet_materials',mapping);save(current);receipt['saved'][p]={'sha256':sha(p)};record()
icon=json.loads((O/'icon.json').read_text());p='/Game/ColdSteelData/AttachmentIcons20260913/'+icon['key']
if p not in receipt['saved']:
    if p in dirty:raise RuntimeError('Unsaved icon retained')
    backup(p);png=PROJECT/'Content/ColdSteelData/AttachmentIcons20260913'/(icon['key']+'.png');oldpng=O/'Before'/png.relative_to(PROJECT/'Content');oldpng.parent.mkdir(parents=True,exist_ok=True)
    if png.exists() and not oldpng.exists():shutil.copy2(png,oldpng)
    shutil.copy2(icon['file'],png);task=u.AssetImportTask();task.filename=str(png);task.destination_path=p.rsplit('/',1)[0];task.destination_name=icon['key'];task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);texture=load(p);texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(texture);receipt['saved'][p]={'sha256':sha(p),'png':str(png)};record()
bindings={}
for key in ['Body','Props']:
    a=load(cap[key]['asset']);bindings[a.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in a.materials};export(a,key)
manifest=S/'Material21/bindings.json';data=json.loads(manifest.read_text());data['meshes'].update(bindings);data['current_cloth_box_revision']='ClothTop45';manifest.write_text(json.dumps(data,indent=2));(O/'bindings.json').write_text(json.dumps(bindings,indent=2));receipt.update(status='current_c45_saved',animations_modified=False,native_code_modified=False,runtime_tested=False,rendered_acceptance=False,materials=materials,source=str(O/'LMG201_ClothTop45.blend'));record();print('C45_CURRENT_SAVED',len(receipt['saved']),flush=True)
