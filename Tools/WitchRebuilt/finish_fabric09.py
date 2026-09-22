"""Resume only the mesh-slot save after Fabric09 materials were saved successfully."""
import unreal as u,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from fabric09_settings import *
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=ROOT.parent.parent/'FPSGAME.uproject':raise RuntimeError('Wrong editor project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; retained')
path=DEST+'/SK_WitchRebuilt'
if any(p.get_path_name()==path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Unsaved Witch mesh retained')
mesh=u.load_asset(path);slots=list(mesh.materials);instances={}
for part,(_,name,_) in PARTS.items():
 instances[part]=u.load_asset(DEST+'/Materials/'+name)
 if not instances[part]:raise RuntimeError('Saved Fabric09 instance missing: '+part)
assignments=[]
for slot in slots:
 name=str(slot.get_editor_property('imported_material_slot_name'))
 part=next((p for p in PARTS if p in name),None)
 if part:
  slot.material_interface=instances[part];assignments.append({'slot':name,'material':instances[part].get_path_name()})
mesh.set_editor_property('materials',slots)
u.EditorAssetLibrary.set_metadata_tag(mesh,'Surface','Fabric09: upper, cuffs, waist, skirt and lining share the same opaque weave; Seams07 geometry and Drape07 retained')
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save still blocked; material assets remain saved')
result={'revision':'Fabric09','master':DEST+'/Materials/M_WitchRebuilt_Fabric09.M_WitchRebuilt_Fabric09',
 'assignments':assignments,'parameters':json.loads((OUT/'fabric09_parameters.json').read_text(encoding='utf-8')),
 'texture_samples_per_fabric_pixel':2,'new_texture_assets':0,'new_material_slots':0,
 'geometry_animation_cloth_solver_changed':False,'runtime_tested':False,'performance_measured':False,'user_visual_acceptance':False}
(OUT/'ue_asset_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
p=ROOT/'ue_delivery.json';delivery=json.loads(p.read_text(encoding='utf-8'));delivery.update(status='Fabric09 shared cloth installed; user visual and performance acceptance pending',revision09=result)
p.write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result))
