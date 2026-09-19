import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'))
src=bpy.data.objects['SK_Manny_Arms_Export'];sr=bpy.data.objects['SK_M4_Infima']
def rigid(m):
 p,q,_=m.decompose();return Matrix.LocRotScale(p,q,Vector((1,1,1)))
source_rest={b.name:rigid(sr.matrix_world@b.matrix_local) for b in sr.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in sr.data.bones}
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'ArmsRepair20260909/Integrated/SK_AKM_HandsRepair_Source.blend'))
r=bpy.data.objects['SK_AKM_Viewmodel'];s=bpy.context.scene
with bpy.data.libraries.load(str(O.parent/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'),link=False) as (a,b):b.objects=['SK_Manny_Arms_Export']
arms=b.objects[0];s.collection.objects.link(arms);world=arms.matrix_world.copy()
target_rest={b.name:rigid(r.matrix_world@b.matrix_local) for b in r.data.bones}
mapping={}
for g in arms.vertex_groups:
 n=g.name
 while n not in target_rest and n is not None:n=parents.get(n)
 if n:mapping[g.index]=n
weights=[];coords=[]
for v in arms.data.vertices:
 p=world@v.co;out=Vector();total=0;w={}
 for g in v.groups:
  if g.group not in mapping:continue
  name=arms.vertex_groups[g.group].name;target=mapping[g.group]
  out+=(target_rest[target]@source_rest[name].inverted()@p)*g.weight;total+=g.weight
  w[target]=w.get(target,0)+g.weight
 assert total>1e-5,(v.index,total)
 coords.append(r.matrix_world.inverted()@(out/total));weights.append({n:value/total for n,value in w.items()})
arms.data=arms.data.copy();arms.name='SK_AKM_MannyArms'
for v,p in zip(arms.data.vertices,coords):v.co=p
arms.vertex_groups.clear()
groups={n:arms.vertex_groups.new(name=n) for n in set(mapping.values())}
for i,w in enumerate(weights):
 for n,v in w.items():groups[n].add([i],v,'REPLACE')
arms.modifiers.clear();mod=arms.modifiers.new('SharedMannySkin','ARMATURE');mod.object=r
arms.parent=r;arms.matrix_parent_inverse=Matrix.Identity(4);arms.matrix_basis=Matrix.Identity(4)
arms.hide_render=False;arms.hide_set(False)
export=[o for o in s.objects if o.name.startswith('AKMR_') and o.type=='MESH']+[arms]
for o in s.objects:
 if o.type=='MESH':o.hide_render=o not in export
r.hide_set(False);r.animation_data.action=None
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
for o in export+[r]:o.select_set(True)
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(O/'SK_AKM_SharedArms.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False)
a=bpy.data.actions.get('AKM_idle');r.animation_data.action=a
if a and a.slots:r.animation_data.action_slot=a.slots[0]
s.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'AKM_SharedArms_Editable.blend'))
(O/'shared_arms.json').write_text(json.dumps({'source':'M4TacticalToss20260910/SK_Manny_Arms_Export','vertices':len(arms.data.vertices),'materials':[m.name for m in arms.data.materials],'remapped_groups':{arms.vertex_groups[i].name:n for i,n in []},'meshes':[o.name for o in export]},indent=2))
print('SHARED_ARMS_EXPORTED')
