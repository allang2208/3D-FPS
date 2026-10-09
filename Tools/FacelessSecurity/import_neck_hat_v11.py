"""Import V11 sewn neck + physical cap and save the existing guard Blueprint."""
from pathlib import Path
import json
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V11')
DEST='/Game/Monsters/FacelessSecurity'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; no asset changes made')
bp=u.load_asset(DEST+'/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class())
if cdo.get_editor_property('visual_mesh').get_name() not in ['SK_FacelessSecurity_V10','SK_FacelessSecurity_V11']:
    raise RuntimeError('Active security mesh changed outside this revision')
manifest=json.loads((ROOT/'authoring_receipt.json').read_text(encoding='utf-8'))
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')

# Static hat: use authored convex collision instead of complex render triangles.
name='SM_SecurityServiceCap_V11'
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
data=opt.static_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
data.combine_meshes=True;data.auto_generate_collision=False;data.one_convex_hull_per_ucx=True
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
task=u.AssetImportTask();task.filename=str(ROOT/'Delivery'/(name+'.fbx'));task.destination_path=DEST+'/Accessories';task.destination_name=name
task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=opt;task.factory=u.FbxFactory()
AT.import_asset_tasks([task]);hat=u.load_asset(DEST+'/Accessories/'+name)
if not hat or not task.imported_object_paths:raise RuntimeError('Cap import did not create an asset')
slots=list(hat.get_editor_property('static_materials'))
for slot in slots:
    family=str(slot.get_editor_property('imported_material_slot_name')).removeprefix('Security_').split('.')[0]
    material=u.load_asset(DEST+'/Materials/M_FS1_'+family)
    if not material:raise RuntimeError('Missing hat material '+family)
    slot.material_interface=material
hat.set_editor_property('static_materials',slots)
LIB.set_metadata_tag(hat,'SecurityAccessoryRevision','V11 service cap; native head-local pivot; two authored convex collision hulls')
if not LIB.save_loaded_asset(hat,False):raise RuntimeError('Cap save failed')
hat_path=hat.get_path_name()

# Reuse the existing skeletal importer, stopping before its BP write.
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/import_uniform_v04.py').read_text(encoding='utf-8').replace('V04','V11')
src=src.split("mesh=u.load_asset(report['meshes']['outfit']);cdo.set_editor_property")[0]
src=src.replace('torso-only belt; no side pouches; front-only collar panels; continuous garment and trim weights',
    'Sewn anatomical neck opening and paired wall; local shoulder clearance; retained V10 boot skin and V09 hands')
exec(compile(src,'security_v11_skeletal_import','exec'))
report['cpp_modified']=True
report['saved'].append(hat_path)

# Add an opt-in component only to this security Blueprint; generic zombies
# have no hat and no additional per-frame work.
subsystem=u.get_engine_subsystem(u.SubobjectDataSubsystem);library=u.SubobjectDataBlueprintFunctionLibrary
handles=subsystem.k2_gather_subobject_data_for_blueprint(bp)
hat_component=None;mesh_parent=handles[0]
for handle in handles:
    obj=library.get_object_for_blueprint(library.get_data(handle),bp)
    if isinstance(obj,u.SkeletalMeshComponent):mesh_parent=handle
    if isinstance(obj,u.SecurityHatComponent):hat_component=obj
if hat_component is None:
    params=u.AddNewSubobjectParams(parent_handle=mesh_parent,new_class=u.SecurityHatComponent,blueprint_context=bp)
    handle,reason=subsystem.add_new_subobject(params=params)
    hat_component=library.get_object_for_blueprint(library.get_data(handle),bp)
    if not hat_component:raise RuntimeError('Cannot add cap component: '+str(reason))
    subsystem.rename_subobject(handle,u.Text('SecurityServiceCap'))
offset=manifest['hat']['relative_location_cm']
transform=u.Transform(location=u.Vector(*offset),rotation=u.Rotator(0,0,0),scale=u.Vector(1,1,1))
hat_component.set_static_mesh(hat)
hat_component.set_editor_property('head_bone','head')
hat_component.set_editor_property('head_attachment_transform',transform)
hat_component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
# Overlap events are disabled by the native component constructor.

cdo=u.get_default_object(bp.generated_class());mesh=u.load_asset(report['meshes']['outfit'])
cdo.set_editor_property('visual_mesh',mesh);cdo.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
LIB.set_metadata_tag(bp,'UniformRevision','V11 sewn anatomical neckline and shoulder clearance; V10 boot mask preserved')
LIB.set_metadata_tag(bp,'HatRevision','V11 head-bound security cap; head point damage releases one 0.32 kg physical prop; 35 s lifetime')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
report.update(stage='saved',blueprint=bp.get_path_name(),hat=hat_path,hat_attachment=manifest['hat'],
    animation_and_combat_timing='Preserved V06 idle/walk, V10 attack recovery, current contact window, speed and ground offset',
    complete_body='Existing intact V09 body retained',rendered=False,game_tested=False)
record();print('SECURITY_V11_NECK_HAT_SAVED '+json.dumps(report),flush=True)
