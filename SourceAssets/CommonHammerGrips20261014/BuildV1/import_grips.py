"""Import and save grip geometry, PBR materials and shared final icons."""
import unreal as u,json,runpy,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];D='/Game/Weapons/CommonHammerGrips20261014/BuildV1'
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('PIE active; defer asset mutation')
rows=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts'];ICONS='/Game/ColdSteelData/AttachmentIcons20260913'
MESH_DIR=runpy.run_path(str(P/'catalog.py'))['MESH_DIR']
targets={ICONS+'/grip_'+r['id'] for r in rows}
for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if pkg.get_name().startswith(D+'/') or pkg.get_name() in targets:raise RuntimeError('Unsaved target: '+pkg.get_name())
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
receipt={'complete':False,'game_tested':False,'assets':[],'slot':'grip','stat_modifiers_assigned':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not asset or not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed: '+str(asset))
    receipt['assets'].append(asset.get_path_name());record()
def imp(path,name,dest,options=None):
    asset=u.load_asset(dest+'/'+name)
    if asset:return asset
    task=u.AssetImportTask();task.filename=str(path);task.destination_path=dest;task.destination_name=name;task.automated=True;task.save=False
    if options:task.options=options
    A.import_asset_tasks([task]);asset=u.load_asset(dest+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+name)
    return asset
record();textures={}
for kind in ('Woven','Leather'):
    for channel in ('BaseColor','Normal','ORM'):
        name='T_HammerGrip_'+kind+'_'+channel;texture=imp(P/'Textures'/(name+'.png'),name,D+'/Textures')
        texture.set_editor_property('srgb',channel=='BaseColor')
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
        if channel=='Normal':texture.set_editor_property('flip_green_channel',True)
        texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP if channel=='Normal' else u.TextureGroup.TEXTUREGROUP_WORLD)
        save(texture);textures[(kind,channel)]=texture
materials={'M_SteelWarhammerSurface':u.load_asset('/Game/Weapons/SteelWarhammer20261014/Materials/M_SteelWarhammerSurface')}
if not materials['M_SteelWarhammerSurface']:raise RuntimeError('Factory surface unavailable')
for name,kind,tint in [('M_HammerGripWoven','Woven',(1,1,1)),('M_HammerGripLeather','Leather',(1,1,1)),('M_HammerGripDarkLeather','Leather',(.29,.38,.48))]:
    material=u.load_asset(D+'/Materials/'+name)
    if not material:
        material=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew());material.set_editor_property('use_material_attributes',False)
        material.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE);material.set_editor_property('used_with_skeletal_mesh',False)
        surface=E.create_material_expression(material,u.MaterialExpressionSubstrateShadingModels,500,0)
        surface.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        nodes={}
        for channel in ('BaseColor','Normal','ORM'):
            node=E.create_material_expression(material,u.MaterialExpressionTextureSample,-600,len(nodes)*220);node.set_editor_property('texture',textures[(kind,channel)])
            node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR);nodes[channel]=node
        def wire(node,output,pin,prop):
            if not E.connect_material_expressions(node,output,surface,pin):raise RuntimeError('Material input '+pin)
            E.connect_material_property(node,output,prop)
        mult=E.create_material_expression(material,u.MaterialExpressionMultiply,-120,0)
        factor=E.create_material_expression(material,u.MaterialExpressionConstant3Vector,-400,-160);factor.set_editor_property('constant',u.LinearColor(*tint,1))
        E.connect_material_expressions(nodes['BaseColor'],'RGB',mult,'A');E.connect_material_expressions(factor,'',mult,'B')
        wire(mult,'','BaseColor',u.MaterialProperty.MP_BASE_COLOR)
        wire(nodes['ORM'],'G','Roughness',u.MaterialProperty.MP_ROUGHNESS)
        wire(nodes['ORM'],'B','Metallic',u.MaterialProperty.MP_METALLIC)
        wire(nodes['Normal'],'RGB','Normal',u.MaterialProperty.MP_NORMAL)
        E.connect_material_property(nodes['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
        if not E.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output missing')
        E.layout_material_expressions(material);errors=list(E.recompile_material(material))
        if errors:raise RuntimeError('Material compile failed: '+str(errors))
    save(material);materials[name]=material
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
for row in rows:
    mesh=imp(P/'Export'/(row['mesh']+'.fbx'),row['mesh'],MESH_DIR,opt)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=str(slot.material_slot_name)
        if name not in materials:raise RuntimeError('Unknown material slot: '+name)
        mesh.set_material(i,materials[name])
    save(mesh)
    key='grip_'+row['id'];source=P/'Icons'/(row['id']+'.png');texture=imp(source,key,ICONS)
    texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('srgb',True);texture.set_editor_property('never_stream',True);texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    save(texture);shutil.copy2(source,ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(key+'.png'))
before=P/'Before';before.mkdir(exist_ok=True)
for name in ('warhammer-modules.json','warhammer-gunsmith.json','common-hammer-grips.json'):
    src=ROOT/'Content/ColdSteelData'/name
    if src.exists() and not (before/name).exists():shutil.copy2(src,before/name)
runpy.run_path(str(P/'register_grips.py'),run_name='__main__')
receipt['complete']=True;record();print('COMMON_HAMMER_GRIPS_SAVED '+str(len(receipt['assets'])))
