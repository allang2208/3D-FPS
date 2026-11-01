"""Save Detail V2 into the existing M24 body attachment; no skeletal reimport."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;BASE=O.parent;P=BASE.parents[1]
D='/Game/Weapons/M24/AdvancedAction20261029';HOST='/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
R=dict(complete=False,revision='DetailV2',saved=[],runtime_tested=False,animations_changed=False,
       host_modified=False,editor_opened=False,headless_import='-run=pythonscript' in u.SystemLibrary.get_command_line().lower())
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing '+path)
    return asset
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in R['saved']:R['saved'].append(asset.get_path_name())
    record()
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(D) or p==HOST for p in dirty):raise RuntimeError('Unsaved M24 edits retained')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; import deferred')
if not json.loads((O/'bake_receipt.json').read_text())['complete']:raise RuntimeError('Mask authoring not complete')
spec=json.loads((O/'authoring.json').read_text())
def texture(name,kind):
    task=u.AssetImportTask();task.filename=str(O/'Textures'/(name+'.png'));task.destination_path=D+'/Textures';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=load(task.destination_path+'/'+name)
    tex.srgb=False;tex.never_stream=False
    tex.compression_settings={'N':u.TextureCompressionSettings.TC_NORMALMAP,'R':u.TextureCompressionSettings.TC_GRAYSCALE,'Mask':u.TextureCompressionSettings.TC_MASKS}[kind]
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind=='N' else u.TextureGroup.TEXTUREGROUP_WEAPON
    if kind=='N':tex.flip_green_channel=True
    save(tex);return tex
tex={key:{k:texture('T_M24_AAS_V2_'+key+'_'+k,k) for k in ('N','R')} for key in ('Metal','Steel','Interior')}
mask=texture('T_M24_AAS_V2_SurfaceMask','Mask')
master=load(D+'/Materials/M_M24AdvancedSurface')
for k,v in dict(automatically_set_usage_in_editor=False,used_with_skeletal_mesh=False,used_with_morph_targets=False,used_with_clothing=False).items():master.set_editor_property(k,v)
errors=list(L.recompile_material(master) or [])
if errors:raise RuntimeError('Material compile '+str(errors[:4]))
save(master)
settings={'M24_AAS_CoatedMetal':((.032,.034,.037),1.,.395,'Metal'),
          'M24_AAS_SatinSteel':((.074,.078,.083),1.,.335,'Steel'),
          'M24_AAS_Interior':((.009,.010,.011),0.,.62,'Interior')}
materials={};R['material_bindings']={}
for name,(color,metal,rough,key) in settings.items():
    path=D+'/Materials/MI_'+name
    mi=load(path) if E.does_asset_exist(path) else E.duplicate_asset('/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanPolymer',path)
    L.set_material_instance_parent(mi,master);L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(*color,1))
    scalars=dict(Metallic=metal,EdgeMetallic=metal,Specular=.5,Roughness=rough,MaskUVChannel=1,
        SourceColorWeight=0,SourceRoughnessWeight=1,SourceRoughnessPivot=.5,GrainRoughness=0,
        MottleRoughness=0,MottleColor=0,Stipple=0,GrainTileCm=4,BeadScale=9.68,
        EdgeWear=0,EdgeHighlight=.045 if metal else .01,ScratchAmount=0,CavityDarken=.020,
        CavityRoughness=.018,HandlingPolish=0,AOStrength=.45,WeaponWetness=0)
    for k,v in scalars.items():L.set_material_instance_scalar_parameter_value(mi,k,v)
    for k,v in {'SurfaceNormal':tex[key]['N'],'SourceRoughness':tex[key]['R'],'SurfaceMask':mask}.items():L.set_material_instance_texture_parameter_value(mi,k,v)
    L.update_material_instance(mi);save(mi);materials[name]=mi
    R['material_bindings'][name]=dict(path=mi.get_path_name(),metallic=metal,roughness=rough,
        normal=tex[key]['N'].get_path_name(),roughness_texture=tex[key]['R'].get_path_name(),mask=mask.get_path_name(),mask_uv=1)
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,row in spec['models'].items():
        mesh_path=D+'/Meshes/SM_M24_'+key
        if E.does_asset_exist(mesh_path):
            existing=load(mesh_path)
            slots=[]
            for name in spec['materials']:
                slot=u.StaticMaterial(material_interface=materials[name],material_slot_name=name)
                # ImportedMaterialSlotName is editor-only/EditConst, so it is
                # absent from Python's constructor. Struct text import writes
                # the complete authoring identity without touching the graph.
                if not slot.import_text('(ImportedMaterialSlotName="'+name+'")'):
                    raise RuntimeError('Cannot author imported slot '+name)
                slots.append(slot)
            # Seed the import contract before FBX reimport snapshots old slots.
            # This data is only saved after the replacement geometry is imported.
            existing.set_editor_property('static_materials',slots)
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        opt.reset_to_fbx_on_material_conflict=True
        imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False
        imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=row['file'];task.destination_path=D+'/Meshes';task.destination_name='SM_M24_'+key
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory();task.options=opt;A.import_asset_tasks([task])
        mesh=load(task.destination_path+'/'+task.destination_name)
        for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,materials[str(slot.material_slot_name)])
        sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
        bs=sub.get_lod_build_settings(mesh,0);bs.recompute_normals=False;bs.recompute_tangents=False
        bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True
        u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh);sub.set_lod_build_settings(mesh,0,bs)
        E.set_metadata_tag(mesh,'M24AdvancedActionSource',str(O/'M24_AdvancedAction_DetailV2.blend'))
        E.set_metadata_tag(mesh,'M24AdvancedActionRevision','DetailV2; body only; native stock and hands preserved')
        save(mesh)
        R['mesh_materials']=[dict(slot=str(s.material_slot_name),material=s.material_interface.get_path_name() if s.material_interface else None) for s in mesh.static_materials]
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
icons=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
mapping=('category_body','ue_m24_category_body','body_m24_advanced_action','ue_m24_body_m24_advanced_action')
for key in mapping:
    target=icons/(key+'.png');backup=O/'Before/Icons'/(key+'.png');backup.parent.mkdir(exist_ok=True)
    if target.exists() and not backup.exists():shutil.copy2(target,backup)
    shutil.copy2(O/'Icons/m24_advanced_action.png',target)
    task=u.AssetImportTask();task.filename=str(target);task.destination_path='/Game/UI/AttachmentIcons20260913/FramedFirearms';task.destination_name='T_'+key
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);icon=load(task.destination_path+'/'+task.destination_name)
    for k,v in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,srgb=True,never_stream=True,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,max_texture_size=1024).items():icon.set_editor_property(k,v)
    save(icon)
R.update(complete=True,host=HOST,original_stock=True,icons=list(mapping),triangles=spec['models']['m24_advanced_action']['triangles']);record()
print('M24_DETAIL_V2_ASSETS_SAVED',len(R['saved']),flush=True)
