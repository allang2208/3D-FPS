"""Short UE import/save batches for geometry produced offline in Blender.

No UE mesh reduction, animation import, PIE, or acceptance runs.
"""
from pathlib import Path
import json, shutil, sys, traceback, time, math
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/AlienGeometry20261006/RemeshV3'
DEST='/Game/Monsters/RemeshV3'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
T=u.AssetToolsHelpers.get_asset_tools();S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
LIVE={
 'SpiralPillarM14':'/Game/Monsters/SpiralPillarM14/SK_M14_SupportSkin_v15',
 'HangingBellM09':'/Game/Monsters/HangingBellM09/V04/SK_M09',
 'M10Mawcrawler':'/Game/Monsters/M10Mawcrawler/SurfaceRigV5/SK_M10_SurfaceRig_V5',
 'LurkerM08':'/Game/Monsters/LurkerM08/CanineV03/SK_LurkerM08_CanineV03',
}
BLUEPRINT={
 'SpiralPillarM14':'/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14',
 'M10Mawcrawler':'/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler',
 'LurkerM08':'/Game/Monsters/LurkerM08/BP_LurkerM08',
}

def load(path):
    result=u.load_asset(path)
    if not result:raise RuntimeError('Missing asset '+path)
    return result

def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf8')

def backup(asset,out):
    relative=asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset'
    src=PROJECT/'Content'/relative;dest=out/'Before'/relative
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(src,dest)

def save(asset,report):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())

def imported(file,name,folder,options=None,replace=False):
    task=u.AssetImportTask();task.filename=str(file);task.destination_name=name;task.destination_path=folder
    task.automated=True;task.save=False;task.replace_existing=replace;task.replace_existing_settings=replace
    if options:task.options=options;task.factory=u.FbxFactory()
    T.import_asset_tasks([task])
    return load(folder+'/'+name)

def original_material(species,name):
    if species=='HangingBellM09':return load('/Game/Monsters/HangingBellM09/V04/Materials/M_M09_Body')
    if species=='SpiralPillarM14':return load('/Game/Monsters/SpiralPillarM14/Materials/M_M14_'+name.split('_')[-1])
    if species=='LurkerM08':return load('/Game/Monsters/LurkerM08/Materials/M_M08_'+('InnerArch' if 'InnerArch' in name else 'Skin'))
    if name.startswith('M_M10_'):return load('/Game/Monsters/M10Mawcrawler/SurfaceRigV5/'+name)
    return load('/Game/Monsters/M10Mawcrawler/Materials/M_M10_MeshySurface')

def new_material(source,textures,folder,report):
    path=folder+'/'+source.get_name()+'_RemeshV3'
    mat=u.load_asset(path) or E.duplicate_asset(source.get_path_name(),path)
    if isinstance(mat,u.MaterialInstanceConstant):
        # Preserve authored instance parameters while moving its parent to the
        # new atlas. This also covers instances added after the original import.
        parent=new_material(source.get_editor_property('parent'),textures,folder,report)
        L.set_material_instance_parent(mat,parent)
        for value in list(mat.get_editor_property('texture_parameter_values')):
            old=value.get_editor_property('parameter_value')
            if old:
                role=texture_role(old.get_name())
                if role:L.set_material_instance_texture_parameter_value(mat,value.get_editor_property('parameter_info').get_editor_property('name'),textures[role])
    else:
        changed=[]
        for node in L.get_material_expressions(mat):
            if not isinstance(node,u.MaterialExpressionTextureBase):continue
            old=node.get_editor_property('texture')
            if not old:continue
            role=texture_role(old.get_name())
            if role:
                node.set_editor_property('texture',textures[role]);changed.append(role)
        if 'BaseColor' not in changed:raise RuntimeError('No source color sampler identified in '+source.get_path_name())
        errors=L.recompile_material(mat)
        if errors:raise RuntimeError(str(errors))
    save(mat,report);return mat

def texture_role(name):
    key=name.lower().replace('_','')
    if 'normal' in key:return 'Normal'
    if 'metallicrough' in key or 'roughnessmetal' in key or key.endswith('mr') or 'orm' in key:return 'MetallicRoughness'
    if 'basecolor' in key or 'albedo' in key or 'diffuse' in key or name.lower().endswith('_base'):return 'BaseColor'
    return None

def materials(species,author,report):
    folder=DEST+'/'+species;tex={}
    for role,file in author['textures'].items():
        path=folder+'/Textures/T_'+species+'_'+role
        asset=u.load_asset(path) or imported(file,path.rsplit('/',1)[1],folder+'/Textures')
        if role!='BaseColor':asset.set_editor_property('srgb',False)
        if role=='Normal':asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);asset.set_editor_property('flip_green_channel',True)
        elif role=='MetallicRoughness':asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        save(asset,report);tex[role]=asset
    result={};cache={}
    for name,entry in author['materials'].items():
        source=original_material(species,entry['source_material_name']);path=source.get_path_name()
        if entry['new_texture']:
            if path not in cache:cache[path]=new_material(source,tex,folder+'/Materials',report)
            result[name]=cache[path]
        else:result[name]=source
    return result

def assign_materials(mesh,mapping):
    slots=list(mesh.get_editor_property('materials'))
    for slot in slots:
        name=str(slot.get_editor_property('imported_material_slot_name'))
        if name not in mapping:name=str(slot.get_editor_property('material_slot_name'))
        if name not in mapping:raise RuntimeError('Unmapped imported material slot '+name)
        slot.set_editor_property('material_interface',mapping[name])
    mesh.set_editor_property('materials',slots)

def import_live(species,author,out,report):
    mesh=load(LIVE[species]);backup(mesh,out)
    if report.get('live_imported'):
        export_corpse_input(species,mesh,out,report)
        return
    skeleton=mesh.get_editor_property('skeleton');physics=mesh.get_editor_property('physics_asset')
    mapping=materials(species,author,report)
    report['original_skeleton']=skeleton.get_path_name();report['original_physics']=physics.get_path_name() if physics else None
    write(out/'installation.json',report)
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False
    options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeleton=skeleton
    data=options.skeletal_mesh_import_data
    data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
    data.set_editor_property('import_morph_targets',True);data.set_editor_property('import_mesh_lods',False)
    data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    data.set_editor_property('normal_generation_method',u.FBXNormalGenerationMethod.MIKK_T_SPACE)
    path=LIVE[species];folder,name=path.rsplit('/',1)
    mesh=imported(author['lods'][0]['file'],name,folder,options,replace=True)
    mesh.set_editor_property('physics_asset',physics)
    assign_materials(mesh,mapping)
    # Reimporting in place preserves every animation, BP and native hard path.
    # ImportLOD consumes authored FBXs; it never calls RegenerateLOD here.
    for item in author['lods'][1:]:
        level=item['level']
        if S.import_lod(mesh,level,item['file'])!=level:raise RuntimeError('LOD import failed '+str(level))
    assign_materials(mesh,mapping)
    models=list(mesh.get_editor_property('source_models'))
    for i,model in enumerate(models):
        size=model.get_editor_property('screen_size');size.set_editor_property('default',[1.,.45,.22,.09][i]);model.set_editor_property('screen_size',size)
    mesh.set_editor_property('source_models',models)
    if species=='M10Mawcrawler':
        if not u.M10Mawcrawler.configure_surface_rig(mesh):raise RuntimeError('Cannot bind imported tissue morph names to the production animation node')
        save(skeleton,report)
    E.set_metadata_tag(mesh,'AlienGeometry.Revision',author.get('revision','MeshyRemeshV3')+' offline Blender authoring')
    save(mesh,report)
    if species in BLUEPRINT:
        bp=load(BLUEPRINT[species]);component=u.get_default_object(bp.generated_class()).get_editor_property('mesh')
        if list(component.get_editor_property('override_materials')):
            backup(bp,out)
            component.set_editor_property('override_materials',[slot.material_interface for slot in mesh.get_editor_property('materials')])
            save(bp,report)
    report['live_imported']=True;report['mesh']=mesh.get_path_name();report['offline_lods']=author['lods']
    export_corpse_input(species,mesh,out,report)

def export_corpse_input(species,mesh,out,report):
    # Generate exact UE-space input for the separate offline corpse embedding.
    if not u.M14SoftBodyData.export_surface(mesh,str(out/'surface.bin'),[]):raise RuntimeError('Cannot export reduced corpse surface')
    if species=='SpiralPillarM14':
        cage=json.loads((PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV19/Exports/cage.json').read_text())
        # Match BuildCorpse's legacy Blender-axis adapter using the production
        # reference skeleton. The modifier is read only; never commit it.
        modifier=u.SkeletonModifier()
        if not modifier.set_skeletal_mesh(mesh):raise RuntimeError('Cannot read M14 reference axes')
        base=modifier.get_bone_transform('base',True).translation
        def axis(name):
            p=modifier.get_bone_transform(name,True).translation
            x,y=p.x-base.x,p.y-base.y;length=math.hypot(x,y)
            return x/length,y/length
        x,y=axis('roottoe_00'),axis('roottoe_02')
        cage['nodes']=[[x[0]*p[0]+y[0]*p[1],x[1]*p[0]+y[1]*p[1],p[2]] for p in cage['nodes']]
        cage['coordinates']='mesh_m'
        write(out/'cage.json',cage)
    else:shutil.copy2(PROJECT/'SourceAssets/MonsterSoftCorpse20261005'/species/'cage.json',out/'cage.json')
    report['stage']='live_saved_waiting_offline_corpse_binding'

def install_corpse(species,author,out,report):
    mesh=load(LIVE[species]);folder=DEST+'/'+species
    corpse_path=folder+'/SK_'+species+'_SoftCorpse'
    data_path=folder+'/DA_'+species+'_SoftCorpse'
    data=u.load_asset(data_path)
    if data and data.get_editor_property('corpse_mesh'):
        corpse=data.get_editor_property('corpse_mesh')
    else:
        corpse=u.load_asset(corpse_path) or E.duplicate_asset(mesh.get_path_name(),corpse_path)
        count=S.get_lod_count(corpse)
        if count>1 and not S.remove_lods(corpse,list(range(1,count))):raise RuntimeError('Cannot remove unbound live LODs from corpse')
        skel_path=folder+'/SKEL_'+species+'_SoftCorpse'
        skeleton=u.load_asset(skel_path) or E.duplicate_asset(mesh.get_editor_property('skeleton').get_path_name(),skel_path)
        if not data:
            factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.M14SoftBodyData)
            data=T.create_asset(data_path.rsplit('/',1)[1],folder,u.M14SoftBodyData,factory)
        if not u.M14SoftBodyData.build_corpse(corpse,skeleton,data,str(out/'cage.json'),str(out/'embedding.bin')):raise RuntimeError('Reduced corpse binding failed')
        save(skeleton,report)
    sys.path.insert(0,str(PROJECT/'Tools/MonsterSoftCorpse'))
    import corpse_materials
    corpse_materials.DEST=folder+'/CorpseMaterials'
    # A duplicated live mesh must not carry the previous death binding and
    # retain a hard dependency on its million-face historical corpse.
    userdata=list(corpse.get_editor_property('asset_user_data'))
    corpse.set_editor_property('asset_user_data',[entry for entry in userdata if entry and entry.get_class().get_name()!='MonsterSoftCorpseBinding'])
    slots=list(mesh.get_editor_property('materials'));saved=set()
    for slot in slots:slot.set_editor_property('material_interface',corpse_materials.make(slot.get_editor_property('material_interface'),saved))
    corpse.set_editor_property('materials',slots);report['saved'].extend(sorted(saved));save(corpse,report);save(data,report)
    u.M14SoftBodyData.bind_to_living_mesh(mesh,data);save(mesh,report)
    if species=='SpiralPillarM14':
        bp=load('/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14');backup(bp,out)
        cdo=u.get_default_object(bp.generated_class());cdo.set_editor_property('soft_body_death_data',data)
        save(bp,report)
    report.update(stage='saved_and_bound',complete=True,corpse=corpse.get_path_name(),corpse_data=data.get_path_name(),
        corpse_lods=1,animations_reimported=False,native_build_required=False,user_testing_pending=True)

def run(species,stage):
    out=ROOT/species;author=json.loads((out/'authoring.json').read_text(encoding='utf8'))
    if not author['complete']:raise RuntimeError('Offline authoring incomplete')
    file=out/'installation.json'
    report=json.loads(file.read_text(encoding='utf8')) if file.exists() else dict(species=species,complete=False,saved=[],tested=False,rendered=False)
    report.pop('error',None);start=time.time()
    # Protect actual unsaved packages. No cross-session messages or polling.
    prefixes=(LIVE[species],DEST+'/'+species,BLUEPRINT.get(species,LIVE[species]))
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if package.get_name().startswith(prefixes):raise RuntimeError('Preserving unsaved asset '+package.get_name())
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        level=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level and level.is_in_play_in_editor():
            report['stage']='waiting_for_pie';write(file,report)
            print('REMESH_V3_WAITING_FOR_PIE '+species,flush=True)
            return
    cvar='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None,cvar+' 0')
    try:
        report['stage']=stage;write(file,report)
        if stage=='import':import_live(species,author,out,report)
        elif stage=='corpse':install_corpse(species,author,out,report)
        else:raise RuntimeError('Unknown production stage '+stage)
        report[stage+'_seconds']=round(time.time()-start,2)
        if report.get('live_imported'):
            author['ue_imported']=True;write(out/'authoring.json',author)
        write(file,report);print('REMESH_V3_SAVED '+species+' '+stage,flush=True)
    except Exception:
        report['error']=traceback.format_exc();write(file,report);raise
    finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(old))

if __name__=='__main__':
    command=u.SystemLibrary.get_command_line()
    def arg(key):return command.split('-'+key+'=',1)[1].split()[0]
    run(arg('RemeshSpecies'),arg('RemeshStage'))
