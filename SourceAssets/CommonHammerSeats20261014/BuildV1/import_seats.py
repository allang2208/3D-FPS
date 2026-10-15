"""Save the seat assets, then publish the shared appearance options."""
import unreal as u,json,runpy,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];D='/Game/Weapons/CommonHammerSeats20261014/BuildV1'
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('PIE is active; preserve play and defer import')
rows=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts']
ICONS='/Game/ColdSteelData/AttachmentIcons20260913'
targets={ICONS+'/head_mount_'+r['id'] for r in rows}
for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if pkg.get_name().startswith(D+'/') or pkg.get_name() in targets:raise RuntimeError('Unsaved target: '+pkg.get_name())
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
receipt={'complete':False,'game_tested':False,'assets':[],'slot':'head_mount','stat_modifiers_assigned':False}
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
record()
materials={name:u.load_asset(path) for name,path in {
    'M_SteelWarhammerSurface':'/Game/Weapons/SteelWarhammer20261014/Materials/M_SteelWarhammerSurface',
    'M_CommonHammerHeadSteel':'/Game/Weapons/CommonHammerHeads20261014/Materials/M_CommonHammerHeadSteel'}.items()}
textures={key:u.load_asset('/Game/Weapons/CommonHammerHeads20261014/Textures/T_CommonHammerSteel_'+key) for key in ('BaseColor','MetallicRoughness','Normal')}
if any(not x for x in list(materials.values())+list(textures.values())):raise RuntimeError('Required shared steel asset unavailable')

for name,is_pad in [('M_CommonHammerSeatDarkSteel',False),('M_CommonHammerSeatDamping',True)]:
    material=u.load_asset(D+'/Materials/'+name)
    if not material:
        material=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
        material.set_editor_property('use_material_attributes',False);material.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
        material.set_editor_property('used_with_skeletal_mesh',False)
        surface=E.create_material_expression(material,u.MaterialExpressionSubstrateShadingModels,600,0)
        surface.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        uv=E.create_material_expression(material,u.MaterialExpressionTextureCoordinate,-800,0);uv.set_editor_property('coordinate_index',1)
        nodes={}
        for key,texture in textures.items():
            node=E.create_material_expression(material,u.MaterialExpressionTextureSample,-600,len(nodes)*210);node.set_editor_property('texture',texture)
            node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if key=='MetallicRoughness' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            E.connect_material_expressions(uv,'',node,'UVs');nodes[key]=node
        def constant(value):
            node=E.create_material_expression(material,u.MaterialExpressionConstant,-250,0);node.set_editor_property('r',value);return node
        def wire(node,channel,pin,prop):
            if not E.connect_material_expressions(node,channel,surface,pin):raise RuntimeError('Material input: '+pin)
            E.connect_material_property(node,channel,prop)
        if is_pad:
            wire(constant(.025),'','BaseColor',u.MaterialProperty.MP_BASE_COLOR)
            wire(constant(.74),'','Roughness',u.MaterialProperty.MP_ROUGHNESS)
            wire(constant(0),'','Metallic',u.MaterialProperty.MP_METALLIC)
            flat=E.create_material_expression(material,u.MaterialExpressionConstant3Vector,-250,420);flat.set_editor_property('constant',u.LinearColor(0,0,1,1))
            blend=E.create_material_expression(material,u.MaterialExpressionLinearInterpolate,0,400);blend.set_editor_property('const_alpha',.25)
            E.connect_material_expressions(flat,'',blend,'A');E.connect_material_expressions(nodes['Normal'],'RGB',blend,'B')
            normal=E.create_material_expression(material,u.MaterialExpressionNormalize,250,400);E.connect_material_expressions(blend,'',normal,'VectorInput')
            wire(normal,'','Normal',u.MaterialProperty.MP_NORMAL)
        else:
            multiply=E.create_material_expression(material,u.MaterialExpressionMultiply,-100,0);multiply.set_editor_property('const_b',.38)
            E.connect_material_expressions(nodes['BaseColor'],'RGB',multiply,'A')
            wire(multiply,'','BaseColor',u.MaterialProperty.MP_BASE_COLOR)
            wire(nodes['MetallicRoughness'],'G','Roughness',u.MaterialProperty.MP_ROUGHNESS)
            wire(nodes['MetallicRoughness'],'B','Metallic',u.MaterialProperty.MP_METALLIC)
            wire(nodes['Normal'],'RGB','Normal',u.MaterialProperty.MP_NORMAL)
        if not E.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output missing')
        E.layout_material_expressions(material)
        errors=list(E.recompile_material(material))
        if errors:raise RuntimeError('Material compile failed: '+str(errors))
    save(material);materials[name]=material

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
for row in rows:
    mesh=imp(P/'Export'/(row['mesh']+'.fbx'),row['mesh'],D,opt)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=str(slot.material_slot_name)
        match=next((mat for key,mat in materials.items() if name==key),None)
        if not match:raise RuntimeError('Unknown material slot: '+name)
        mesh.set_material(i,match)
    save(mesh)
    key='head_mount_'+row['id'];source=P/'Icons'/(row['id']+'.png')
    texture=imp(source,key,ICONS)
    texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('srgb',True);texture.set_editor_property('never_stream',True)
    texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(texture)
    shutil.copy2(source,ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(key+'.png'))
before=P/'Before';before.mkdir(exist_ok=True)
for name in ('warhammer-modules.json','warhammer-gunsmith.json','common-hammer-seats.json'):
    src=ROOT/'Content/ColdSteelData'/name
    if src.exists() and not (before/name).exists():shutil.copy2(src,before/name)
runpy.run_path(str(P/'register_seats.py'),run_name='__main__')
receipt['complete']=True;record();print('COMMON_HAMMER_SEATS_SAVED '+str(len(receipt['assets'])))
