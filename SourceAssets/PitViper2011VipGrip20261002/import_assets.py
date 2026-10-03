"""Save the fitted VIP surface, WS metal, wetness bindings and UI icon."""
import json,re
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1];D='/Game/Weapons/PitViper2011/VipGrip20261002'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
auth=json.loads((O/'authoring.json').read_text(encoding='utf8'))
WET='/Game/Weapons/PistolGripSurface20260927/DA_PistolGripSurfaceWetMaterials'
receipt={'saved':[],'runtime_tested':False,'acceptance_rendered':False}
targets={auth['mesh'],*auth['materials'].values(),WET,D+'/Icons/T_ue_pit_viper2011_reargrip_pit_viper_vip_scales'}
targets.update(D+'/Textures/'+Path(f).stem for f in auth['textures'].values())
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(P/'Content').resolve():
    raise RuntimeError('Wrong production project')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
surfacepath=auth['materials']['surface']
partial=u.load_asset(surfacepath) or u.find_object(None,surfacepath+'.'+Path(surfacepath).name)
if partial and globals().get('__VIP_RESUME_OWN_MATERIAL__',False):
    # Resume only the material made by this batch after a Python authoring error.
    dirty.discard(auth['materials']['surface'])
if dirty&targets:raise RuntimeError('Preserve unsaved VIP grip packages: '+str(sorted(dirty&targets)))

def record():(O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing production asset '+path)
    return obj
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed '+obj.get_path_name())
    if obj.get_path_name() not in receipt['saved']:receipt['saved'].append(obj.get_path_name())
    record();return obj
def asset(name,folder,cls,factory):
    result=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,cls,factory)
    if not result:raise RuntimeError('Cannot create '+name)
    return result
def import_file(file,folder,name,options=None):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    if options:task.options=options;task.factory=u.FbxFactory()
    A.import_asset_tasks([task]);return load(folder+'/'+name)

textures={}
for kind,file in auth['textures'].items():
    tex=import_file(file,D+'/Textures',Path(file).stem)
    tex.srgb=kind=='BaseColor'
    tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS if kind in ('ORM','Height') else u.TextureCompressionSettings.TC_DEFAULT
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON
    if kind=='Normal':tex.set_editor_property('flip_green_channel',True)
    save(tex);textures[kind]=tex

path=auth['materials']['surface'];mat=partial
if not mat or E.get_metadata_tag(mat,'VipSurfaceGraphComplete')!='1':
    if not mat:mat=A.create_asset(Path(path).name,str(Path(path).parent).replace('\\','/'),u.Material,u.MaterialFactoryNew())
    if not mat:raise RuntimeError('Cannot create VIP surface material')
    E.set_metadata_tag(mat,'VipSurfaceAuthorJob',str(O))
    def node(cls):return L.create_material_expression(mat,cls)
    def wire(src,pin,dst,input):
        if not L.connect_material_expressions(src,pin,dst,input):raise RuntimeError('Material connection failed '+input)
    def prop(src,pin,target):
        if not L.connect_material_property(src,pin,target):raise RuntimeError('Material output connection failed '+str(target))
    samples={}
    for kind in ('BaseColor','Normal','ORM'):
        n=node(u.MaterialExpressionTextureSample);n.texture=textures[kind]
        n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR
        samples[kind]=n
    wet=node(u.MaterialExpressionScalarParameter)
    wet.set_editor_property('parameter_name','WeaponWetness');wet.set_editor_property('default_value',0)
    dark=node(u.MaterialExpressionConstant);dark.r=.90
    mul=node(u.MaterialExpressionMultiply);wire(samples['BaseColor'],'RGB',mul,'A');wire(dark,'',mul,'B')
    color=node(u.MaterialExpressionLinearInterpolate)
    wire(samples['BaseColor'],'RGB',color,'A');wire(mul,'',color,'B');wire(wet,'',color,'Alpha')
    prop(color,'',u.MaterialProperty.MP_BASE_COLOR)
    # Existing weather parameter, material relief remains unchanged when wet.
    wetrough=node(u.MaterialExpressionConstant);wetrough.r=.35
    rough=node(u.MaterialExpressionLinearInterpolate)
    wire(samples['ORM'],'G',rough,'A');wire(wetrough,'',rough,'B');wire(wet,'',rough,'Alpha')
    prop(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    prop(samples['Normal'],'',u.MaterialProperty.MP_NORMAL)
    prop(samples['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    prop(samples['ORM'],'B',u.MaterialProperty.MP_METALLIC)
    mat.set_editor_property('used_with_skeletal_mesh',False)
    L.recompile_material(mat)
    E.set_metadata_tag(mat,'VipSurfaceGraphComplete','1')
E.set_metadata_tag(mat,'SourceAttribution',auth['provenance']);save(mat)

goldpath=auth['materials']['metal']
gold=asset(Path(goldpath).name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
parent=load('/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanPolishedSteel')
L.set_material_instance_parent(gold,parent)
for name,value in {'SourceColorWeight':0.,'SourceRoughnessWeight':0.,'MaskUVChannel':1.,'Roughness':.46,'Metallic':1.,'EdgeWear':0.}.items():
    L.set_material_instance_scalar_parameter_value(gold,name,value)
L.set_material_instance_vector_parameter_value(gold,'FinishColor',u.LinearColor(.19,.145,.090,1))
L.update_material_instance(gold);save(gold)
receipt['materials']={'surface':mat.get_path_name(),'metal':gold.get_path_name(),'metal_parent':parent.get_path_name()};record()

flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
    opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
    opt.static_mesh_import_data.generate_lightmap_u_vs=False
    opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh=import_file(auth['fbx'],D,auth['name'],opt)
    slots=list(mesh.static_materials)
    for i,slot in enumerate(slots):
        label=re.sub(r'[._]\d{3}$','',str(slot.material_slot_name))
        slot.material_interface=gold if 'Champagne' in label else mat;slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    if subsystem:
        settings=subsystem.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True
        subsystem.set_lod_build_settings(mesh,0,settings)
    E.set_metadata_tag(mesh,'SourceAttribution',auth['provenance'])
    E.set_metadata_tag(mesh,'GripSurfaceFrame',auth['frame']);save(mesh)
    receipt['mesh']={'asset':mesh.get_path_name(),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},'source':auth['fbx']};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
library=load(WET);mapping=dict(library.get_editor_property('wet_materials'))
for material in (mat,gold):mapping[material.get_path_name()]=material
library.set_editor_property('wet_materials',mapping);save(library)
receipt['wetness_library']=WET
key='ue_pit_viper2011_reargrip_pit_viper_vip_scales'
icon=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'/(key+'.png')
tex=import_file(icon,D+'/Icons','T_'+key);tex.srgb=True
tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI
tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;tex.never_stream=True;save(tex)
receipt['icon']={'png':str(icon),'asset':tex.get_path_name()}
script=O/'publish_catalog.py'
exec(compile(script.read_text(encoding='utf8'),str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
receipt.update(status='imported_and_saved',catalog_published=True);record()
print('VIP_VIPER_GRIP_IMPORTED_AND_SAVED',flush=True)
finish=O.parent/'PitViper2011SurfaceRefine20261003/restore_saved_finish.py'
if finish.exists():
    import runpy
    runpy.run_path(str(finish),run_name='__main__')
# Reauthoring this legacy entry also refreshes the current private long-skin
# maps and mesh, retaining the quiet finish applied immediately above.
longitudinal=O.parent/'PitViper2011ViperLongitudinalGrip20261003/import_assets.py'
if auth.get('revision')=='longitudinal_grip_20261003' and longitudinal.exists():
    import runpy
    runpy.run_path(str(longitudinal),run_name='__main__')
