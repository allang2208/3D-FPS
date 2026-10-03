"""Preserve existing performance, rebake bent joints, add tissue correctives and export."""
from pathlib import Path
import json,math
import bpy,numpy as np
from mathutils import Vector,Matrix,Quaternion
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Delivery';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'HowlV4/Delivery/M10_HowlV4_Editable.blend'))
scene=bpy.context.scene;scene.render.fps=30
rig=next(o for o in scene.objects if o.type=='ARMATURE');arm=rig.data
obj=next(o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers))
cfg=json.loads((ROOT/'rig_definition.json').read_text(encoding='utf8'))
old_rest={b.name:b.matrix_local.copy() for b in arm.bones}
roles={'Idle':'M10_Idle','Walk':'M10_Walk','Hit':'M10_Hit','Death':'M10_Death',
       'CurveLeft':'M10_CurveLeft_V2','CurveRight':'M10_CurveRight_V2','PivotLeft':'M10_PivotLeft_V2','PivotRight':'M10_PivotRight_V2',
       'Bite':'M10_BiteSnap_V3','Howl':'M10_Howl_V4'}
cache={}
for role,name in roles.items():
    action=bpy.data.actions[name];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    frames={}
    for f in range(int(action.frame_range.x),int(action.frame_range.y)+1):
        scene.frame_set(f);frames[f]={b.name:rig.pose.bones[b.name].matrix.copy() for b in arm.bones}
    cache[role]=frames
print('M10_V5_EXISTING_PERFORMANCES_CAPTURED',flush=True)

rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for spec in cfg['bones']:
    bone=arm.edit_bones.get(spec['name']) or arm.edit_bones.new(spec['name'])
    bone.use_connect=False;bone.head=spec['head'];bone.tail=spec['tail'];bone.use_deform=spec['deform']
    if spec['parent']:bone.parent=arm.edit_bones[spec['parent']]
    bone.align_roll(Vector((0,1,0)))
bpy.ops.object.mode_set(mode='OBJECT')
rest={b.name:b.matrix_local.copy() for b in arm.bones}

data=np.load(ROOT/'surface_rig_data.npz');kd=KDTree(len(data['vertices']))
for i,p in enumerate(data['vertices']):kd.insert(Vector(p),i)
kd.balance();mapping=np.array([kd.find(v.co)[1] for v in obj.data.vertices])
positions=np.empty(len(obj.data.vertices)*3,np.float32);obj.data.vertices.foreach_get('co',positions);positions=positions.reshape(-1,3)
original_normals=np.empty(len(obj.data.loops)*3,np.float32);obj.data.corner_normals.foreach_get('vector',original_normals);original_normals=original_normals.reshape(-1,3)
loop_vertices=np.empty(len(obj.data.loops),np.int32);obj.data.loops.foreach_get('vertex_index',loop_vertices)
# Meshy fused the opposite oral surfaces together. Cut only the internal seam;
# lips and cheeks stay continuous. This prevents triangles spanning both rows
# from becoming long ribbons when each tooth follows its own rigid jaw.
tri=loop_vertices.reshape(-1,3);source_tri=mapping[tri]
data_jaw=((data['bone_indices']==list(data['bone_names']).index('jaw'))*data['weights']).sum(axis=1)
jaw_tri=data_jaw[source_tri];center=data['vertices'][source_tri].mean(axis=1)
oral_r=np.sqrt((center[:,1]/.39)**2+((center[:,2]-.323)/.139)**2)
cut=(oral_r<.955)&(center[:,0]>1.56)
keep=~cut;removed_faces=int(cut.sum())
if removed_faces:
    original=obj.data;replacement=bpy.data.meshes.new('M10_SurfaceRigV5_OralSeam')
    replacement.vertices.add(len(positions));replacement.vertices.foreach_set('co',positions.ravel())
    kept=tri[keep];replacement.loops.add(kept.size);replacement.loops.foreach_set('vertex_index',kept.ravel())
    replacement.polygons.add(len(kept));replacement.polygons.foreach_set('loop_start',np.arange(len(kept),dtype=np.int32)*3);replacement.polygons.foreach_set('loop_total',np.full(len(kept),3,np.int32));replacement.polygons.foreach_set('use_smooth',np.ones(len(kept),bool))
    for layer in original.uv_layers:
        coords=np.empty(len(original.loops)*2,np.float32);layer.data.foreach_get('uv',coords)
        replacement.uv_layers.new(name=layer.name).data.foreach_set('uv',coords.reshape(-1,3,2)[keep].ravel())
    for material in original.materials:replacement.materials.append(material)
    replacement.update();obj.data=replacement
    original_normals=original_normals.reshape(-1,3,3)[keep].reshape(-1,3);loop_vertices=kept.ravel()
positions+=data['displacement'][mapping]
obj.data.vertices.foreach_set('co',positions.ravel());obj.data.update()
# Zeros ask Blender to use recalculated geometric normals; the original normal
# texture still supplies fine surface detail on top of the displaced geometry.
changed=(np.linalg.norm(data['displacement'][mapping],axis=1)>.00005)
original_normals[changed[loop_vertices]]=0
obj.data.normals_split_custom_set(original_normals.tolist())
obj.shape_key_add(name='Basis')
for name,key in [('M10_MouthOpenTissue','open_delta'),('M10_MouthWideTissue','wide_delta')]:
    shape=obj.shape_key_add(name=name);shape.data.foreach_set('co',(positions+data[key][mapping]).astype(np.float32).ravel());shape.value=0
obj.vertex_groups.clear();groups=[obj.vertex_groups.new(name=str(name)) for name in data['bone_names']]
indices=data['bone_indices'][mapping];weights=data['weights'][mapping]
for i in range(len(positions)):
    for j in range(4):
        if weights[i,j]>1e-6:groups[indices[i,j]].add([i],float(weights[i,j]),'REPLACE')
print('M10_V5_SURFACE_AND_WEIGHTS_AUTHORED',flush=True)

# Recessed oral liner closes the exposed internal seam, with a dark wet material.
liner_vertices=[];liner_faces=[];liner_weights=[];segments=64;rings=12
for j in range(rings):
    t=j/(rings-1);radius=.99*(1-t*.92)
    for i in range(segments):
        angle=2*math.pi*i/segments;vertical=math.sin(angle)
        liner_vertices.append((1.965-.255*math.cos(angle)**2-.49*t,.395*radius*math.cos(angle),.321+.137*radius*vertical))
        fraction=max(0,min(1,(.2-vertical)/.4));fraction=fraction*fraction*(3-2*fraction)
        liner_weights.append(fraction*(1-.65*t))
for j in range(rings-1):
    for i in range(segments):
        a=j*segments+i;b=j*segments+(i+1)%segments;c=b+segments;d=a+segments
        liner_faces.extend([(a,b,c),(a,c,d)])
liner_faces.append(tuple(range((rings-1)*segments,rings*segments)))
liner_data=bpy.data.meshes.new('M10_OralLiner');liner_data.from_pydata(liner_vertices,[],liner_faces);liner_data.update()
liner=bpy.data.objects.new('M10_OralLiner',liner_data);scene.collection.objects.link(liner);liner.parent=rig
modifier=liner.modifiers.new('M10_OralLinerSkin','ARMATURE');modifier.object=rig
ghead=liner.vertex_groups.new(name='head');gjaw=liner.vertex_groups.new(name='jaw')
for i,weight in enumerate(liner_weights):ghead.add([i],1-weight,'REPLACE');gjaw.add([i],weight,'REPLACE')
for p in liner_data.polygons:p.use_smooth=True
material=bpy.data.materials.new('M_M10_OralInterior');material.use_nodes=True
bsdf=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Base Color'].default_value=(.008,.0015,.003,1);bsdf.inputs['Roughness'].default_value=.55
liner_data.materials.append(material)
oral_objects=[liner]

def oral_object(name,vertices,faces,jaw_weights,tint,roughness):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    part=bpy.data.objects.new(name,mesh);scene.collection.objects.link(part);part.parent=rig
    skin=part.modifiers.new(name+'Skin','ARMATURE');skin.object=rig
    hg=part.vertex_groups.new(name='head');jg=part.vertex_groups.new(name='jaw')
    for i,w in enumerate(jaw_weights):
        if w<1:hg.add([i],1-w,'REPLACE')
        if w>0:jg.add([i],w,'REPLACE')
    for p in mesh.polygons:p.use_smooth=True
    mat=bpy.data.materials.new('M_'+name);mat.use_nodes=True
    shader=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');shader.inputs['Base Color'].default_value=(*tint,1);shader.inputs['Roughness'].default_value=roughness
    mesh.materials.append(mat);oral_objects.append(part);return part

# Complete separate tooth rows and a rounded gum rim replace the fused interior.
# Each tooth is a closed curved solid with one rigid skeletal owner.
tv=[];tf=[];tw=[]
for is_lower,count_teeth in [(False,19),(True,17)]:
    for tooth in range(count_teeth):
        y=-.335+.67*tooth/(count_teeth-1);side=abs(y)/.335;wave=math.sin(tooth*2.37)
        z=.321+(-1 if is_lower else 1)*.132*math.sqrt(1-(y/.386)**2)
        x=2.012-.28*(y/.386)**2
        length=(.092 if is_lower else .106)*(1-.46*side)+.015*wave
        width=(.019 if is_lower else .021)*(1-.23*side);base=len(tv);slices=12;levels=7
        for j in range(levels):
            t=j/(levels-1);radius=width*(1-t)**.72+.00035
            center_tooth=Vector((x+.012*math.sin(t*math.pi)-.012*t*t,y+(.002*wave)*t,z+(1 if is_lower else -1)*length*t))
            for k in range(slices):
                a=2*math.pi*k/slices;tv.append(tuple(center_tooth+Vector((radius*.78*math.cos(a),radius*math.sin(a),0))));tw.append(float(is_lower))
        for j in range(levels-1):
            for k in range(slices):
                a=base+j*slices+k;b=base+j*slices+(k+1)%slices;c=b+slices;d=a+slices;tf.extend([(a,b,c),(a,c,d)])
        tf.append(tuple(base+k for k in reversed(range(slices))));tf.append(tuple(base+(levels-1)*slices+k for k in range(slices)))
oral_object('M10_OralTeeth',tv,tf,tw,(.58,.48,.35),.31)
gv=[];gf=[];gw=[];tube_segments=12
for i in range(segments):
    a=2*math.pi*i/segments;s=math.sin(a);c=math.cos(a);center_gum=Vector((2.012-.28*c*c,.386*c,.321+.132*s))
    jaw=max(0,min(1,(.2-s)/.4));jaw=jaw*jaw*(3-2*jaw)
    for k in range(tube_segments):
        b=2*math.pi*k/tube_segments;gv.append(tuple(center_gum+Vector((.019*math.cos(b),.022*c*math.sin(b),.026*s*math.sin(b)))));gw.append(jaw)
for i in range(segments):
    for k in range(tube_segments):
        a=i*tube_segments+k;b=i*tube_segments+(k+1)%tube_segments;c=((i+1)%segments)*tube_segments+(k+1)%tube_segments;d=((i+1)%segments)*tube_segments+k;gf.extend([(a,b,c),(a,c,d)])
oral_object('M10_OralGum',gv,gf,gw,(.16,.060,.055),.46)
print('M10_V5_ORAL_REBUILD',removed_faces,'faces removed; 36 rigid teeth and recessed liner',flush=True)

def aim(name,head,tail):
    old=Vector(arm.bones[name].tail_local-arm.bones[name].head_local)
    return Matrix.Translation(head)@old.rotation_difference(tail-head).to_matrix().to_4x4()@rest[name].to_3x3().to_4x4()
def solve(pts,root,pole,target):
    upper=(pts[1]-pts[0]).length;lower=(pts[2]-pts[1]).length;delta=target-root
    dist=max(abs(upper-lower)+.002,min(delta.length,(upper+lower)*.98));direction=delta.normalized()
    plane=pole-root;plane-=direction*plane.dot(direction);plane.normalize()
    along=(upper*upper-lower*lower+dist*dist)/(2*dist)
    return root+direction*along+plane*math.sqrt(max(0,upper*upper-along*along)),root+direction*dist
clips={}
for role,frames in cache.items():
    action=bpy.data.actions.new('M10_'+role+'_V5');action.use_fake_user=True;rig.animation_data.action=action
    for f,old in frames.items():
        scene.frame_set(f);target={n:m.copy() for n,m in old.items()}
        for leg in cfg['legs']:
            pts=[Vector(p) for p in leg['points']];parent=leg['parent'];upper,lower,foot=leg['bones']
            body=old[parent]@rest[parent].inverted();root=body@pts[0];pole=body@pts[1]
            knee,end=solve(pts,root,pole,old[foot].translation)
            target[upper]=aim(upper,root,knee);target[lower]=aim(lower,knee,end)
            target[foot]=Matrix.Translation(end)@old[foot].to_3x3().to_4x4()
            for sector in ('inner','outer'):
                n=leg['region']+'_toes_'+sector;target[n]=target[foot]@old[foot].inverted()@old[n]
            helper=leg['region']+'_socket';base=body@rest[helper]
            q=base.to_quaternion().slerp(target[upper].to_quaternion(),.45)
            target[helper]=Matrix.Translation(root)@q.to_matrix().to_4x4()
        for bone in arm.bones:
            local=rest[bone.name].inverted()@rest[bone.parent.name]@target[bone.parent.name].inverted()@target[bone.name] if bone.parent else rest[bone.name].inverted()@target[bone.name]
            p=rig.pose.bones[bone.name];p.rotation_mode='QUATERNION';p.matrix_basis=local
            for channel in ('location','rotation_quaternion','scale'):p.keyframe_insert(channel,frame=f)
        if not rig.animation_data.action_slot and action.slots:rig.animation_data.action_slot=action.slots[0]
    clips[role]={'action':action.name,'file':str(OUT/f'A_M10_{role}_V5.fbx'),'frames':len(frames),'seconds':(len(frames)-1)/30}
    print('M10_V5_REBAKED',role,flush=True)

# Export new skeleton/skin to a separate package so old rig inputs remain recoverable.
rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);obj.select_set(True)
for part in oral_objects:part.select_set(True)
bpy.context.view_layer.objects.active=rig
export=dict(use_selection=True,path_mode='AUTO',add_leaf_bones=False,use_armature_deform_only=False,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z')
# Modifier application would erase the corrective shapes in FBX.
mesh_file=OUT/'SK_M10_SurfaceRig_V5.fbx'
bpy.ops.export_scene.fbx(filepath=str(mesh_file),bake_anim=False,use_mesh_modifiers=False,**export)
obj.select_set(False)
for part in oral_objects:part.select_set(False)
for role,row in clips.items():
    action=bpy.data.actions[row['action']];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    scene.frame_start=1;scene.frame_end=row['frames'];scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=row['file'],bake_anim=True,**export)
rig.animation_data.action=bpy.data.actions[clips['Idle']['action']];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_end=97;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M10_SurfaceRigV5_Editable.blend'))
(ROOT/'export_contract.json').write_text(json.dumps({'mesh_file':str(mesh_file),'clips':clips,'bones':len(arm.bones),'morphs':['M10_MouthOpenTissue','M10_MouthWideTissue'],'topology_changed':True,'removed_oral_bridge_faces':removed_faces,'oral_liner_vertices':len(liner_vertices),'game_tested':False},indent=2),encoding='utf8')
print('M10_SURFACE_RIG_V5_SOURCE_SAVED',flush=True)
