"""Import the gardener outfit and clone the researcher's complete animation setup."""
import json,traceback
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/EcologyGardener20261014/V01')
DEST='/Game/Monsters/EcologyGardener';SOURCE='/Game/Monsters/FacelessResearcher'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
manifest=json.loads((ROOT/'authoring_receipt.json').read_text(encoding='utf8'))
report={'stage':'importing','saved':[],'runtime_tested':False,'multiplayer_tested':False,'rendered':False}
def record():(ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()
def imported(file,folder,name,options=None):
    path=folder+'/'+name
    if E.does_asset_exist(path):return u.load_asset(path)
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=False
    if options:task.options=options;task.factory=u.FbxFactory()
    AT.import_asset_tasks([task]);asset=u.load_asset(path)
    if not asset:raise RuntimeError('Import failed '+path)
    return asset
def connect(source,output,dest,pin):
    normalize=lambda s:''.join(c.lower() for c in str(s) if c.isalnum())
    names=M.get_material_expression_input_names(dest)
    target=next((p for p in names if normalize(p)==normalize(pin)),None)
    if target is None:target=next((p for p in names if normalize(p).startswith(normalize(pin))),None)
    if target is None or not M.connect_material_expressions(source,output,dest,target):raise RuntimeError('Material input '+pin)
try:
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Preserve active PIE')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved gardener assets')
    source=u.load_asset(SOURCE+'/BP_FacelessResearcher')
    cdo=u.get_default_object(source.generated_class());source_mesh=cdo.get_editor_property('visual_mesh')
    if source_mesh.get_name()!='SK_FacelessResearcher_V05':raise RuntimeError('Researcher source changed from the authored V05 outfit')
    skeleton=source_mesh.get_editor_property('skeleton');physics=source_mesh.get_editor_property('physics_asset')
    textures={}
    for file in sorted((ROOT/'Textures').glob('*.png')):
        tex=imported(file,DEST+'/Textures','T_'+file.stem)
        normal=file.stem.endswith('_Normal');data=normal or file.stem.endswith('_ORM')
        tex.set_editor_property('srgb',not data);tex.set_editor_property('never_stream',False)
        if normal:
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
            tex.set_editor_property('flip_green_channel',True)
        elif data:tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        save(tex);textures[file.stem]=tex
    materials={}
    for family in manifest['material_families']:
        name='M_Gardener_'+family;path=DEST+'/Materials/'+name
        mat=u.load_asset(path) if E.does_asset_exist(path) else AT.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        M.delete_all_material_expressions(mat)
        # Usage changes can compile immediately; set them before adding texture nodes.
        # RecompileMaterial below refreshes the completed graph's texture references.
        mat.set_editor_property('two_sided',False)
        mat.set_editor_property('used_with_skeletal_mesh',True)
        mat.set_editor_property('used_with_morph_targets',True)
        cloth=family in ('Workwear','Trousers','Binding')
        slab=M.create_material_expression(mat,u.MaterialExpressionSubstrateSlabBSDF if cloth else u.MaterialExpressionSubstrateShadingModels,650,0)
        samples={}
        for i,(suffix,sampler) in enumerate([('BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR),
                ('Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),('ORM',u.MaterialSamplerType.SAMPLERTYPE_MASKS)]):
            node=M.create_material_expression(mat,u.MaterialExpressionTextureSample,-500,i*220)
            node.texture=textures['Gardener_'+family+'_'+suffix];node.sampler_type=sampler;samples[suffix]=node
        # Rest-space vertex soil coverage was authored on the garment, not on the body.
        wear=M.create_material_expression(mat,u.MaterialExpressionVertexColor,-500,-180)
        soil=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-250,-180)
        soil.constant=u.LinearColor(.095,.052,.018,1)
        mixed=M.create_material_expression(mat,u.MaterialExpressionLinearInterpolate,100,0)
        connect(samples['BaseColor'],'RGB',mixed,'A');connect(soil,'',mixed,'B');connect(wear,'R',mixed,'Alpha')
        connect(mixed,'',slab,'DiffuseAlbedo' if cloth else 'BaseColor')
        connect(samples['Normal'],'RGB',slab,'Normal');connect(samples['ORM'],'G',slab,'Roughness')
        if cloth:
            connect(mixed,'',slab,'FuzzColor')
            for pin,value in [('F0',.022),('FuzzAmount',.12),('FuzzRoughness',.84)]:
                node=M.create_material_expression(mat,u.MaterialExpressionConstant,350,280);node.r=value;connect(node,'',slab,pin)
        else:connect(samples['ORM'],'B',slab,'Metallic')
        if not M.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output')
        errors=M.recompile_material(mat)
        if errors:raise RuntimeError('Material authoring failed '+str(errors))
        save(mat);materials['Gardener_'+family]=mat
    materials['Researcher_Skin']=u.load_asset(SOURCE+'/Materials/M_FRS1_Skin')
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;options.import_as_skeletal=True
    options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
    options.skeleton=skeleton;options.create_physics_asset=False;options.physics_asset=physics
    data=options.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.set_editor_property('import_morph_targets',True)
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    mesh=imported(ROOT/manifest['file'],DEST,'SK_EcologyGardener_V01',options)
    slots=list(mesh.get_editor_property('materials'))
    for slot in slots:
        name=str(slot.get_editor_property('imported_material_slot_name'))
        mat=next((v for k,v in materials.items() if name.startswith(k)),None)
        if not mat:raise RuntimeError('Unassigned gardener material '+name)
        slot.material_interface=mat
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics)
    E.set_metadata_tag(mesh,'Source','FacelessResearcher V05; original body, skeleton, skin weights and 231 corrective morphs')
    E.set_metadata_tag(mesh,'GarmentDesign','Olive work coat; brown waterproof bib apron, straps, belt, reinforced pockets and muddy rubber boots')
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll');save(mesh)
    imported_morphs={x.get_name() for x in mesh.get_editor_property('morph_targets')}
    missing=set(manifest['corrective_morphs'])-imported_morphs
    if missing:raise RuntimeError('Shared researcher curves have no imported morph: '+str(sorted(missing)))
    bp=u.load_asset(DEST+'/BP_EcologyGardener') if E.does_asset_exist(DEST+'/BP_EcologyGardener') else E.duplicate_asset(source.get_path_name(),DEST+'/BP_EcologyGardener')
    if not bp:raise RuntimeError('Gardener blueprint could not be created')
    u.BlueprintEditorLibrary.compile_blueprint(bp);target=u.get_default_object(bp.generated_class())
    target.set_editor_property('visual_mesh',mesh)
    component=target.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh);component.set_editor_property('override_materials',[])
    # Researcher is retained as the animation/FR-curve family; Gardener is the identity.
    tags=list(target.get_editor_property('tags'))
    if not any(str(t)=='EcologyGardener' for t in tags):tags.append(u.Name('EcologyGardener'))
    target.set_editor_property('tags',tags);target.set_editor_property('rank',u.MonsterRank.NORMAL)
    E.set_metadata_tag(bp,'DisplayName','园艺师');E.set_metadata_tag(bp,'IntendedRegion','Ecology nursery and hydroponics')
    E.set_metadata_tag(bp,'AnimationFamily','Exact FacelessResearcher V05 clips and native clothing-curve transition')
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    target=u.get_default_object(bp.generated_class())
    clips={p:target.get_editor_property(p+'_clip').get_path_name() for p in ('idle','walk','attack')}
    for group,names in [('combat',('hit_clip','dizzy_clip')),('knockdown',('fall_clip','get_up_clip','prone_get_up_clip'))]:
        for key in names:
            clip=target.get_editor_property(group).get_editor_property(key)
            clips[group+'.'+key]=clip.get_path_name() if clip else None
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
    report.update(stage='assets_saved',blueprint=bp.get_path_name(),mesh=mesh.get_path_name(),
        source_blueprint=source.get_path_name(),source_mesh=source_mesh.get_path_name(),
        skeleton=skeleton.get_path_name(),physics=physics.get_path_name(),shared_animations=clips,
        authored_morphs=manifest['morph_count'],imported_morphs=len(imported_morphs),triangles=manifest['triangles'],display_name='园艺师',
        combat='Researcher AI, attacks, movement, reactions, humanoid death and replication; normal rank',
        ecology={'EcoNursery':{'gardener':[6,8]},'EcoHydroponics':{'gardener':[6,8],'spiral':4},'EcoBiosphere':{'spiral':2,'root_crown':1}})
    record();print('ECOLOGY_GARDENER_SAVED '+json.dumps({'saved':len(report['saved']),'blueprint':report['blueprint']}),flush=True)
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
