"""Save isolated SVCh mesh, finish and contact profile. No PIE or runtime test."""
import json,copy,hashlib,runpy
from pathlib import Path
import unreal as u
O=Path(__file__).parent
P=Path(u.Paths.project_dir()).resolve()
ROOT='/Game/Weapons/SVCH/Refined20261018'
SURFACE=ROOT+'/SurfaceV4'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt={'saved':[],'runtime_tested':False,'complete':False}
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())
    (O/'install_receipt.json').write_text(json.dumps(receipt,indent=1))
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing '+path)
    return asset
textures={}
for kind in ('Metal','Polymer','Rubber'):
    task=u.AssetImportTask();task.filename=str(O/'Textures'/('T_SVCH_'+kind+'_N.png'))
    task.destination_path=SURFACE+'/Textures';task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task])
    tex=load(SURFACE+'/Textures/T_SVCH_'+kind+'_N')
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
    tex.set_editor_property('srgb',False)
    save(tex);textures[kind]=tex

final=ROOT+'/SK_SVCH_Refined_R4'
if E.does_asset_exist(final):raise RuntimeError('Revision mesh exists; do not merge material slots through reimport.')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False
opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
opt.skeleton=load('/Game/Weapons/M4HK416Replica/SK_M4_HK416_Skeleton')
opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
task=u.AssetImportTask();task.filename=str(O/'Exports/SK_SVCH_Refined.fbx')
task.destination_path=ROOT;task.destination_name='SK_SVCH_Refined_R4'
task.automated=True;task.save=False;task.options=opt;task.factory=u.FbxFactory()
A.import_asset_tasks([task]);mesh=load(final)
editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
build=editor.get_lod_build_settings(mesh,0)
build.use_full_precision_u_vs=True;build.use_high_precision_tangent_basis=True
build.recompute_normals=False;build.recompute_tangents=True
editor.set_lod_build_settings(mesh,0,build)
donor=load('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock')
arm_mats={str(s.material_slot_name):s.material_interface for s in donor.get_editor_property('materials')}
presets={'Body':'CleanAnodized','BarrelSteel':'CleanSatinSteel','BoltCarrier':'CleanPolishedSteel',
         'Magazine':'CleanPolymer','Polymer':'CleanPolymer','Rubber':'CleanPolymer',
         'Cartridge':'CleanPolishedSteel','MagRelease':'CleanAnodized','Selector':'CleanAnodized'}
slots=list(mesh.get_editor_property('materials'));arm_slots=[];surface_slots={}
if len(slots)!=11:raise RuntimeError('Expected 9 surface identities and 2 arm slots, got '+str(len(slots)))
for i,slot in enumerate(slots):
    name=str(slot.material_slot_name)
    if name in arm_mats and name.startswith('MI_Manny_'):
        slot.material_interface=arm_mats[name];slots[i]=slot;arm_slots.append(i);continue
    part=name.removeprefix('SVCH_')
    if part not in presets:raise RuntimeError('Unknown imported material identity '+name)
    instance=u.load_asset(SURFACE+'/Materials/MI_SVCH_'+part) or A.create_asset('MI_SVCH_'+part,SURFACE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(instance,load('/Game/Weapons/WeaponSurface/Presets/MI_WS_'+presets[part]))
    kind='Rubber' if part=='Rubber' else 'Polymer' if part in ('Polymer','Magazine') else 'Metal'
    L.set_material_instance_texture_parameter_value(instance,'SurfaceNormal',textures[kind])
    # Cube projection is 25 cm per tile, only for tangent normals/water beads.
    # WS1 grain uses PreSkinnedPosition, and was never driven by UV island size.
    L.set_material_instance_scalar_parameter_value(instance,'BeadScale',60.5)
    L.set_material_instance_scalar_parameter_value(instance,'GrainTileCm',3.)
    L.set_material_instance_scalar_parameter_value(instance,'GrainRoughness',.012 if kind=='Metal' else .02)
    L.set_material_instance_scalar_parameter_value(instance,'MottleRoughness',0. if kind=='Metal' else .005)
    if part=='Rubber':L.set_material_instance_scalar_parameter_value(instance,'Roughness',.74)
    if part=='Cartridge':L.set_material_instance_vector_parameter_value(instance,'FinishColor',u.LinearColor(.24,.14,.055,1))
    E.set_metadata_tag(instance,'SVCHSurface','Welded bevel geometry and restrained micro normals, 20261018')
    save(instance);slot.material_interface=instance;slots[i]=slot;surface_slots[name]=i
if len(arm_slots)!=2:raise RuntimeError('Cannot determine both native arm slots')
mesh.set_editor_property('materials',slots)
E.set_metadata_tag(mesh,'Attribution','Low-Poly SVCh 308 by TastyTony, Sketchfab 739390f40fef4b22ac9a71b72f7a95b8, CC BY 4.0; local surface refinement')
save(mesh)
runpy.run_path(str(O/'install_arm_correctives.py'))
profile_path=ROOT+'/DA_SVCH_BaseGrip'
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
profile=u.load_asset(profile_path) or A.create_asset('DA_SVCH_BaseGrip',ROOT,u.WeaponGripProfile,factory)
if not profile.set_shared_clips_from_json((O/'shared_profile.json').read_text()):raise RuntimeError('Profile production failed')
save(profile)
receipt['profile_source_sha256']=hashlib.sha256((O/'shared_profile.json').read_bytes()).hexdigest()
mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh)
ref=mod.get_bone_transform('WPN_root',True)
receipt['root_bind']={'translation':[ref.translation.x,ref.translation.y,ref.translation.z],
                     'rotation':[ref.rotation.x,ref.rotation.y,ref.rotation.z,ref.rotation.w],
                     'scale':[ref.scale3d.x,ref.scale3d.y,ref.scale3d.z]}
del mod

# Preserve parallel edits to the outfit table; add the new mesh's exact identity
# only after every corresponding asset has been saved.
path=P/'Content/ColdSteelData/modular_outfits.json'
data=json.loads(path.read_text(encoding='utf-8-sig'))
source='/Game/Weapons/SVCH/Integrated20261017/SK_SVCH_Manny.SK_SVCH_Manny'
entry=copy.deepcopy(data['profiles'][source])
entry['hide_source_materials']=arm_slots;entry['shirt_covers']=arm_slots;entry['glove_covers']=[]
data['profiles'][mesh.get_path_name()]=entry
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt.update(complete=True,mesh=mesh.get_path_name(),profile=profile.get_path_name(),
               arm_slots=arm_slots,surface_slots=surface_slots)
(O/'install_receipt.json').write_text(json.dumps(receipt,indent=1))
print('SVCH_REFINED_SAVED',json.dumps(receipt),flush=True)
