"""Import the authored bow into a staging project at its final /Game package paths."""
from pathlib import Path
import json, os
import unreal as u

P=Path(__file__).resolve().parent
batch=Path(os.environ['FRONTIER_BOW_BATCH'])
dest='/Game/Weapons/FrontierCompoundBow'
tools=u.AssetToolsHelpers.get_asset_tools()
edit=u.MaterialEditingLibrary
saved={}
def save(obj):
    if not obj or not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):
        raise RuntimeError('Could not save '+str(obj))
    saved[obj.get_name()]=obj.get_path_name()
    return obj
def ingest(src,folder,name,options=None):
    task=u.AssetImportTask();task.filename=str(src);task.destination_path=folder
    task.destination_name=name;task.automated=True;task.replace_existing=True
    task.save=False
    if options:task.options=options
    tools.import_asset_tasks([task])
    obj=u.load_asset(folder+'/'+name)
    if not obj:raise RuntimeError('No imported object '+name)
    return obj
tex={}
for kind in ('BaseColor','Normal','MetalRough'):
    name='T_Frontier_'+kind
    t=ingest(P/'Textures'/(name+'.png'),dest+'/Textures',name)
    t.srgb=kind=='BaseColor';t.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    if kind=='Normal':
        t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP
        t.set_editor_property('flip_green_channel',True)
    if kind=='MetalRough':t.compression_settings=u.TextureCompressionSettings.TC_MASKS
    tex[kind]=save(t)
def material(name):
    m=u.load_asset(dest+'/'+name) if u.EditorAssetLibrary.does_asset_exist(dest+'/'+name) else tools.create_asset(name,dest,u.Material,u.MaterialFactoryNew())
    edit.delete_all_material_expressions(m)
    m.set_editor_property('used_with_skeletal_mesh',True)
    return m
m=material('M_Frontier_Surface')
for kind,pins,mode in [('BaseColor',[('RGB','MP_BASE_COLOR')],'SAMPLERTYPE_COLOR'),
        ('Normal',[('RGB','MP_NORMAL')],'SAMPLERTYPE_NORMAL'),
        ('MetalRough',[('G','MP_ROUGHNESS'),('B','MP_METALLIC')],'SAMPLERTYPE_MASKS')]:
    node=edit.create_material_expression(m,u.MaterialExpressionTextureSample)
    node.texture=tex[kind];node.sampler_type=getattr(u.MaterialSamplerType,mode)
    for pin,prop in pins:edit.connect_material_property(node,pin,getattr(u.MaterialProperty,prop))
edit.recompile_material(m);save(m)
cord=material('M_Frontier_Cord')
color=edit.create_material_expression(cord,u.MaterialExpressionConstant3Vector)
color.constant=u.LinearColor(.045,.053,.051,1.)
edit.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
rough=edit.create_material_expression(cord,u.MaterialExpressionConstant);rough.r=.76
edit.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
edit.recompile_material(cord);save(cord)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for name in ('SK_Frontier_Assembly','SM_Frontier_Grip','SM_Frontier_Rest','SM_Frontier_Stabilizer'):
    sk=name.startswith('SK_')
    o=u.FbxImportUI();o.automated_import_should_detect_type=False
    o.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if sk else u.FBXImportType.FBXIT_STATIC_MESH
    o.import_as_skeletal=sk;o.import_mesh=True;o.import_animations=False;o.import_materials=False;o.import_textures=False;o.create_physics_asset=False
    data=o.skeletal_mesh_import_data if sk else o.static_mesh_import_data
    if not sk:data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    asset=ingest(P/'Export'/(name+'.fbx'),dest,name,o)
    slots=list(asset.materials if sk else asset.static_materials)
    for slot in slots:slot.material_interface=cord if 'Cord' in str(slot.material_slot_name) else m
    if sk:
        asset.materials=slots;save(asset.skeleton)
        pose=asset.skeleton.get_reference_pose()
        bones={str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)}
        expected={prefix+side+suffix for prefix in ('','draw_') for side in ('upper','lower') for suffix in ('_01','_02','_cam','_tip')}
        expected.update({'compound_draw_end','upper_cable0','lower_cable0','upper_cable1','lower_cable1'})
        if expected-bones:raise RuntimeError('FBX lost rig controls: '+str(sorted(expected-bones)))
        anchors={}
        for n in ('upper_tip','lower_tip','compound_draw_end'):
            v=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD).translation
            anchors[n]=[v.x,v.y,v.z]
    else:asset.static_materials=slots
    save(asset)
icon=ingest(P/'Export/bow_frontier_compound.png','/Game/ColdSteelData/Icons','bow_frontier_compound')
icon.lod_group=u.TextureGroup.TEXTUREGROUP_UI;icon.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
icon.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;icon.srgb=True;save(icon)
(batch/'import.json').write_text(json.dumps(dict(packages=saved,anchors=anchors,bones=sorted(bones)),indent=2),encoding='utf8')
