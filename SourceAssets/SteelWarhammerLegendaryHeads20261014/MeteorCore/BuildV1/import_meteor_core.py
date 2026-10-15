"""Save legendary head PBR, animated lava material, mesh and production icon."""
import unreal as u,json,runpy,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
catalog=runpy.run_path(str(P/'catalog.py'));D=catalog['MESH_DIR'];ICONS='/Game/ColdSteelData/AttachmentIcons20260913'
ICON='ue_steel_warhammer_hammer_heads_meteor_core'
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('PIE active; defer asset batch')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name().startswith(D+'/') or package.get_name()==ICONS+'/'+ICON:
        raise RuntimeError('Unsaved target: '+package.get_name())
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
receipt={'complete':False,'tested':False,'assets':[],'revision':'MeteorCoreV1','balance_assigned':False}
if (P/'import_receipt.json').exists():
    receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
saved=set(receipt['assets'])
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name());record()
def imp(source,name,dest,options=None):
    asset=u.load_asset(dest+'/'+name)
    if asset:return asset
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=dest;task.destination_name=name;task.automated=True;task.save=False
    if options:task.options=options
    A.import_asset_tasks([task]);asset=u.load_asset(dest+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+name)
    return asset
record()
textures={}
for prefix in ('T_MeteorBronze','T_MeteorRuneBand','T_MeteorCore'):
    textures[prefix]={}
    for channel in ('BaseColor','Normal','ORM')+(('Heat',) if prefix=='T_MeteorCore' else ()):
        name=prefix+'_'+channel;texture=imp(P/'Textures'/(name+'.png'),name,D+'/Textures')
        if texture.get_path_name() in saved:
            textures[prefix][channel]=texture;continue
        texture.set_editor_property('srgb',channel=='BaseColor')
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if channel=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP if channel=='Normal' else u.TextureGroup.TEXTUREGROUP_WORLD)
        if channel=='Normal':texture.set_editor_property('flip_green_channel',True)
        save(texture);textures[prefix][channel]=texture
materials={name:u.load_asset(path) for name,path in catalog['MATERIALS'].items() if not path.startswith(D+'/')}
if any(not m for m in materials.values()):raise RuntimeError('Current host steel materials unavailable')
for name,prefix in (('M_MeteorBronze','T_MeteorBronze'),('M_MeteorRuneBand','T_MeteorRuneBand'),('M_MeteorLavaCore','T_MeteorCore')):
    material=u.load_asset(D+'/Materials/'+name)
    if material and material.get_path_name() in saved:
        materials[name]=material;continue
    if not material:material=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
    if not material:raise RuntimeError('Material creation failed: '+name)
    E.delete_all_material_expressions(material)
    material.set_editor_property('use_material_attributes',False)
    material.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('two_sided',False)
    material.set_editor_property('used_with_skeletal_mesh',False)
    surface=E.create_material_expression(material,u.MaterialExpressionSubstrateShadingModels,650,0)
    surface.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    def node(cls,x,y,**properties):
        result=E.create_material_expression(material,cls,x,y)
        for key,value in properties.items():result.set_editor_property(key,value)
        return result
    def connect(source,channel,target,pin):
        if not E.connect_material_expressions(source,channel,target,pin):raise RuntimeError('Material input '+name+': '+pin)
    def wire(source,channel,pin,prop):
        connect(source,channel,surface,pin);E.connect_material_property(source,channel,prop)
    uv=node(u.MaterialExpressionTextureCoordinate,-1200,0,coordinate_index=0)
    samples={}
    for index,(channel,texture) in enumerate(textures[prefix].items()):
        sample=node(u.MaterialExpressionTextureSample,-900,index*220,texture=texture,
          sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        connect(uv,'',sample,'UVs');samples[channel]=sample
    wire(samples['BaseColor'],'RGB','BaseColor',u.MaterialProperty.MP_BASE_COLOR)
    wire(samples['Normal'],'RGB','Normal',u.MaterialProperty.MP_NORMAL)
    wire(samples['ORM'],'G','Roughness',u.MaterialProperty.MP_ROUGHNESS)
    wire(samples['ORM'],'B','Metallic',u.MaterialProperty.MP_METALLIC)
    E.connect_material_property(samples['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    if prefix=='T_MeteorCore':
        time=node(u.MaterialExpressionTime,-900,920)
        parameters={
          'EmissionStrength':node(u.MaterialExpressionScalarParameter,-700,940,parameter_name='EmissionStrength',default_value=5.5),
          'PulseSpeed':node(u.MaterialExpressionScalarParameter,-700,1100,parameter_name='PulseSpeed',default_value=.85),
          'FlowSpeed':node(u.MaterialExpressionScalarParameter,-700,1260,parameter_name='FlowSpeed',default_value=.70),
          'EmberColor':node(u.MaterialExpressionVectorParameter,-700,1420,parameter_name='EmberColor',default_value=u.LinearColor(1,.035,.001,1)),
          'HotColor':node(u.MaterialExpressionVectorParameter,-700,1580,parameter_name='HotColor',default_value=u.LinearColor(1,.35,.025,1))}
        emission=node(u.MaterialExpressionCustom,120,600,code=(P/'lava_emission.hlsl').read_text(encoding='utf-8'),output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
        inputs={'Heat':(samples['Heat'],'RGB'),'Time':(time,''),'UV':(uv,'')}
        inputs.update({k:(v,'') for k,v in parameters.items()})
        pins=[]
        for key in inputs:
            pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
        emission.set_editor_property('inputs',pins)
        for key,(source,channel) in inputs.items():connect(source,channel,emission,key)
        wire(emission,'','Emissive Color',u.MaterialProperty.MP_EMISSIVE_COLOR)
    if not E.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output failed')
    E.layout_material_expressions(material)
    errors=list(E.recompile_material(material))
    if errors:raise RuntimeError('Material compilation failed '+name+': '+str(errors))
    save(material);materials[name]=material
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
row=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts'][0]
mesh=imp(P/'Export'/(row['mesh']+'.fbx'),row['mesh'],D,opt)
for index,slot in enumerate(mesh.get_editor_property('static_materials')):
    name=str(slot.material_slot_name)
    if name not in materials:raise RuntimeError('Unknown material '+name)
    mesh.set_material(index,materials[name])
save(mesh)
source=P/'Icons/meteor_core.png';texture=imp(source,ICON,ICONS)
texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property('srgb',True);texture.set_editor_property('never_stream',True)
texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(texture)
shutil.copy2(source,ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(ICON+'.png'))
receipt.update(complete=True,lava_effect={'emission_strength':5.5,'pulse_speed':.85,'flow_speed':.70,'opaque_core':True,'cpu_tick':False})
record();runpy.run_path(str(P/'register_meteor_core.py'),run_name='__main__')
print('METEOR_CORE_SAVED '+json.dumps(receipt),flush=True)
