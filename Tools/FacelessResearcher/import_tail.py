# Appended to the material/mesh importer; executed in the existing UE mutex.
source=json.loads((ROOT/'nurse_source.json').read_text(encoding='utf-8'))
fit=json.loads((ROOT/'placement_manifest.json').read_text(encoding='utf-8'))
curves=json.loads((ROOT/'corrective_curves.json').read_text(encoding='utf-8'))
curve_manifest=json.loads((ROOT/'corrective_manifest.json').read_text(encoding='utf-8'))
requested=json.loads((ROOT/'export_receipt.json').read_text(encoding='utf-8'))['morph_names']
actual=[m.get_name() for m in meshes['outfit'].get_editor_property('morph_targets')];mapping={}
for name in requested:
    matches=[n for n in actual if n==name or n.endswith('_'+name)]
    if len(matches)!=1:raise RuntimeError('Morph import did not produce '+name)
    mapping[name]=matches[0]
clips={}
for role in ['idle','walk','attack']:
    clip=copy_asset(source['clips'][role]['source'],'Animations/A_Researcher_'+role)
    if not u.WeaponAnimationAuthoring.rebind_native_animation(clip,skeleton):raise RuntimeError('Cannot attach Nurse tracks to independent researcher skeleton')
    clip.set_preview_skeletal_mesh(meshes['outfit'])
    if role=='walk':clip.set_editor_property('rate_scale',source['clips'][role]['rate_scale']/fit['component_scale'])
    frames=curve_manifest[role]['frames'];duration=clip.get_play_length()
    for name,values in curves[role].items():
        target=mapping[name]
        if u.AnimationLibrary.does_curve_exist(clip,target,u.RawCurveTrackTypes.RCT_FLOAT):u.AnimationLibrary.remove_curve(clip,target)
        u.AnimationLibrary.add_curve(clip,target)
        times=[i*duration/(frames-1) for i in range(frames)]
        u.AnimationLibrary.add_float_curve_keys(clip,target,times,values)
        u.AnimationLibrary.set_curve_meta_data_morph_target(skeleton,target,True)
    LIB.set_metadata_tag(clip,'ResearcherSourceMotion',source['clips'][role]['source'])
    LIB.set_metadata_tag(clip,'ResearcherTailoring','Original Nurse bone tracks; independent motion-driven coat clearance curves')
    save(clip);clips[role]=clip
save(skeleton)
bp=copy_asset('/Game/Monsters/NurseZombie/BP_NurseZombie','BP_FacelessResearcher')
u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
cdo.set_editor_property('visual_mesh',meshes['outfit']);component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(meshes['outfit'])
for role,clip in clips.items():cdo.set_editor_property(role+'_clip',clip)
for key,value in source['properties'].items():cdo.set_editor_property(key,value)
# Native body bindings share Nurse proportions and animations. A small uniform
# component scale gives the designed researcher height without nonuniform bones.
scale=fit['component_scale'];component.set_relative_scale3d(u.Vector(scale,scale,scale))
cdo.get_editor_property('capsule_component').set_capsule_half_height(fit['capsule_half_height_cm'],False)
component.set_relative_location(u.Vector(0,0,fit['mesh_relative_z_cm']),False,False)
tags=[t for t in cdo.get_editor_property('tags') if str(t) not in ['NurseZombie','FacelessReceptionist','FacelessSecurity','FacelessResearcher']]
tags.append(u.Name('FacelessResearcher'));cdo.set_editor_property('tags',tags)
LIB.set_metadata_tag(bp,'ResearcherRevision','V01 high slender faceless researcher; continuous lab coat, paired walls, closed shoes and Nurse motions')
LIB.set_metadata_tag(bp,'SourceGLB','Meshy_AI_Gray_Full_Body_Manneq_1009014620_texture.glb')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
report.update(stage='saved',blueprint=bp.get_path_name(),meshes={k:v.get_path_name() for k,v in meshes.items()},
    animations={k:v.get_path_name() for k,v in clips.items()},skeleton=skeleton.get_path_name(),physics=physics.get_path_name(),
    source_motion=source,placement=fit,morph_names=mapping,
    clothing='Independent continuous coat, trouser and shoe source meshes; consolidated runtime skin; offline corrective shapes; no runtime cloth solver',
    complete_body_preserved=True,runtime_tested=False,rendered=False)
record();print('RESEARCHER_UE_SAVED '+json.dumps({'saved_count':len(report['saved']),'blueprint':report['blueprint']}),flush=True)
