"""Save the weighted grip and replacement surface; split factory grip sections."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;Source=O.parent;P=Source.parents[1]
D='/Game/Weapons/RSH12/HeavyGrip20261005';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Unexpected project')
headless='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not headless and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE prevents asset import')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith((D,'/Game/Weapons/RSH12/Native71520261003')) for p in dirty):raise RuntimeError('Target RSH assets have unsaved changes')
auth=json.loads((Source/'authoring.json').read_text(encoding='utf8'))
outfit_updates={}
receipt=json.loads((O/'import_receipt.json').read_text()) if (O/'import_receipt.json').exists() else {'complete':False,'saved':[],'host_sections':{},'runtime_tested':False}
receipt['complete']=False
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing source '+path)
    return obj
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    if obj.get_path_name() not in receipt['saved']:receipt['saved'].append(obj.get_path_name())
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
def backup(package):
    disk=P/'Content'/(package.removeprefix('/Game/')+'.uasset');out=O/'BeforeAssets'/disk.relative_to(P/'Content')
    if disk.exists() and not out.exists():out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,out)
def imported(file,name,folder,options=None,factory=None):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name;task.automated=True
    task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=options
    if factory:task.factory=factory
    A.import_asset_tasks([task]);return load(folder+'/'+name)
def texture(file,kind):
    tex=imported(file,Path(file).stem,D+'/Textures');tex.srgb=kind=='color';tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    tex.compression_settings={'color':u.TextureCompressionSettings.TC_BC7,'orm':u.TextureCompressionSettings.TC_MASKS,'normal':u.TextureCompressionSettings.TC_NORMALMAP}[kind]
    if kind=='normal':tex.flip_green_channel=False
    save(tex);return tex
def node(mat,cls,**values):
    n=L.create_material_expression(mat,cls)
    for key,value in values.items():n.set_editor_property(key,value)
    return n
def wire(src,pin,dst,input):
    if not L.connect_material_expressions(src,pin,dst,input):raise RuntimeError('Material pin '+input)
def output(src,pin,prop):
    if not L.connect_material_property(src,pin,prop):raise RuntimeError('Material output')
materials={}
def material(label,maps=None,color=(.065,.069,.075),rough=.38,metal=1):
    name='M_RSH12_HeavyGrip_'+label;path=D+'/Materials/'+name
    m=u.load_asset(path)
    if m:return m
    m=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
    for flag in ('used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):m.set_editor_property(flag,False)
    if maps:
        bc=texture(Source/maps['base_color'],'color');orm=texture(Source/maps['orm'],'orm');normal=texture(Source/maps['normal_dx'],'normal')
        c=node(m,u.MaterialExpressionTextureSample,texture=bc,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        r=node(m,u.MaterialExpressionTextureSample,texture=orm,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        n=node(m,u.MaterialExpressionTextureSample,texture=normal,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        rough_pin='G';color_pin='RGB';output(r,'B',u.MaterialProperty.MP_METALLIC);output(r,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION);output(n,'RGB',u.MaterialProperty.MP_NORMAL)
    else:
        c=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*color,1));r=node(m,u.MaterialExpressionConstant,r=rough)
        rough_pin=color_pin='';output(node(m,u.MaterialExpressionConstant,r=metal),'',u.MaterialProperty.MP_METALLIC)
    wet=node(m,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
    dark=node(m,u.MaterialExpressionLinearInterpolate,const_a=1.,const_b=.92);wire(wet,'',dark,'Alpha')
    colorout=node(m,u.MaterialExpressionMultiply);wire(c,color_pin,colorout,'A');wire(dark,'',colorout,'B');output(colorout,'',u.MaterialProperty.MP_BASE_COLOR)
    roughout=node(m,u.MaterialExpressionLinearInterpolate,const_b=.16 if metal else .28);wire(r,rough_pin,roughout,'A');wire(wet,'',roughout,'Alpha');output(roughout,'',u.MaterialProperty.MP_ROUGHNESS)
    L.recompile_material(m);save(m);return m
materials['RSH12HeavyGrip_RubberContactShell']=material('Rubber',auth['textures']['RubberPanel'],metal=0)
materials['RSH12HeavyGrip_RubberPanel']=materials['RSH12HeavyGrip_RubberContactShell']
materials['RSH12HeavyGrip_GraphiteHeel']=material('GraphiteHeel',auth['textures']['GraphiteHeel'])
materials['RSH12HeavyGrip_EdgeAndSpine']=material('EdgeAndSpine')
materials['RSH12HeavyGrip_Recess']=material('Recess',color=(.004,.005,.006),rough=.85,metal=0)
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for name,file in [('SM_RSH12_HeavyGrip',O/'SM_RSH12_HeavyGrip.fbx'),('SM_RSH12_HeavyGrip_Surface',Path(auth['surface_fbx']))]:
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        mesh=imported(file,name,D+'/Meshes',opt,u.FbxFactory());u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
        slots=list(mesh.static_materials)
        for i,s in enumerate(slots):
            label=str(s.material_slot_name).split('.')[0];label=next((k for k in materials if label.startswith(k)),label)
            s.material_interface=materials[label];slots[i]=s
        mesh.set_editor_property('static_materials',slots)
        editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
        settings=editor.get_lod_build_settings(mesh,0);settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True;settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
        editor.set_lod_build_settings(mesh,0,settings)
        if not u.ASH12AttachmentAssetTools.finish_and_validate_build(mesh):raise RuntimeError('Static mesh build failed '+name)
        E.set_metadata_tag(mesh,'SourceAttribution',auth['provenance']);E.set_metadata_tag(mesh,'GripInterface','Native component reference; inverse WPN_root; no added offset; UV0 physical rubber')
        save(mesh)
    metal=load('/Game/Weapons/RSH12/Materials/MI_RSH12_SourcePBR');bare=load('/Game/Characters/ModularOutfit20260924/BarePalmV7/Materials/MI_BareNative_Default')
    for side,spec in json.loads((O/'host_sections.json').read_text()).items():
        folder='/Game/Weapons/RSH12/Native71520261003/'+side;path=folder+'/'+spec['name'];backup(path)
        original=load(path);old_materials={str(s.material_slot_name):s.material_interface for s in original.materials}
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
        opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=original.skeleton
        opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False);opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False);opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        mesh=imported(spec['fbx'],spec['name'],folder,opt,u.FbxFactory());slots=list(mesh.materials)
        for i,s in enumerate(slots):
            label=str(s.material_slot_name);s.material_interface=old_materials.get(label,bare if 'Manny' in label else metal);slots[i]=s
        mesh.set_editor_property('materials',slots)
        E.set_metadata_tag(mesh,'RSHFactoryGripSection','M_RSH12_FactoryGrip; original 9_l faces only; existing geometry, UV, bones and weights retained')
        save(mesh);receipt['host_sections'][side]={'mesh':mesh.get_path_name(),'factory_faces':spec['factory_grip_faces'],'materials':[str(s.material_slot_name) for s in slots]}
        outfit_updates[mesh.get_path_name()]=[i for i,s in enumerate(slots) if 'Manny' in str(s.material_slot_name)]
    wetpath='/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials';backup(wetpath);wet=load(wetpath);mapping=dict(wet.get_editor_property('wet_materials'))
    for m in materials.values():mapping[m.get_path_name()]=m
    wet.set_editor_property('wet_materials',mapping);save(wet)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
config=P/'Content/ColdSteelData/modular_outfits.json';raw=config.read_bytes();text=raw.decode('utf-8-sig');decoder=json.JSONDecoder()
for key,indices in outfit_updates.items():
    keypos=text.index(json.dumps(key));start=text.index(':',keypos)+1
    while text[start].isspace():start+=1
    profile,end=decoder.raw_decode(text,start)
    if profile.get('hide_source_materials')==indices:continue
    profile['hide_source_materials']=indices
    indent=''.join(c for c in text[:keypos].rsplit('\n',1)[-1] if c in ' \t')
    text=text[:start]+json.dumps(profile,ensure_ascii=False,indent=2).replace('\n','\n'+indent)+text[end:]
if text!=raw.decode('utf-8-sig'):
    before=O/'Before/modular_outfits.json';before.parent.mkdir(exist_ok=True)
    if not before.exists():before.write_bytes(raw)
    if config.read_bytes()!=raw:raise RuntimeError('Concurrent outfit profile change')
    config.write_bytes(text.encode('utf8'))
receipt['complete']=True;(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8');print('RSH_HEAVY_GRIP_ASSETS_SAVED',flush=True)
