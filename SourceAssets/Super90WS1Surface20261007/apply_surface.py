"""Save Super90 WS1 instances and material sections in the existing editor."""
import unreal as u,json,shutil,hashlib,math
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];R='/Game/Weapons/Super90/Cransh20261006';D='/Game/Weapons/Super90/WS1Surface20261007'
M=json.loads((O/'authoring.json').read_text());E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('Exit PIE before importing the Super90 material sections. No assets were modified.')
receipt={'completed':False,'saved':[],'materials':{},'mesh_slots':[],'attachments':{},'runtime_tested':False}
B=O/'Before';B.mkdir(exist_ok=True)
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing material input '+path)
    return asset
def backup(asset):
    rel=asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset';src=P/'Content'/rel;dst=B/rel
    if src.exists() and not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in receipt['saved']:receipt['saved'].append(asset.get_path_name())
    record();return asset
def texture(name,color):
    path=D+'/Textures/'+name;task=u.AssetImportTask();task.filename=str(O/'Textures'/(name+'.png'));task.destination_path=D+'/Textures';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=load(path)
    tex.srgb=color;tex.compression_settings=u.TextureCompressionSettings.TC_BC7
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON;tex.never_stream=False
    E.set_metadata_tag(tex,'Super90WS1Input','Clean receiver with retained author ink' if color else 'UV0: R=0 G=0 B=original AO A=1; one AO layer')
    return save(tex)
clean=texture('T_Super90_CleanReceiver',True);mask=texture('T_Super90_SurfaceMask',False)
neutral=load('/Game/Weapons/WeaponSurface/Textures/T_WS_MaskNeutral');flat=load('/Engine/EngineMaterials/DefaultNormal')
normal=load(R+'/Textures/T_S90_TTI_Benelli_M4_Normal_brand_friendly')
backup(normal);normal.flip_green_channel=False;save(normal)
def make(name,preset,values,vectors,structure=flat,surface_mask=neutral,source=None):
    path=D+'/Materials/MI_Super90_'+name
    mi=load(path) if E.does_asset_exist(path) else A.create_asset('MI_Super90_'+name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property('parent',load('/Game/Weapons/WeaponSurface/Presets/MI_WS_'+preset))
    defaults={'SourceColorWeight':0.,'SourceRoughnessWeight':0.,'MaskUVChannel':0.,'GrainTileCm':2.,'GrainRoughness':.012,
              'MottleRoughness':.005,'MottleColor':0.,'ScratchAmount':0.,'HandlingPolish':0.,'Stipple':0.,
              'EdgeWear':0.,'EdgeHighlight':.06,'CavityDarken':0.,'CavityRoughness':0.,'AOStrength':.6,'WeaponWetness':0.}
    defaults.update(values)
    for key,value in defaults.items():L.set_material_instance_scalar_parameter_value(mi,key,value)
    for key,value in vectors.items():L.set_material_instance_vector_parameter_value(mi,key,u.LinearColor(*value,1))
    for key,value in {'SurfaceNormal':structure,'SurfaceMask':surface_mask,'SourceBaseColor':source or clean}.items():L.set_material_instance_texture_parameter_value(mi,key,value)
    L.update_material_instance(mi);E.set_metadata_tag(mi,'Super90SurfaceStandard','WS1.1 Clean project finish; shared M_WeaponSurface; single built-in wet layer')
    E.set_metadata_tag(mi,'Super90SurfaceRecipe','SourceAssets/Super90WS1Surface20261007/authoring.json; old colour only as protected ink, source roughness disabled')
    save(mi);receipt['materials'][name]={'asset':mi.get_path_name(),'parent':mi.parent.get_path_name(),'scalars':defaults,'vectors':vectors};record();return mi
materials={}
for name,recipe in M['recipe'].items():
    area=M['slots'][name];bead=242.*math.sqrt(area['area_m2']/area['uv_area'])
    values={'Metallic':recipe['metallic'],'EdgeMetallic':recipe['metallic'],'Roughness':recipe['roughness'],'BeadScale':bead}
    if name=='TTI_Benelli_M4':values['SourceColorWeight']=1.
    structure=normal;surface_mask=mask
    if name=='matchsaverz':structure=load(R+'/Textures/T_S90_matchsaverz_Normal');surface_mask=neutral
    materials[name]=make(name,recipe['preset'],values,{'FinishColor':recipe['color']},structure,surface_mask)
mount=make('MountSteel','CleanAnodized',{'Metallic':1.,'EdgeMetallic':1.,'Roughness':.44,'AOStrength':0.},{'FinishColor':(.022,.023,.024)})
mesh=load(R+'/SK_Super90_V7');backup(mesh);old={str(s.material_slot_name):s.material_interface for s in mesh.materials}
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=mesh.skeleton
    opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=M['mesh_fbx'];task.destination_path=R;task.destination_name='SK_Super90_V7'
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task])
    mesh=load(R+'/SK_Super90_V7');slots=list(mesh.materials)
    for i,s in enumerate(slots):
        key=str(s.material_slot_name)
        if key in materials:s.material_interface=materials[key]
        else:
            if key not in old and 'Manny_S90_'+key in old:s.material_slot_name='Manny_S90_'+key;key=str(s.material_slot_name)
            s.material_interface=old[key]
        slots[i]=s
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None)
    editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);settings=editor.get_lod_build_settings(mesh,0)
    settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True;settings.recompute_normals=False;settings.recompute_tangents=False;editor.set_lod_build_settings(mesh,0,settings)
    E.set_metadata_tag(mesh,'Super90SurfaceStandard','WS1.1 Clean; source PNG V-origin conversion only; rebuilt material regions; preserved geometry, skin and skeleton')
    E.set_metadata_tag(mesh,'Super90AtlasMapping',M['atlas_mapping'])
    E.set_metadata_tag(mesh,'Super90SourceSHA256',hashlib.sha256(Path(M['mesh_fbx']).read_bytes()).hexdigest())
    save(mesh);receipt['mesh_slots']=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in mesh.materials];record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
# Keep the just-fitted Super90 metal rail shoes/saddles on the same finish.
# Optical glass, reticles, body coatings and non-metal grip skins retain their slots.
for source in ('Super90Optics20261007','Super90Foregrips20261007'):
    rows=json.loads((O.parent/source/'import_receipt.json').read_text())['meshes']
    for kind,path in rows.items():
        part=load(path);slots=list(part.static_materials);changed=False
        for i,s in enumerate(slots):
            label=str(s.material_slot_name)
            if kind.startswith('Rail_') or label.startswith(('Super90_Foregrip_Saddle','Resonance_Metal_M4','M_M4_prism_1')):
                if not changed:backup(part)
                s.material_interface=mount;slots[i]=s;changed=True
        if changed:
            part.set_editor_property('static_materials',slots);save(part)
            receipt['attachments'][part.get_path_name()]=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in part.static_materials];record()
outfit=P/'Content/ColdSteelData/modular_outfits.json'
if not (B/outfit.name).exists():shutil.copy2(outfit,B/outfit.name)
config=json.loads(outfit.read_text(encoding='utf-8-sig'))
config['profiles'][mesh.get_path_name()]['hide_source_materials']=[i for i,s in enumerate(mesh.materials) if str(s.material_slot_name).startswith('Manny_S90_')]
outfit.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt['completed']=True;record();print('SUPER90_WS1_SAVED',len(receipt['saved']),flush=True)
