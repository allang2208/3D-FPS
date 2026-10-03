"""Read the reported weapon's material binding and current preview state only."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;L=u.MaterialEditingLibrary
report={'meshes':{},'materials':{},'current_preview':{},'asset_changes':False}
def prop(o,n,d=None):
 try:return o.get_editor_property(n)
 except Exception:return d
def material(m):
 if not m:return None
 path=m.get_path_name()
 if path in report['materials']:return path
 row={'class':m.get_class().get_name()}
 report['materials'][path]=row
 if isinstance(m,u.MaterialInstance):
  parent=prop(m,'parent');row['parent']=material(parent)
  row['scalar_parameters']={k:L.get_material_instance_scalar_parameter_value(m,k) for k in ('SourceColorWeight','SourceRoughnessWeight','Roughness','Metallic','WeaponWetness','GrainRoughness')}
  c=L.get_material_instance_vector_parameter_value(m,'FinishColor');row['FinishColor']=[c.r,c.g,c.b,c.a]
  row['base_overrides']=str(prop(m,'base_property_overrides'))
  overrides=prop(m,'base_property_overrides')
  row['two_sided_override']={k:prop(overrides,k) for k in ('override_two_sided','two_sided')}
 elif isinstance(m,u.Material):
  row.update(two_sided=prop(m,'two_sided'),skeletal_usage=prop(m,'used_with_skeletal_mesh'),domain=str(prop(m,'material_domain')),shading=str(prop(m,'shading_model')),blend=str(prop(m,'blend_mode')))
  if 'M_WeaponPreviewResolved' in path:
   row['graph']=[{'type':n.get_class().get_name(),'parameter':str(prop(n,'parameter_name',''))} for n in L.get_material_expressions(m)]
 return path
for path in ['/Game/Weapons/PitViper2011/Integrated20261002/Single/SK_PitViper2011_Manny']+['/Game/Weapons/PitViper2011/Attachments20261002/SM_PitViper2011_'+k for k in ('holographic','panoramic_red_dot','eoth_holographic')]:
 mesh=u.load_asset(path)
 slots=mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials
 report['meshes'][path]={str(s.material_slot_name):material(s.material_interface) for s in slots}
material(u.load_asset('/Game/UI/GunsmithWorkbench/M_WeaponPreviewResolved'))
try:
 world=u.EditorLevelLibrary.get_game_world()
 if world:
  for actor in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
   for component in actor.get_components_by_class(u.SkeletalMeshComponent):
    asset=component.get_skeletal_mesh_asset()
    if asset and '/Weapons/PitViper2011/' in asset.get_path_name():
     report['current_preview'][component.get_path_name()]={'asset':asset.get_path_name(),'materials':[material(component.get_material(i)) for i in range(component.get_num_materials())]}
except Exception as e:report['live_scope_note']=str(e)
(O/'material_diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('PIT_VIPER_MATERIAL_DIAGNOSIS_SAVED',flush=True)
