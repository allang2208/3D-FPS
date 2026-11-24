"""Import the authored variants and save their material, textures, meshes and shared string skeleton."""
import json, os
from pathlib import Path
import unreal as u

src=Path(__file__).resolve().parent
batch=Path(os.environ['FRONTIER_MOD_BATCH'])
dest='/Game/Weapons/FrontierCompoundBow/CommonModsR1'
data=json.loads((src/'parts.json').read_text(encoding='utf8'))
tools=u.AssetToolsHelpers.get_asset_tools()
edit=u.MaterialEditingLibrary
saved={}
def save(obj):
    if not obj or not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):
        raise RuntimeError('Failed to save '+str(obj))
    saved[obj.get_name()]=obj.get_path_name()
def ingest(file,folder,options=None):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=file.stem
    task.automated=True;task.replace_existing=True
    if options:task.options=options
    tools.import_asset_tasks([task])
    obj=u.load_asset(folder+'/'+file.stem)
    if not obj:raise RuntimeError('Missing import '+str(file))
    return obj
textures={}
for key in ('Color','Normal','ORM'):
    t=ingest(src/'Textures'/f'T_FrontierMods_{key}.png',dest+'/Textures')
    t.srgb=key=='Color'
    if key=='Normal':t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP
    if key=='ORM':t.compression_settings=u.TextureCompressionSettings.TC_MASKS
    save(t);textures[key]=t
def shared_material():
    name='M_FrontierMods_Surface'
    mat=u.load_asset(dest+'/'+name) if u.EditorAssetLibrary.does_asset_exist(dest+'/'+name) else tools.create_asset(name,dest,u.Material,u.MaterialFactoryNew())
    edit.delete_all_material_expressions(mat)
    mat.set_editor_property('used_with_skeletal_mesh',True)
    for idx,(k,pins) in enumerate([('Color',{'RGB':u.MaterialProperty.MP_BASE_COLOR}),
                                   ('Normal',{'RGB':u.MaterialProperty.MP_NORMAL}),
                                   ('ORM',{'R':u.MaterialProperty.MP_AMBIENT_OCCLUSION,'G':u.MaterialProperty.MP_ROUGHNESS,'B':u.MaterialProperty.MP_METALLIC})]):
        node=edit.create_material_expression(mat,u.MaterialExpressionTextureSample,-380,idx*210)
        node.texture=textures[k]
        node.sampler_type={'Color':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'ORM':u.MaterialSamplerType.SAMPLERTYPE_MASKS}[k]
        for channel,pin in pins.items():
            if not edit.connect_material_property(node,channel,pin):raise RuntimeError('Texture connection '+k)
    edit.recompile_material(mat);save(mat);return mat
materials={'M_FrontierMods_Surface':shared_material(),'M_Frontier_Surface':u.load_asset('/Game/Weapons/FrontierCompoundBow/M_Frontier_Surface')}
for power in (2,4):
    name=f'M_BowOptic_Glass{power}x'
    materials[name]=u.load_asset('/Game/Weapons/DarkBow20260925/SingleLensOptics20260927/'+name)
static=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
skins=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
skeleton=None
for name,spec in data['meshes'].items():
    sk=name.startswith('SK_')
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if sk else u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=sk;opt.import_animations=False;opt.create_physics_asset=False
    opt.import_materials=False;opt.import_textures=False
    options=opt.skeletal_mesh_import_data if sk else opt.static_mesh_import_data
    options.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    if sk:
        options.set_editor_property('use_t0_as_ref_pose',False)
        options.set_editor_property('update_skeleton_reference_pose',False)
        if skeleton:opt.skeleton=skeleton
    else:
        options.combine_meshes=True;options.auto_generate_collision=False;options.generate_lightmap_u_vs=False
    mesh=ingest(src/'Export'/(name+'.fbx'),dest,opt)
    slots=list(mesh.materials if sk else mesh.static_materials)
    for slot in slots:
        key=str(slot.material_slot_name)
        if not materials.get(key):raise RuntimeError(f'{name} has unbound material {key}')
        slot.material_interface=materials[key]
    if sk:
        mesh.materials=slots
        if not skeleton:
            skeleton=mesh.skeleton
            pose=skeleton.get_reference_pose()
            for role,anchor in [('string_upper','upper'),('string_nock','brace'),('string_lower','lower')]:
                loc=u.AnimPoseExtensions.get_bone_pose(pose,role,u.AnimPoseSpaces.WORLD).translation
                if max(abs(a-b) for a,b in zip((loc.x,loc.y,loc.z),data['anchors'][anchor]))>.01:
                    raise RuntimeError(f'FBX joint {role} arrived at {loc} rather than its R2 marker')
            save(skeleton)
        if mesh.skeleton!=skeleton:raise RuntimeError('Inconsistent cord skeleton '+name)
        if not skins.regenerate_lod(mesh,3,False,False):raise RuntimeError('String LOD generation failed '+name)
    else:
        mesh.static_materials=slots
        opts=u.StaticMeshReductionOptions();opts.auto_compute_lod_screen_size=True;levels=[]
        for ratio in (1.,.55,.24):
            row=u.StaticMeshReductionSettings();row.percent_triangles=ratio;levels.append(row)
        opts.reduction_settings=levels;static.set_lods(mesh,opts)
    save(mesh)
(batch/'imported.json').write_text(json.dumps(saved,indent=2),encoding='utf8')
print('FRONTIER_MODS_SAVED',len(saved),flush=True)
