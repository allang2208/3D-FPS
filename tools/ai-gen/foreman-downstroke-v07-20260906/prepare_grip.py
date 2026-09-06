# Executed by build_motion.py after loading V05; preserves shoulder smoothing.
import numpy as np
a.animation_data.action=None
for tr in a.animation_data.nla_tracks:tr.mute=True
for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4);pb.rotation_mode='QUATERNION'
bpy.context.view_layer.objects.active=a;bpy.ops.object.mode_set(mode='EDIT')
for side,sign in [('L',1),('R',-1)]:
 b=a.data.edit_bones['fingers_cup.'+side];b.head=(sign*.868,-.13,1.205);b.tail=(sign*.87,-.13,1.085)
 b=a.data.edit_bones.new('fingers_tip.'+side);b.head=(sign*.866,-.13,1.13);b.tail=(sign*.85,-.13,1.055);b.parent=a.data.edit_bones['fingers_cup.'+side]
 b=a.data.edit_bones.new('thumb.'+side);b.head=(sign*.81,-.205,1.255);b.tail=(sign*.755,-.245,1.185);b.parent=a.data.edit_bones['hand.'+side]
bpy.ops.object.mode_set(mode='OBJECT')
def smooth(a0,b0,x):
 u=max(0,min(1,(x-a0)/(b0-a0)));return u*u*(3-2*u)
for side,sign in [('L',1),('R',-1)]:
 hand=body.vertex_groups['hand.'+side];cup=body.vertex_groups['fingers_cup.'+side];thumb=body.vertex_groups.new(name='thumb.'+side);tip=body.vertex_groups.new(name='fingers_tip.'+side)
 for v in body.data.vertices:
  x,y,z=v.co;old={body.vertex_groups[g.group].name:g.weight for g in v.groups};total=old.get(hand.name,0)+old.get(cup.name,0)
  if total<1e-7:continue
  # Thumb occupies the anterior, inner branch. Four fingers lie behind it.
  tw=(1-smooth(-.24,-.19,y))*(1-smooth(.79,.835,abs(x)))*(1-smooth(1.24,1.31,z))
  fw=(1-smooth(1.17,1.245,z))*smooth(.785,.84,abs(x))*(1-tw)
  distal=1-smooth(1.09,1.17,z)
  hand.add([v.index],total*(1-fw-tw),'REPLACE');cup.add([v.index],total*fw*(1-distal),'REPLACE');tip.add([v.index],total*fw*distal,'REPLACE');thumb.add([v.index],total*tw,'REPLACE')
 # Existing V05 finger channels will be replaced for all rebuilt clips.
# Relax the branch boundaries on mesh adjacency so individual triangles cannot
# remain attached to the palm while their neighbours curl into the grip.
groups=list(body.vertex_groups);weights=np.zeros((len(body.data.vertices),len(groups)))
for v in body.data.vertices:
 for g in v.groups:weights[v.index,g.group]=g.weight
edges=np.array([e.vertices[:] for e in body.data.edges]);source=np.concatenate([edges[:,0],edges[:,1]]);target=np.concatenate([edges[:,1],edges[:,0]])
count=np.maximum(1,np.bincount(source,minlength=len(weights)))
hand_columns=[g.index for g in groups if g.name.startswith(('hand.','fingers_','thumb.'))]
region=weights[:,hand_columns].sum(axis=1)>.92
for iteration in range(5):
 average=np.stack([np.bincount(source,weights=weights[target,k],minlength=len(weights))/count for k in range(len(groups))],axis=1)
 weights[region]=.4*weights[region]+.6*average[region]
for g in groups:g.remove(list(range(len(weights))))
for k,g in enumerate(groups):
 for i in np.where(weights[:,k]>1e-7)[0]:g.add([int(i)],float(weights[i,k]),'REPLACE')
for v in body.data.vertices:
 influences=sorted([(g.group,g.weight) for g in v.groups if g.weight>1e-7],key=lambda row:-row[1]);total=sum(w for _,w in influences[:4])
 for idx,_ in influences:body.vertex_groups[idx].remove([v.index])
 for idx,w in influences[:4]:body.vertex_groups[idx].add([v.index],w/total,'REPLACE')
# A rigid grip makes the hand/weapon relationship visible; the rope starts at its tip.
bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.021,depth=.22,location=(-.805,-.125,1.18),rotation=(math.pi/2,0,0))
handle=bpy.context.object;handle.name='WhipHandle';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
mat=bpy.data.materials.new('Foreman leather whip grip');mat.diffuse_color=(.075,.035,.016,1);mat.use_nodes=True
node=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');node.inputs['Base Color'].default_value=(.075,.035,.016,1);node.inputs['Roughness'].default_value=.85
handle.data.materials.append(mat);vg=handle.vertex_groups.new(name='hand.R');vg.add(list(range(len(handle.data.vertices))),1,'REPLACE')
mod=handle.modifiers.new('Foreman grip skin','ARMATURE');mod.object=a;handle.parent=a
