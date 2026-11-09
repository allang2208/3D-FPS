"""Publish the scoped animation repair and M249 magazine surface instances."""
from pathlib import Path
import unreal as u,json,gzip,hashlib,zipfile
r=Path(__file__).resolve().parent;p=r.parents[2];E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
inputs=json.loads((r/'inputs.json').read_text());dest='/Game/Weapons/M249/SideMagazine20261108/Finish20'
receipt=r/'install_receipt.json';report=json.loads(receipt.read_text()) if receipt.exists() else dict(saved={},animations=[],profiles=[],meshes={},materials={},complete=False,runtime_tested=False)
profiles={family:('/Game/Weapons/M249/Bipod/DA_M249_SupportGrip' if family=='base' else '/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_'+family) for family in ('base','vertical','canted','prism','angled')}
motions=[json.load(gzip.open(f,'rt')) for f in sorted((r/'Motion').glob('*.json.gz'))]
meshes=[k.split('.')[0] for k in inputs['meshes'] if '/SideMagazine20261108/Meshes/' in k]
targets=[m['asset'] for m in motions]+list(profiles.values())+meshes
def disk(path):return p/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())
    path=a.get_path_name().split('.')[0];report['saved'][path]=hashlib.sha256(disk(path).read_bytes()).hexdigest();receipt.write_text(json.dumps(report,indent=2));return a
def clone(src,dst):return u.load_asset(dst) or E.duplicate_asset(src,dst)
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE is running; assets retained')
dirty={a.get_name() for a in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(targets) or any(x.startswith(dest) for x in dirty):raise RuntimeError('Unsaved target packages retained')
for path,sha in inputs['hashes'].items():
    if hashlib.sha256(disk(path).read_bytes()).hexdigest()!=report['saved'].get(path,sha):raise RuntimeError('Source changed '+path)
if not (r/'Before.zip').exists():
    with zipfile.ZipFile(r/'Before.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in targets:z.write(disk(path),str(disk(path).relative_to(p)))
    (r/'before.json').write_text(json.dumps({path:inputs['hashes'][path] for path in targets},indent=2))
master=clone('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface',dest+'/M_M249MagazineSurface')
for key in ('automatically_set_usage_in_editor','used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):master.set_editor_property(key,False)
errors=L.recompile_material(master)
if errors:raise RuntimeError('Material compilation '+str(errors))
save(master)
receiver=next(v for k,v in inputs['materials'].items() if '/MI_M249_Factory_Receiver.' in k)
old=next(v for k,v in inputs['materials'].items() if '/MI_M249_SideMagazine.' in k)
materials={}
for role,preset in [('Magazine','CleanPolymer'),('Port','CleanSatinSteel')]:
    src='/Game/Weapons/WeaponSurface/Presets/MI_WS_'+preset;mi=clone(src,dest+'/MI_M249_'+role);L.set_material_instance_parent(mi,master)
    baseline=inputs['materials'][src+'.'+src.split('/')[-1]]
    scalars=dict(baseline['scalars']);vectors=dict(baseline['vectors']);textures=dict(baseline['textures'])
    scalars.update(Roughness=.55 if role=='Magazine' else receiver['scalars']['Roughness'],Specular=.5,GrainTileCm=receiver['scalars']['GrainTileCm'],GrainRoughness=.012,MottleRoughness=.005,MottleColor=0.,ScratchAmount=0.,MaskUVChannel=0.,EdgeWear=0. if role=='Magazine' else .025)
    vectors['FinishColor']=receiver['vectors']['PolymerColor'] if role=='Magazine' else receiver['vectors']['FinishColor']
    if role=='Magazine':
        textures.update(SourceBaseColor=old['textures']['DiffuseColorMap'],SurfaceNormal=old['textures']['NormalMap'],SourceRoughness=old['textures']['ShininessMap']);scalars.update(SourceColorWeight=.10,SourceRoughnessWeight=.08,Stipple=.02)
    for k,v in scalars.items():L.set_material_instance_scalar_parameter_value(mi,k,v)
    for k,v in vectors.items():L.set_material_instance_vector_parameter_value(mi,k,u.LinearColor(*v))
    for k,v in textures.items():L.set_material_instance_texture_parameter_value(mi,k,load(v))
    L.update_material_instance(mi);save(mi);materials[role]=mi
    report['materials'][role]=dict(asset=mi.get_path_name(),parent=mi.parent.get_path_name(),normal=L.get_material_instance_texture_parameter_value(mi,'SurfaceNormal').get_path_name(),roughness=L.get_material_instance_scalar_parameter_value(mi,'Roughness'),metallic=L.get_material_instance_scalar_parameter_value(mi,'Metallic'),finish=list(L.get_material_instance_vector_parameter_value(mi,'FinishColor').to_tuple()))
for path in meshes:
    m=load(path);mi=materials['Port' if path.endswith('SidePort') else 'Magazine']
    for i in range(len(m.static_materials)):m.set_material(i,mi)
    save(m);report['meshes'][path]=[s.material_interface.get_path_name() for s in m.static_materials]
for data in motions:
    clip=load(data['asset']);ctl=clip.get_editor_property('controller');ctl.open_bracket('M249 anatomical elbow and receiver response',False)
    try:
        ctl.set_frame_rate(u.FrameRate(numerator=data['fps'],denominator=1),False);ctl.set_number_of_frames(u.FrameNumber(value=round(data['duration']*data['fps'])),False)
        for bone,rows in data['tracks'].items():
            if not bone.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky','ik_hand','WPN_','PKM_','New_')):continue
            if not ctl.set_bone_track_keys(bone,[u.Vector(*v[:3]) for v in rows],[u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:]) for v in rows],False):raise RuntimeError('Track '+bone)
    finally:ctl.close_bracket(False)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Compression '+clip.get_path_name())
    save(clip);report['animations'].append(data['asset']);print('M249_REPAIR20_ACTION_SAVED',clip.get_name(),flush=True)
for family,path in profiles.items():
    a=load(path);incoming=json.load(gzip.open(r/(family+'.json.gz'),'rt'))['clips'];keys={c['base'].split('.')[0] for c in incoming};rows=[];kept=[]
    for c in a.get_editor_property('clips'):
        base=c.get_editor_property('base');retained=c.get_editor_property('retained')
        if base.get_path_name().split('.')[0] in keys:continue
        if retained:kept.append((base,retained));continue
        rows.append(dict(base=base.get_path_name(),duration=c.get_editor_property('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')]))
    if not a.set_shared_clips_from_json(json.dumps(dict(family=family,clips=rows+incoming))):raise RuntimeError('Profile '+family)
    for base,retained in kept:a.keep_clip(base,retained)
    save(a);report['profiles'].append(path)
feed_finish={};exec(compile((r.parent/'Finish29/bindings.py').read_text(),str(r.parent/'Finish29/bindings.py'),'exec'),feed_finish)
report['saved'].update(feed_finish['restore']())
for path in report['meshes']:report['meshes'][path]=[s.material_interface.get_path_name() for s in load(path).static_materials]
report['feed_finish_revision']='Finish29'
report['complete']=True;receipt.write_text(json.dumps(report,indent=2));print('M249_REPAIR20_ASSETS_SAVED',len(report['saved']),flush=True)
exec(compile((r/'readback.py').read_text(),str(r/'readback.py'),'exec'))
