"""Save the repaired rigid cap and update only the existing hat component."""
import unreal as u,json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V14');D='/Game/Monsters/FacelessSecurity'
L=u.EditorAssetLibrary
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; no assets modified')
bp=u.load_asset(D+'/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class())
ss=u.get_engine_subsystem(u.SubobjectDataSubsystem);lib=u.SubobjectDataBlueprintFunctionLibrary
components=[]
for h in ss.k2_gather_subobject_data_for_blueprint(bp):
    obj=lib.get_object_for_blueprint(lib.get_data(h),bp)
    if isinstance(obj,u.SecurityHatComponent):components.append(obj)
if len(components)!=1:raise RuntimeError('Expected the single existing security hat component')
component=components[0];old=component.get_editor_property('static_mesh')
if not old or old.get_name()!='SM_SecurityServiceCap_V11':raise RuntimeError('Current hat changed outside this revision')
attachment=component.get_editor_property('head_attachment_transform')
body=cdo.get_editor_property('visual_mesh');bone=component.get_editor_property('head_bone')
name='SM_SecurityServiceCap_V14';dest=D+'/Accessories/'+name
if L.does_asset_exist(dest):raise RuntimeError('V14 asset already exists; inspect receipt before repeating import')
report={'revision':'V14','stage':'importing','previous_hat':old.get_path_name(),'body_mesh':body.get_path_name(),
        'saved':[],'game_tested':False,'rendered':False,'cpp_modified':False}
def record():(R/'ue_delivery.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def save(a):
    if not L.save_loaded_asset(a,False):raise RuntimeError('Save failed: '+a.get_path_name())
    report['saved'].append(a.get_path_name());record()
record();u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
data=opt.static_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
data.combine_meshes=True;data.auto_generate_collision=False;data.one_convex_hull_per_ucx=True
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
task=u.AssetImportTask();task.filename=str(R/'Delivery'/(name+'.fbx'));task.destination_path=D+'/Accessories';task.destination_name=name
task.automated=True;task.save=False;task.replace_existing=False;task.options=opt;task.factory=u.FbxFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);hat=u.load_asset(dest)
if not hat or not task.imported_object_paths:raise RuntimeError('Repaired cap import did not create an asset')
slots=list(hat.get_editor_property('static_materials'))
for slot in slots:
    family=str(slot.get_editor_property('imported_material_slot_name')).removeprefix('Security_').split('.')[0]
    material=u.load_asset(D+'/Materials/M_FS1_'+family)
    if not material:raise RuntimeError('Missing material family '+family)
    slot.material_interface=material
hat.set_editor_property('static_materials',slots)
L.set_metadata_tag(hat,'SecurityAccessoryRevision','V14 sewn band/visor shared rim; closed underside and side returns; existing head-local pivot')
save(hat);report['stage']='hat_saved';report['hat']=hat.get_path_name();record()
component.set_static_mesh(hat)
# Do not recreate the component, reset the head transform, or touch the body.
L.set_metadata_tag(bp,'HatRevision','V14 sewn band/visor; existing head attachment and physical headshot drop retained')
u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class())
if cdo.get_editor_property('visual_mesh')!=body:raise RuntimeError('Unexpected body mesh change')
save(bp)
report.update(stage='saved',blueprint=bp.get_path_name(),head_bone=str(bone),
              preserved='V13 uniform, current animation clips, head attachment transform, mass, drop impulse and lifetime',
              collision='Two authored convex bodies: original crown and updated visor')
record();print('SECURITY_HAT_V14_SAVED '+json.dumps(report),flush=True)
