"""Save palm-first motion and placement on the existing hand assets. No PIE/test/render."""
from pathlib import Path
import json,math,shutil,sys
import unreal as u

ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
DEST='/Game/Monsters/FleshHand';REV='PalmForward20260927'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale

def install():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong UE project')
    receipt=json.loads((ROOT/'ue_installation.json').read_text(encoding='utf-8'))
    source=json.loads((ROOT/'Animations/authoring.json').read_text(encoding='utf-8'))
    if source.get('choreography_revision')!=REV:raise RuntimeError('Palm-forward animation exports required')
    blueprints=[DEST+'/BP_FleshHand',DEST+'/BP_FleshHandMinion']
    targets=blueprints+[DEST+'/SM_FleshHand_PalmFist']+[DEST+'/Animations/A_FleshHand_'+role for role in source['clips']]
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(targets):raise RuntimeError('Preserving unsaved target assets: '+str(sorted(dirty.intersection(targets))))
    backup=(ROOT.parents[1]/'trash/monster-hands-20260927/SourceAssets/FleshHand20260926/BeforePalmForward/Content')
    for path in targets:
        file=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        copy=backup/file.relative_to(PROJECT/'Content')
        if file.exists() and not copy.exists():
            copy.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,copy)
    report={'revision':REV,'state':'importing','saved':[],'root_units':{},
            'palm_source_axis':[0,1,0],'actor_front_axis':[1,0,0],
            'source_anatomy':'Palm crease UV (0.53125,0.28125) normal +Y; middle fingernail UV (0.184375,0.678125) normal -Y',
            'runtime_tested':False,'game_started':False,'rendered':False}
    def record():
        (ROOT/'palm_forward_installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    def load(path):
        asset=u.load_asset(path)
        if not asset:raise RuntimeError('Missing asset: '+path)
        return asset
    def save(asset):
        LIB.set_metadata_tag(asset,'FleshHand.Revision','GreenLocalHand20260927V1')
        LIB.set_metadata_tag(asset,'FleshHand.PalmForward',REV)
        if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
        report['saved'].append(asset.get_path_name());record()
    def reimport(file,path,options):
        asset=load(path)
        if LIB.get_metadata_tag(asset,'FleshHand.Revision')!='GreenLocalHand20260927V1':raise RuntimeError('Foreign asset: '+path)
        task=u.AssetImportTask();task.filename=str(file);task.destination_path=path.rsplit('/',1)[0]
        task.destination_name=path.rsplit('/',1)[1];task.automated=True;task.save=False;task.replace_existing=True;task.options=options
        TOOLS.import_asset_tasks([task])
        if not task.imported_object_paths:raise RuntimeError('Import produced no asset: '+path)
        return load(path)
    record()
    mesh=load(DEST+'/SK_FleshHand_Green');skeleton=mesh.get_editor_property('skeleton')
    cvar='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None,cvar+' 0')
    try:
        for role,row in source['clips'].items():
            options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            options.import_as_skeletal=True;options.import_mesh=False;options.import_animations=True
            options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
            data=options.anim_sequence_import_data
            data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',60)
            data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            data.set_editor_property('remove_redundant_keys',False)
            clip=reimport(row['file'],DEST+'/Animations/A_FleshHand_'+role,options)
            clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',False)
            clip.set_editor_property('rate_scale',1.);clip.set_preview_skeletal_mesh(mesh)
            report['root_units'][role]=match_bind_root_scale(clip,mesh);save(clip)
        options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh=True;options.import_as_skeletal=False;options.import_materials=False;options.import_textures=False;options.import_animations=False
        options.static_mesh_import_data.set_editor_property('combine_meshes',True)
        options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
        fist=reimport(ROOT/'Animations/SM_FleshHand_PalmFist.fbx',DEST+'/SM_FleshHand_PalmFist',options)
        fist.set_material(0,load(DEST+'/MI_FleshHand_GreenSkin'));save(fist)
    finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(previous))

    # The bind skeleton has not changed: reuse its recorded source/import coordinates.
    fit=receipt['coordinate_fit'];src=fit['source_heads'];dst=fit['imported_heads']
    def sub(a,b):return [a[i]-b[i] for i in range(3)]
    def det(a,b,c):return a[0]*(b[1]*c[2]-b[2]*c[1])-b[0]*(a[1]*c[2]-a[2]*c[1])+c[0]*(a[1]*b[2]-a[2]*b[1])
    a,b,c=[sub(p,src[0]) for p in src[1:]]
    forward=json.loads((ROOT/'LocalRig/rig_definition.json').read_text(encoding='utf-8'))['palm_outward_axis']
    d=det(a,b,c);coeff=[det(forward,b,c)/d,det(a,forward,c)/d,det(a,b,forward)/d]
    edges=[sub(p,dst[0]) for p in dst[1:]]
    direction=[sum(coeff[j]*edges[j][i] for j in range(3)) for i in range(3)]
    yaw=-math.degrees(math.atan2(direction[1],direction[0]))
    rotation=u.Rotator(pitch=0.,yaw=yaw,roll=0.)
    report['rotation']={'pitch':0.,'yaw':yaw,'roll':0.}
    for path in blueprints:
        bp=load(path);bp.modify();cdo=u.get_default_object(bp.generated_class());cdo.modify()
        component=cdo.get_editor_property('mesh');component.modify();component.set_editor_property('relative_rotation',rotation)
        fist_component=u.find_object(cdo,'PalmFist')
        if not fist_component:raise RuntimeError('Missing PalmFist component: '+path)
        fist_component.modify();fist_component.set_editor_property('relative_rotation',rotation)
        cdo.set_editor_property('use_controller_rotation_yaw',False)
        movement=cdo.get_editor_property('character_movement');movement.modify()
        movement.set_editor_property('orient_rotation_to_movement',True)
        save(bp)
    receipt['coordinate_fit'].update(model_forward_cm=direction,mesh_yaw=yaw,palm_source_axis=forward)
    report['state']='assets_saved'
    receipt['palm_forward_correction']=report
    (ROOT/'ue_installation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    record();u.log('FLESHHAND_PALM_FORWARD_SAVED '+json.dumps(report,ensure_ascii=False))

install()
