import unreal as u,json
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/SkinDeathV13/Records')
out.mkdir(parents=True,exist_ok=True)
m=u.load_asset('/Game/Monsters/HangingBellM09/V04/SK_M09');p=m.physics_asset
def get(o,n):
 try:return o.get_editor_property(n)
 except Exception as e:return str(e)
r={'mesh':m.get_path_name(),'physics':p.get_path_name(),'bodies':[],'constraints':[]}
for prop,output in [('skeletal_body_setups','bodies'),('constraint_setup','constraints')]:
 values=get(p,prop)
 if isinstance(values,str):r[prop]=values;continue
 for o in values:
  item={'name':o.get_name()}
  if output=='bodies':
   item.update(bone=str(get(o,'bone_name')),shapes=str(get(o,'agg_geom')),instance=str(get(o,'default_instance')))
  else:item['instance']=str(get(o,'default_instance'))
  r[output].append(item)
c=u.new_object(u.SkeletalMeshComponent);c.set_skeletal_mesh_asset(m)
r['bones']=[{'name':str(c.get_bone_name(i)),'parent':str(c.get_parent_bone(c.get_bone_name(i))),
 'transform':str(c.get_socket_transform(c.get_bone_name(i),u.RelativeTransformSpace.RTS_COMPONENT))} for i in range(c.get_num_bones())]
(out/'physics_before.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print('M09_PHYSICS_INSPECTED')
