import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
old=O.parent/'M24ReceiverGripRebuild20261031'
spec=json.loads((old/'geometry_contract.json').read_text())
paths={n:'/Game/Weapons/M24/ReceiverGripRebuild20261031/Meshes/'+n for n in spec['exports']}
paths['host']='/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9'
paths['scope']='/Game/Weapons/M24/Surface20261027/SM_M24_m24_custom_scope_6x'
paths['advanced_original']='/Game/Weapons/M24/AdvancedAction20261029/Meshes/SM_M24_m24_advanced_action'
R={'assets':{},'materials':{},'live_components':[]}
scalars=['SourceColorWeight','SourceRoughnessWeight','Roughness','Metallic','Specular','EdgeMetallic','EdgeWear','EdgeHighlight','GrainRoughness','MottleRoughness','MottleColor','Stipple','ScratchAmount','HandlingPolish','NormalStrength','NormalIntensity','MaskUVChannel','AOStrength','WeaponWetness','SourceRoughnessPivot']
vectors=['FinishColor','Tint','BaseColor','Color','EdgeColor']
textures=['SourceBaseColor','SourceRoughness','SourceMetallic','SurfaceNormal','SurfaceMask']
def material(m):
 if not m or m.get_path_name() in R['materials']:return
 out={'class':m.get_class().get_name(),'parent':None,'scalar':{},'vector':{},'texture':{}}
 if isinstance(m,u.MaterialInstanceConstant):
  parent=m.get_editor_property('parent');out['parent']=parent.get_path_name() if parent else None
  for k in scalars:out['scalar'][k]=L.get_material_instance_scalar_parameter_value(m,k)
  for k in vectors:
   v=L.get_material_instance_vector_parameter_value(m,k);out['vector'][k]=[v.r,v.g,v.b,v.a]
  for k in textures:
   v=L.get_material_instance_texture_parameter_value(m,k)
   out['texture'][k]={'path':v.get_path_name(),'srgb':v.get_editor_property('srgb'),'compression':str(v.get_editor_property('compression_settings')),'flip_green':v.get_editor_property('flip_green_channel')} if isinstance(v,u.Texture2D) else v.get_path_name() if v else None
  out['scalar_overrides']=[{'name':str(p.parameter_info.name),'value':p.parameter_value} for p in m.scalar_parameter_values]
 R['materials'][m.get_path_name()]=out
for name,path in paths.items():
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 mats=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials
 disk=Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset')
 R['assets'][name]={'path':path,'sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),'slots':[]}
 for slot in mats:
  m=slot.material_interface;R['assets'][name]['slots'].append({'slot':str(slot.material_slot_name),'material':m.get_path_name() if m else None});material(m)
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=editor.get_game_world() if editor else None
R['pie']=bool(world)
if world:
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
  for c in actor.get_components_by_class(u.MeshComponent):
   mesh=c.get_editor_property('static_mesh') if isinstance(c,u.StaticMeshComponent) else c.get_skeletal_mesh_asset() if isinstance(c,u.SkeletalMeshComponent) else None
   if not mesh or not any(x in mesh.get_path_name() for x in ('/Weapons/M24/','/Weapons/SkeletonSniperStock')):continue
   R['live_components'].append({'actor':actor.get_name(),'component':c.get_name(),'mesh':mesh.get_path_name(),'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())],'relative_rotation':str(c.relative_rotation),'relative_location':str(c.relative_location),'relative_scale':str(c.relative_scale3d)})
(O/'inputs.json').write_text(json.dumps(R,indent=2))
print('M24_CONTINUITY_INPUTS',len(R['assets']),len(R['materials']),R['pie'],flush=True)
