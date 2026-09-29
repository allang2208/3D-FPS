import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];E=u.EditorAssetLibrary
BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10';a=u.load_asset(BODY)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
out={'pie':bool(world),'dirty':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],'body':BODY,'sha256':hashlib.sha256((P/'Content/Weapons/LMG201/Cover10/SK_LMG201_Cover10.uasset').read_bytes()).hexdigest(),'slots':[],'materials':{},'runtime':[]}
for i,s in enumerate(a.materials):
 m=s.material_interface;path=m.get_path_name() if m else None;out['slots'].append({'id':i,'slot':str(s.material_slot_name),'material':path})
 if m and path not in out['materials']:
  base=m.get_base_material();row={'class':m.get_class().get_name(),'base':base.get_path_name()}
  for prop in ['used_with_skeletal_mesh','automatically_set_usage_in_editor','two_sided','blend_mode']:
   try:row[prop]=str(base.get_editor_property(prop))
   except Exception as ex:row[prop]=str(ex)
  try:row['textures']=[t.get_path_name() for t in u.MaterialEditingLibrary.get_used_textures(m)]
  except Exception as ex:row['textures_error']=str(ex)
  out['materials'][path]=row
if world:
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  for c in actor.get_components_by_class(u.SkeletalMeshComponent):
   mesh=c.get_editor_property('skeletal_mesh_asset')
   if mesh and mesh.get_path_name().split('.')[0]==BODY:
    out['runtime'].append({'actor':actor.get_name(),'component':c.get_name(),'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]})
(O/'capture.json').write_text(json.dumps(out,indent=2));print('REPAIR36_CAPTURE',json.dumps({'pie':out['pie'],'dirty':out['dirty'],'sha256':out['sha256'],'cloth':[x for x in out['slots'] if 'Cloth33' in x['slot']],'materials':{k:v for k,v in out['materials'].items() if 'Cloth' in k},'runtime_components':len(out['runtime'])}),flush=True)
