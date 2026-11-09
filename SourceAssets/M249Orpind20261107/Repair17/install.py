"""Import actual models, native animations and profile deltas, then save assets."""
import unreal as u,json,gzip,hashlib,zipfile
from pathlib import Path
r=Path(__file__).resolve().parent;p=r.parents[2];D='/Game/Weapons/M249/SideMagazine20261108'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report_path=r/'install_receipt.json';report=json.loads(report_path.read_text()) if report_path.exists() else dict(saved={},meshes={},animations={},profiles={},runtime_tested=False)
report['complete']=False
inputs=json.loads((r/'inputs.json').read_text())
def disk(path):return p/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def record():report_path.write_text(json.dumps(report,indent=2))
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing production source '+path)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())
    report['saved'][a.get_path_name().split('.')[0]]=hashlib.sha256(disk(a.get_path_name()).read_bytes()).hexdigest();record();return a
def clone(src,dst):return u.load_asset(dst) or E.duplicate_asset(src,dst)
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE is running; assets retained')
dirty={a.get_name() for a in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
profiles={family:('/Game/Weapons/M249/Bipod/DA_M249_SupportGrip' if family=='base' else '/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_'+family) for family in ('base','vertical','canted','prism','angled')}
if any(x.startswith(D) or x in profiles.values() for x in dirty):raise RuntimeError('Preserve unsaved M249 work')
for path,sha in inputs['hashes'].items():
    key=path.split('.')[0]
    if key not in report['saved'] and hashlib.sha256(disk(path).read_bytes()).hexdigest()!=sha:raise RuntimeError('Source changed '+key)
if not (r/'BeforeProfiles.zip').exists():
    with zipfile.ZipFile(r/'BeforeProfiles.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in profiles.values():z.write(disk(path),str(disk(path).relative_to(p)))
source=load('/Game/Weapons/M4/SurfaceStandard20261001/Materials/MI_M4_R01_magazine_7a22bc212d')
master=clone(source.get_base_material().get_path_name(),D+'/Materials/M_M249_SideMagazine')
for key in ('automatically_set_usage_in_editor','used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):master.set_editor_property(key,False)
errors=L.recompile_material(master)
if errors:raise RuntimeError('Magazine material compilation '+str(errors))
save(master)
poly=clone(source.get_path_name(),D+'/Materials/MI_M249_SideMagazine');L.set_material_instance_parent(poly,master)
scalars={str(x) for x in L.get_scalar_parameter_names(poly)};vectors={str(x) for x in L.get_vector_parameter_names(poly)}
for key,value in {'Roughness':.55,'GrainRoughness':.012,'MottleRoughness':.005,'EdgeWear':.02,'ScratchAmount':0.}.items():
    if key in scalars:L.set_material_instance_scalar_parameter_value(poly,key,value)
if 'FinishColor' in vectors:L.set_material_instance_vector_parameter_value(poly,'FinishColor',u.LinearColor(.019,.019,.018,1))
L.update_material_instance(poly);save(poly)
metal=clone('/Game/Weapons/M249/Surface20261108/Materials/MI_M249_CommonRail',D+'/Materials/MI_M249_SidePort')
L.set_material_instance_vector_parameter_value(metal,'FinishColor',u.LinearColor(.034,.035,.037,1));L.set_material_instance_scalar_parameter_value(metal,'Roughness',.42);L.update_material_instance(metal);save(metal)
cv='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(cv);u.SystemLibrary.execute_console_command(None,cv+' 0')
try:
    for f in sorted((r/'Exports').glob('*.fbx')):
        path=D+'/Meshes/'+f.stem;mesh=u.load_asset(path)
        if not mesh:
            t=u.AssetImportTask();t.filename=str(f);t.destination_path=D+'/Meshes';t.destination_name=f.stem;t.automated=True;t.save=False
            ui=u.FbxImportUI();ui.import_mesh=True;ui.import_as_skeletal=False;ui.import_materials=False;ui.import_textures=False;ui.import_animations=False
            ui.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;ui.automated_import_should_detect_type=False
            data=ui.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.convert_scene_unit=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
            t.options=ui;t.factory=u.FbxFactory();A.import_asset_tasks([t]);mesh=load(path)
        for i in range(len(mesh.static_materials)):mesh.set_material(i,metal if f.stem.endswith('SidePort') else poly)
        u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
        settings=S.get_lod_build_settings(mesh,0);settings.recompute_normals=False;settings.recompute_tangents=True;settings.generate_lightmap_u_vs=False;S.set_lod_build_settings(mesh,0,settings)
        u.ASH12AttachmentAssetTools.finish_and_validate_build(mesh);save(mesh);report['meshes'][f.stem]=path;record();print('M249_SIDE_MESH_SAVED',f.stem,flush=True)
finally:u.SystemLibrary.execute_console_command(None,cv+' '+str(previous))
native=load('/Game/Weapons/M249/SK_M249_V7')
for f in sorted((r/'Motion').glob('*.json.gz')):
    data=json.loads(gzip.decompress(f.read_bytes()));clip=clone(data['source'],data['asset'])
    if not u.WeaponAnimationAuthoring.rebind_native_animation(clip,native.skeleton):raise RuntimeError('Animation skeleton')
    clip.set_preview_skeletal_mesh(native);ctl=clip.get_editor_property('controller');ctl.open_bracket('M249 side magazine native contacts',False)
    try:
        ctl.set_frame_rate(u.FrameRate(numerator=data['fps'],denominator=1),False);ctl.set_number_of_frames(u.FrameNumber(value=round(data['duration']*data['fps'])),False)
        for bone,rows in data['tracks'].items():
            ctl.add_bone_curve(bone,False)
            if not ctl.set_bone_track_keys(bone,[u.Vector(*v[:3]) for v in rows],[u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:]) for v in rows],False):raise RuntimeError('Track '+bone)
    finally:ctl.close_bracket(False)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation build')
    save(clip);report['animations'][f.name]=data['asset'];record();print('M249_SIDE_ANIMATION_SAVED',f.name,flush=True)
for family,path in profiles.items():
    profile=load(path);temp=u.new_object(u.WeaponGripProfile)
    if not temp.set_shared_clips_from_json(gzip.decompress((r/(family+'.json.gz')).read_bytes()).decode()):raise RuntimeError('Grip import '+family)
    incoming=list(temp.get_editor_property('clips'));keys={c.get_editor_property('base').get_path_name() for c in incoming}
    retained=[c for c in profile.get_editor_property('clips') if c.get_editor_property('base').get_path_name() not in keys]
    rows=[];kept=[]
    for c in retained:
        base=c.get_editor_property('base');other=c.get_editor_property('retained')
        if other:kept.append((base,other));continue
        rows.append(dict(base=base.get_path_name(),duration=c.get_editor_property('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')]))
    rows+=json.loads(gzip.decompress((r/(family+'.json.gz')).read_bytes()))['clips']
    if not profile.set_shared_clips_from_json(json.dumps(dict(family=family,clips=rows))):raise RuntimeError('Merge profile '+family)
    for base,other in kept:profile.keep_clip(base,other)
    save(profile);report['profiles'][family]=path;record()
feed_finish={};exec(compile((r.parent/'Finish29/bindings.py').read_text(),str(r.parent/'Finish29/bindings.py'),'exec'),feed_finish)
report['saved'].update(feed_finish['restore']())
report['complete']=True;record();print('M249_SIDE_MAGAZINE_ASSETS_SAVED',len(report['saved']),flush=True)
