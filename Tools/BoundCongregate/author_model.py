"""Preserve Meshy skin/UVs; author separate fitted garments and a ten-limb rig."""
import bpy, math, json, random
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
recipe=json.loads((ROOT/'Authoring/rig_recipe.json').read_text());S=recipe['scale'];G=recipe['ground_z']
bpy.ops.wm.open_mainfile(filepath=recipe['source'])
body=next(o for o in bpy.context.scene.objects if o.type=='MESH');body.name='BC_Flesh'
bpy.context.view_layer.objects.active=body;body.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
source_points=[v.co.copy() for v in body.data.vertices]
bvh=BVHTree.FromPolygons(source_points,[p.vertices[:] for p in body.data.polygons])
kd=KDTree(len(source_points))
for i,p in enumerate(source_points):kd.insert(p,i)
kd.balance()
skin=np.load(ROOT/'Authoring/skin_weights.npz');names=skin['names'].tolist()

def point(p):return Vector((p[0]*S,p[1]*S,(p[2]-G)*S))
ad=bpy.data.armatures.new('SKEL_BoundCongregate');rig=bpy.data.objects.new('Armature',ad)
bpy.context.collection.objects.link(rig);bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
for b in recipe['bones']:
    eb=ad.edit_bones.new(b['name']);eb.head=point(b['head']);eb.tail=point(b['tail']);eb.use_deform=b['deform']
    if b['parent']:eb.parent=ad.edit_bones[b['parent']]
    axis=(eb.tail-eb.head).normalized();eb.align_roll(Vector((0,-1,0)) if abs(axis.y)<.95 else Vector((0,0,1)))
bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
for p in rig.pose.bones:p.rotation_mode='QUATERNION'
for v in body.data.vertices:v.co=point(v.co)
for n in names:body.vertex_groups.new(name=n)
for i,(ids,ws) in enumerate(zip(skin['indices'],skin['weights'])):
    for j,w in zip(ids,ws):
        if w>.001:body.vertex_groups[int(j)].add([i],float(w),'REPLACE')
modifier=body.modifiers.new('BC_AnatomicalSkin','ARMATURE');modifier.object=rig;body.parent=rig
body.data.materials[0].name='BC_Flesh'
for node in body.data.materials[0].node_tree.nodes:
    if node.type=='TEX_IMAGE' and node.image:
        im=node.image
        links=[link for output in node.outputs for link in output.links]
        key='normal' if any(link.to_node.type=='NORMAL_MAP' for link in links) else 'texture_0' if any(link.to_socket.name=='Base Color' for link in links) else 'texture_0_metallic_roughness'
        path=ROOT/'Textures'/(key+'.png');node.image=bpy.data.images.load(str(path),check_existing=True)
        if key!='texture_0':node.image.colorspace_settings.name='Non-Color'

def material(name,color,rough,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m
fabric=material('BC_RagFabric',(.095,.106,.069),.86)
lining=material('BC_Lining',(.18,.155,.102),.91)
strapmat=material('BC_Binding',(.034,.030,.021),.71)
metalmat=material('BC_Hardware',(.19,.17,.125),.54,.65)
for mat in [fabric,lining]:
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes.get('Principled BSDF')
    for suffix,socket in [('BaseColor','Base Color'),('Roughness','Roughness'),('Normal','Normal')]:
        texture=nodes.new('ShaderNodeTexImage');texture.image=bpy.data.images.load(str(ROOT/'Textures'/('BC_Fabric_'+suffix+'.png')),check_existing=True)
        if suffix!='BaseColor':texture.image.colorspace_settings.name='Non-Color'
        if suffix=='Normal':
            normal=nodes.new('ShaderNodeNormalMap');links.new(texture.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs['Normal'])
        else:links.new(texture.outputs['Color'],p.inputs[socket])
cloth=[];accessories=[]

def skin_object(ob,points,pin_values=None,fixed=None):
    for n in names:ob.vertex_groups.new(name=n)
    for vi,p in enumerate(points):
        if fixed:ob.vertex_groups[fixed].add([vi],1,'REPLACE');continue
        _,near,_=kd.find(Vector(p))
        for j,w in zip(skin['indices'][near],skin['weights'][near]):
            if w>.001:ob.vertex_groups[names[int(j)]].add([vi],float(w),'REPLACE')
    mod=ob.modifiers.new('BC_GarmentSkin','ARMATURE');mod.object=rig;ob.parent=rig
    if pin_values is not None:
        color=ob.data.color_attributes.new(name='ClothTravel',type='FLOAT_COLOR',domain='POINT')
        for c,d in zip(color.data,pin_values):c.color=(d,0,0,1)

def mesh(name,points,faces,uvs,mat,pins=None,fixed=None):
    data=bpy.data.meshes.new(name);data.from_pydata([point(p) for p in points],[],faces);data.update()
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);data.materials.append(mat)
    layer=data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        poly.use_smooth=True
        for li in poly.loop_indices:layer.data[li].uv=uvs[data.loops[li].vertex_index]
    skin_object(ob,points,pins,fixed);return ob

# Two asymmetrical remnants of one split robe. High edges attach to the back,
# the mouth and central pustule ridge stay uncovered. All coordinates use the
# actual surface raycast before the hanging hem leaves the body.
def cape(name,side,y0,y1,t0,t1,nx,ny,mat):
    pts=[];faces=[];uv=[];pins=[]
    for row in range(ny+1):
        v=row/ny
        for col in range(nx+1):
            u=col/nx;y=y0+(y1-y0)*u
            torn=.10*math.sin(col*2.37)+.06*math.sin(col*5.2)
            theta=side*(t0+(t1-t0)*(v+max(0,v-.7)*torn))
            direction=Vector((math.sin(theta),0,math.cos(theta)));origin=Vector((0,y,-.16))
            hit,normal,_,_=bvh.ray_cast(origin,direction,1.0)
            if hit is None:hit=origin+direction*.37;normal=direction
            p=hit+direction*(.012+.012*v+.010*math.sin(u*13*math.pi)*math.sin(v*math.pi))
            # A draped free edge, detached from the lumpy surface with several
            # centimetres of motion clearance and no fabric across a leg root.
            if v>.60:
                p+=Vector((side*.030,0,-.15))*((v-.60)/.40)**1.5
            pts.append(tuple(p));uv.append((u*1.8,v*1.6));pins.append(max(0,min(1,(v-.28)/.72))*.70)
    for r in range(ny):
        for c in range(nx):
            if r>ny-3 and c%11==4:continue
            if r==ny-5 and c in [9,10]:continue
            a=r*(nx+1)+c;faces.append((a,a+1,a+nx+2,a+nx+1) if side>0 else (a+nx+1,a+nx+2,a+1,a))
    ob=mesh(name,pts,faces,uv,mat,pins);cloth.append(ob)
    return pts,nx,ny
cape('BC_LeftTornRobe',-1,-.22,.35,.53,1.78,28,23,fabric)
cape('BC_RightLining',1,.05,.43,.8,1.76,20,18,lining)

# Short remnants on two different donors, leaving elbows and wrists mobile.
def sleeve(leg,index):
    p=[Vector(v) for v in leg['points']];a=p[0].lerp(p[1],.1);end=p[0].lerp(p[1],.73)
    axis=(end-a).normalized();x=axis.cross(Vector((0,0,1))).normalized();z=x.cross(axis).normalized()
    pts=[];uv=[];pins=[];faces=[];nu=22;nv=8
    for row in range(nv+1):
        v=row/nv
        for c in range(nu+1):
            u=c/nu;angle=math.tau*u;center=a.lerp(end,v);rad=x*math.cos(angle)+z*math.sin(angle)
            hit,_,_,_=bvh.ray_cast(center,rad,.24)
            radius=(hit-center).length if hit else .063
            q=center+rad*(radius+.012+.007*math.sin(v*12+u*9))
            if row==nv:q+=axis*(.018*math.sin(c*3.1))
            pts.append(tuple(q));uv.append((u,v*.6));pins.append(max(0,v-.35)*.18)
    for r in range(nv):
        for c in range(nu):
            if r==nv-1 and c%9 in [2,3]:continue
            a0=r*(nu+1)+c;faces.append((a0,a0+1,a0+nu+2,a0+nu+1))
    ob=mesh(f'BC_DonorSleeve{index}',pts,faces,uv,fabric,pins,f'leg_{leg["name"]}_upper');cloth.append(ob)
for i in [1,8]:sleeve(recipe['legs'][i],i)

# A narrow restraint across the left shoulder anchors the torn cloth. Its
# stitched edge and metal tag are separate visible geometry, not skin paint.
pts=[];uv=[];faces=[]
for row in range(49):
    v=row/48;theta=-.30-v*1.70
    for edge in [-1,1]:
        y=-.09+edge*.018;origin=Vector((0,y,-.16));direction=Vector((math.sin(theta),0,math.cos(theta)))
        hit,_,_,_=bvh.ray_cast(origin,direction,1.0)
        if hit is None:hit=origin+direction*.4
        pts.append(tuple(hit+direction*.042));uv.append((edge*.5+.5,v*4))
    if row:faces.append((row*2-2,row*2-1,row*2+1,row*2))
strap=mesh('BC_ShoulderRestraint',pts,faces,uv,strapmat,fixed='body');accessories.append(strap)
solid=strap.modifiers.new('WornLeatherThickness','SOLIDIFY');solid.thickness=.004*S
bpy.context.view_layer.objects.active=strap;bpy.ops.object.modifier_apply(modifier=solid.name)

# Small enamel identification plate, deliberately only M (no invented serial).
tagcenter=point((-.408,-.11,-.12))
bpy.ops.mesh.primitive_cube_add(size=1,location=tagcenter);tag=bpy.context.object;tag.name='BC_M_Tag'
tag.scale=(.006*S,.045*S,.065*S);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bev=tag.modifiers.new('RoundedCorners','BEVEL');bev.width=.003*S;bev.segments=3
bpy.ops.object.modifier_apply(modifier=bev.name);tag.data.materials.append(metalmat)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
skin_object(tag,[(0,0,0)]*len(tag.data.vertices),fixed='body');accessories.append(tag)
bpy.ops.object.text_add(location=tagcenter+Vector((-.004*S,0,0)))
letter=bpy.context.object;letter.name='BC_M_Stamp';letter.data.body='M';letter.data.size=.043*S
letter.data.align_x='CENTER';letter.data.align_y='CENTER';letter.data.extrude=.0007*S
letter.rotation_euler=(math.pi/2,0,-math.pi/2);bpy.ops.object.convert(target='MESH')
letter=bpy.context.object;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
letter.data.materials.append(strapmat);skin_object(letter,[(0,0,0)]*len(letter.data.vertices),fixed='body');accessories.append(letter)

proxies=[];proxy_materials={}
for ob in cloth:
    proxy=ob.copy();proxy.data=ob.data.copy();proxy.name=ob.name+'_SimulationProxy';bpy.context.collection.objects.link(proxy)
    key=proxy.data.materials[0].name
    if key not in proxy_materials:
        pm=proxy.data.materials[0].copy();pm.name=key+'_Proxy';proxy_materials[key]=pm
    proxy.data.materials[0]=proxy_materials[key]
    proxy.hide_render=True;proxies.append(proxy)
    bpy.context.view_layer.objects.active=ob
    shell=ob.modifiers.new('RealFabricThickness','SOLIDIFY');shell.thickness=.0018*S;shell.offset=0
    bpy.ops.object.modifier_apply(modifier=shell.name)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.fps=30;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/BoundCongregate_Clothed_Rig.blend'))
objects=[body]+cloth+accessories+proxies
def select_export():
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects+[rig]:ob.select_set(True)
    bpy.context.view_layer.objects.active=rig
def export(path,animation=False):
    select_export();bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','ARMATURE'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
        add_leaf_bones=False,use_armature_deform_only=False,bake_anim=animation,
        bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,
        mesh_smooth_type='FACE',path_mode='STRIP')
export(ROOT/'Exports/SK_BoundCongregate.fbx')

rest={b.name:b.matrix_local.copy() for b in ad.bones}
def set_delta(name,offset=None,rotation=None,scale=None):
    pb=rig.pose.bones[name];pb.location=Vector((0,0,0)) if offset is None else Vector(offset)
    pb.rotation_quaternion=Quaternion() if rotation is None else rotation
    pb.scale=(1,1,1) if scale is None else scale
def desired_bone(name,a,b):
    base=rest[name];old=ad.bones[name].tail_local-ad.bones[name].head_local
    q=old.rotation_difference(b-a);m=q.to_matrix().to_4x4()@base;m.translation=a
    rig.pose.bones[name].matrix=m
def solve_leg(leg,target,bodymatrix):
    name=leg['name'];root,knee,ankle,toe=[point(p) for p in leg['points']]
    upper=f'leg_{name}_upper';lower=f'leg_{name}_lower';foot=f'leg_{name}_foot'
    root=bodymatrix@root;oldknee=bodymatrix@knee
    a=(knee-point(leg['points'][0])).length;b=(ankle-knee).length
    delta=target-root;d=min(delta.length,(a+b)*.98);d=max(d,abs(a-b)+.002)
    forward=delta.normalized();pole=oldknee-root;pole-=forward*pole.dot(forward)
    if pole.length<.01:pole=Vector((0,0,1))-forward*forward.z
    x=(a*a-b*b+d*d)/(2*d);h=math.sqrt(max(0,a*a-x*x));joint=root+forward*x+pole.normalized()*h
    target=root+forward*d;desired_bone(upper,root,joint);desired_bone(lower,joint,target)
    fm=rest[foot].copy();fm.translation=target;rig.pose.bones[foot].matrix=fm

manifest={}
for role,duration in [('Idle',4),('Walk',1.8),('TurnLeft',1.8),('TurnRight',1.8),('Bite',1.7),('Hit',.7),('Death',2.2)]:
    action=bpy.data.actions.new('A_BoundCongregate_'+role);rig.animation_data_create();rig.animation_data.action=action
    scene.frame_start=1;scene.frame_end=round(duration*30)+1
    for frame in range(1,scene.frame_end+1):
        scene.frame_set(frame);time=(frame-1)/30;phase=time/duration
        for pb in rig.pose.bones:set_delta(pb.name)
        bodypb=rig.pose.bones['body'];breath=math.sin(time*math.tau/4)
        offset=Vector((0,0,.009*S*breath));rot=Quaternion((0,1,0),.012*breath)
        pulse=0
        if role=='Bite':
            wind=math.sin(math.pi*min(time/.65,1)) if time<.65 else 0
            pulse=max(0,1-abs(time-.92)/.23);pulse=pulse*pulse*(3-2*pulse)
            offset.y=(.025*wind-.10*pulse)*S;offset.z+=.025*S*wind
            rot=Quaternion((1,0,0),-.06*wind+.10*pulse)
            for side,sign in [('L',-1),('R',1)]:
                rig.pose.bones['jaw_'+side].rotation_quaternion=Quaternion((0,1,0),sign*(.12*wind-.22*pulse))
        elif role=='Hit':
            pulse=math.sin(math.pi*min(1,time/.7))*math.exp(-time*3)
            offset.y=.035*S*pulse;rot=Quaternion((0,1,0),-.07*pulse)
        elif role=='Death':
            collapse=(min(1,time/1.7)**2)*(3-2*min(1,time/1.7))
            offset.z=-.18*S*collapse;rot=Quaternion((0,1,0),.16*collapse)
        # Convert a world-space body offset into its authored local bone basis.
        bodypb.location=rest['body'].to_3x3().inverted()@offset
        bodypb.rotation_quaternion=rot
        bpy.context.view_layer.update()
        parent_matrices={}
        for name in ['body_front','body_rear']:
            parent_matrices[name]=rig.pose.bones[name].matrix@rest[name].inverted()
        for i,leg in enumerate(recipe['legs']):
            target=point(leg['points'][2]);cycle=(phase+leg['phase'])%1
            if role in ['Walk','TurnLeft','TurnRight']:
                stance=recipe['stance']
                if cycle<stance:travel=.5-cycle/stance;lift=0
                else:
                    a=(cycle-stance)/(1-stance);travel=-.5+(a*a*(3-2*a));lift=.105*math.sin(math.pi*a)**2
                if role=='Walk':target.y-=travel*recipe['stride_m']
                else:
                    sign=1 if role=='TurnLeft' else -1
                    tangent=Vector((-target.y,target.x,0)).normalized();target+=tangent*travel*.26*sign
                target.z+=lift
            elif role=='Death':target+=Vector((target.x,target.y,0)).normalized()*.10*collapse
            parent='body_front' if leg['points'][0][1]<0 else 'body_rear'
            solve_leg(leg,target,parent_matrices[parent])
        for pb in rig.pose.bones:
            if pb.name.startswith(('curl_','feeler_','scent_','grasp_')):
                n=int(pb.name.rsplit('_',1)[1]);amp=.018 if pb.name.startswith('curl') else .045
                if role=='Bite':amp*=1+1.5*pulse
                pb.rotation_quaternion=Quaternion((1,0,0),amp*math.sin(time*2.3-n*.65))@Quaternion((0,0,1),amp*.5*math.sin(time*1.7-n*.7))
            pb.keyframe_insert('location',frame=frame,group=pb.name);pb.keyframe_insert('rotation_quaternion',frame=frame,group=pb.name)
        bpy.context.view_layer.update()
    scene.frame_set(1);export(ROOT/'Exports'/f'A_BoundCongregate_{role}.fbx',True)
    manifest[role]=dict(duration=duration,fps=30,loop=role in ['Idle','Walk','TurnLeft','TurnRight'])
    print('AUTHORED_MOTION',role,flush=True)
rig.animation_data.action=None
for pb in rig.pose.bones:set_delta(pb.name)
scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/BoundCongregate_Clothed_Rig.blend'))
(ROOT/'Authoring/motion_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
(ROOT/'Records/model_authoring.json').write_text(json.dumps(dict(source_preserved=True,body_triangles=197398,
    garment_objects=[o.name for o in cloth],skeleton_bones=len(ad.bones),ground_limbs=10,scale=S,
    walk_speed_cm=recipe['stride_m']/(recipe['walk_cycle']*recipe['stance'])*100,
    bite_contact_seconds=.92,gameplay_tested=False,garment_acceptance_rendered=False),indent=2),encoding='utf8')
