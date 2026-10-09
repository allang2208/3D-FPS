"""Save V06 connected clothing and matched recovery clips to the guard entry."""
from pathlib import Path
base=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/import_security_v05.py').read_text(encoding='utf-8')
prefix=base.split("mesh=u.load_asset(report['meshes']['outfit']);entry=")[0].replace('V05','V06')
prefix=prefix.replace('independent torso and sleeves; same-side arm weights; smooth crotch transition; intact hands and boots',
    'continuous shirt shoulders; graph-connected shoulder weights; fitted belt without loose keepers; intact hands and boots')
exec(compile(prefix,'import_security_meshes_v06','exec'))
mesh=u.load_asset(report['meshes']['outfit']);clips={};report['clips']={}
for role,entry in manifest['clips'].items():
    name='A_Security_Male_V06_'+role;anim_path=DEST+'/Animations/V06'
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal=True;options.import_mesh=False;options.import_animations=True
    options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeleton=skeleton
    data=options.anim_sequence_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',manifest['fps'])
    data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('preserve_local_transform',True)
    task=u.AssetImportTask();task.filename=entry['file'];task.destination_path=anim_path;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=options;task.factory=u.FbxFactory()
    AT.import_asset_tasks([task]);clip=u.load_asset(anim_path+'/'+name)
    if not clip or not task.imported_object_paths:raise RuntimeError('Animation import failed '+role)
    clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('rate_scale',entry['rate_scale'])
    for prop in ['enable_root_motion','force_root_lock']:
        if clip.get_editor_property(prop):clip.set_editor_property(prop,False)
    LIB.set_metadata_tag(clip,'SecurityMotionRevision','V06 matched recovery end, ready idle and Walk_B start; whole-arm recovery curves')
    LIB.set_metadata_tag(clip,'SourceAction',entry['source_asset']);save(clip);clips[role]=clip
    report['clips'][role]={'asset':clip.get_path_name(),'source':entry['source_asset'],'duration':clip.get_play_length(),'rate_scale':entry['rate_scale']}
cdo.set_editor_property('visual_mesh',mesh);component.set_skeletal_mesh_asset(mesh)
for role,clip in clips.items():cdo.set_editor_property(role+'_clip',clip)
cdo.set_editor_property('recovery_time',manifest['recovery_time'])
LIB.set_metadata_tag(bp,'UniformRevision','V06 continuous shoulder/arm surface; attached belt and hardware')
LIB.set_metadata_tag(bp,'MotionRevision','V06 Attack_D return matches ready idle and rephased Walk_B; same contact window and total recovery cycle')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
report.update(stage='saved',blueprint=bp.get_path_name(),
    recovery_time=cdo.get_editor_property('recovery_time'),attack_cycle_seconds=manifest['attack_cycle_seconds'],
    contact_time=cdo.get_editor_property('contact_time'),contact_end=cdo.get_editor_property('contact_end'),
    walk_speed_cm_s=cdo.get_editor_property('walk_speed'),
    mesh_location_cm=[old_location.x,old_location.y,old_location.z],
    preserved='Strike contact window, total attack/recovery cycle, walk speed, V05 ground offset, materials, skeleton, physics, capsule, AI, F6 entry')
record();print('SECURITY_V06_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
