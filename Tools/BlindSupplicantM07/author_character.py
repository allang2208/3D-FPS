"""Author M-07 body, six separate tissue panels, rig and cloth construction source.
No render, cloth playback, runtime probe or acceptance test is performed.
"""
import bpy, bmesh, json, math
from pathlib import Path
import numpy as np
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT=ROOT/'Authoring'; DEL=ROOT/'Delivery'; DEL.mkdir(exist_ok=True)
source=np.load(OUT/'source_mesh.npz')
partition=np.load(OUT/'source_regions.npz')
region=json.loads((OUT/'region_authoring.json').read_text())
cloth=json.loads((OUT/'cloth_manifest.json').read_text())
scale=region['scale_to_meters'];ground=region['ground_source_y']

def convert(p): return Vector((p[0]*scale,-p[2]*scale,(p[1]-ground)*scale))
raw=source['positions'];points=np.c_[raw[:,0],-raw[:,2],raw[:,1]-ground]*scale
uvs=source['uvs'].copy();uvs[:,1]=1-uvs[:,1]
triangles=source['indices'].reshape(-1,3);face_labels=partition['face_labels']
joint={name:convert(pos) for name,pos in region['joint_guides_source'].items()}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1

def collection(name):
    c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);return c
VISIBLE=collection('M07_Display');ANATOMY=collection('M07_CompleteAnatomySource')
SIM=collection('M07_HiddenClothProxies');COLLISION=collection('M07_BodyCollisionSource')
ORIGINAL=collection('M07_FrozenOriginalSource')

def move_collection(o,c):
    for old in list(o.users_collection):old.objects.unlink(o)
    c.objects.link(o)

def skin_material(name, membrane=False):
    m=bpy.data.materials.new(name);m.use_nodes=True
    nt=m.node_tree;bs=nt.nodes.get('Principled BSDF')
    for semantic,filename,socket in [('base','M07_basecolor_source.jpg','Base Color'),
                                    ('rough','M07_roughness.png','Roughness'),
                                    ('metal','M07_metallic.png','Metallic')]:
        n=nt.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(ROOT/'Textures'/filename),check_existing=True)
        if semantic!='base':n.image.colorspace_settings.name='Non-Color'
        nt.links.new(n.outputs['Color'],bs.inputs[socket])
    n=nt.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(ROOT/'Textures/M07_normal_source.jpg'),check_existing=True)
    n.image.colorspace_settings.name='Non-Color';nm=nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(n.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
    m.use_backface_culling=False
    if membrane:
        bs.inputs['Alpha'].default_value=.78
        bs.inputs['Transmission Weight'].default_value=.22
        bs.inputs['Subsurface Weight'].default_value=.12
        bs.inputs['Subsurface Radius'].default_value=(.012,.02,.028)
        m.surface_render_method='DITHERED'
        m['surface_identity']='Living blue-gray veined gill tissue; cloth physics, biological shading'
    return m

BODYMAT=skin_material('M07_Body');GILLMATS=[skin_material(f'M07_Gill_{i:02d}',True) for i in range(1,7)]

def mesh_object(name,vertices,faces,coll,mat,vertex_uv=None,source_normals=None):
    me=bpy.data.meshes.new(name);vertices=np.asarray(vertices,dtype=np.float32);faces=np.asarray(faces,dtype=np.int32)
    me.vertices.add(len(vertices));me.vertices.foreach_set('co',vertices.ravel())
    me.loops.add(faces.size);me.loops.foreach_set('vertex_index',faces.ravel())
    me.polygons.add(len(faces));me.polygons.foreach_set('loop_start',np.arange(len(faces),dtype=np.int32)*3)
    me.polygons.foreach_set('loop_total',np.full(len(faces),3,dtype=np.int32))
    me.polygons.foreach_set('use_smooth',np.ones(len(faces),dtype=bool));me.update()
    if vertex_uv is not None:
        uv=me.uv_layers.new(name='UVMap');uv.data.foreach_set('uv',np.asarray(vertex_uv[faces.ravel()],dtype=np.float32).ravel())
    if source_normals is not None:
        me.normals_split_custom_set_from_vertices(source_normals.tolist())
    o=bpy.data.objects.new(name,me);coll.objects.link(o);me.materials.append(mat);return o

parts=[]
for i in range(7):
    f=triangles[face_labels==i];used,inverse=np.unique(f.ravel(),return_inverse=True)
    normals=source['normals'][used];normals=np.c_[normals[:,0],-normals[:,2],normals[:,1]]
    o=mesh_object('M07_SourceIdentityBody' if i==0 else f'M07_GillDisplay_{i:02d}',points[used],inverse.reshape(-1,3),
                  VISIBLE,BODYMAT if i==0 else GILLMATS[i-1],uvs[used],normals)
    o['source_face_region']=i;o['source_uv_preserved']=True;o['semantic_seams_user_accepted']=False
    parts.append(o)
print('Saved seven source-preserving display partitions in memory',flush=True)

# Use a complete anatomical source, preserving body/hand/foot continuity. The
# supplied sensory head and all exposed Meshy identity remain on the display mesh.
DONOR=ROOT.parent/'WitchMeshy20260919/Authoring/LayeredV04/Sources/Nurse_SourceSkinWalk.fbx'
before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(DONOR),use_anim=False)
imported=set(bpy.data.objects)-before
donorrig=next(o for o in imported if o.type=='ARMATURE')
donorbody=max((o for o in imported if o.type=='MESH'),key=lambda o:len(o.data.vertices))
donorbody.shape_key_clear();oldrest={b.name:donorrig.matrix_world@b.matrix_local for b in donorrig.data.bones}
oldheads={n:m.translation.copy() for n,m in oldrest.items()}
bm=bmesh.new();bm.from_mesh(donorbody.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=3],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(donorbody.data);bm.free()
baseweights=[]
for v in donorbody.data.vertices:
    baseweights.append({donorbody.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-7})
main=set(joint)
for b in donorrig.data.bones:
    if b.name.startswith(('thumb_','index_','middle_','ring_','pinky_')):main.add(b.name)
parentmap={b.name:b.parent.name if b.parent else None for b in donorrig.data.bones}
def major(n):
    while n not in main and parentmap.get(n):n=parentmap[n]
    return n if n in main else 'pelvis'
nextbone={'pelvis':'spine_01','spine_01':'spine_02','spine_02':'spine_03','spine_03':'spine_04',
          'spine_04':'spine_05','spine_05':'neck_01','neck_01':'neck_02','neck_02':'head'}
for side in ['l','r']:
    nextbone.update({'clavicle_'+side:'upperarm_'+side,'upperarm_'+side:'lowerarm_'+side,
                     'lowerarm_'+side:'hand_'+side,'thigh_'+side:'calf_'+side,
                     'calf_'+side:'foot_'+side,'foot_'+side:'ball_'+side})
deltas={};newrest={}
for n in joint:
    src=oldrest[n];srcp=oldheads[n];dst=joint[n]
    nxt=nextbone.get(n)
    if nxt:
        sv=oldheads[nxt]-srcp;tv=joint[nxt]-dst
        rotation=sv.normalized().rotation_difference(tv.normalized()).to_matrix().to_4x4()
        stretch=tv.length/max(sv.length,1e-8)
    else:
        rotation=Matrix.Identity(4);stretch=scale if n=='head' else 1.6
    # Body width follows the existing source silhouette; segment length is
    # authored independently of the retained bone coordinate-frame orientation.
    R=rotation@src.to_quaternion().to_matrix().to_4x4();R.translation=dst
    newrest[n]=R
    A=Matrix.Identity(4)
    for axis in range(3):A[axis][axis]=stretch
    deltas[n]=Matrix.Translation(dst)@rotation@A@Matrix.Translation(-srcp)
for n in main-joint.keys():
    ancestor=major(parentmap.get(n) or 'pelvis')
    if ancestor not in deltas:ancestor='hand_l' if n.endswith('_l') else 'hand_r'
    deltas[n]=deltas[ancestor]
    R=deltas[n]@oldrest[n];newrest[n]=R.normalized()
    newrest[n].translation=R.translation

arm=bpy.data.armatures.new('M07_HumanoidAndGills');rig=bpy.data.objects.new('root',arm);VISIBLE.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for n in sorted(main):
    eb=arm.edit_bones.new(n);eb.matrix=newrest[n]
    eb.length=max(.012,(oldrest[n].to_scale().length/1.732)*.06)
for n in sorted(main):
    par=parentmap.get(n)
    if par:arm.edit_bones[n].parent=arm.edit_bones[major(par)]
gillbones={}
for entry in cloth['panels']:
    i=int(entry['id']);top=Vector(entry['root_world_m']);tip=Vector(entry['tip_world_m'])
    chain=[]
    for j in range(3):
        n=f'gill_{i:02d}_{j:02d}';eb=arm.edit_bones.new(n)
        eb.head=top.lerp(tip,j/3);eb.tail=top.lerp(tip,(j+1)/3)
        if (eb.tail-eb.head).length<.01:eb.tail=eb.head+Vector((0,0,-.02))
        eb.parent=arm.edit_bones[chain[-1]] if chain else arm.edit_bones['spine_05'];chain.append(n)
    gillbones[i]=chain
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)

def assign_quantised(o,names,indices,weights):
    o.vertex_groups.clear();groups={name:o.vertex_groups.new(name=name) for name in names}
    q=np.rint(weights*128).astype(np.int16);q[:,0]+=128-q.sum(axis=1)
    for col in range(indices.shape[1]):
        for bone in np.unique(indices[:,col]):
            mask=indices[:,col]==bone
            for value in np.unique(q[mask,col]):
                if value<=0:continue
                selected=np.flatnonzero(mask&(q[:,col]==value)).tolist()
                groups[names[int(bone)]].add(selected,float(value)/128,'ADD')

def bind(o):
    o.parent=rig;o.matrix_parent_inverse=Matrix.Identity(4)
    mod=o.modifiers.new('M07_Armature','ARMATURE');mod.object=rig

# Fit the entire anatomical source using continuous weighted transforms, then
# preserve it as a separate editable source before deriving hidden-surface fills.
mw=donorbody.matrix_world.copy();deformed=[];remapped=[]
for v,ws in zip(donorbody.data.vertices,baseweights):
    mapped={}
    for n,w in ws.items():mapped[major(n)]=mapped.get(major(n),0)+w
    total=sum(mapped.values());p=mw@v.co
    deformed.append(sum((deltas[n]@p*(w/total) for n,w in mapped.items()),Vector()))
    remapped.append(mapped)
for v,p in zip(donorbody.data.vertices,deformed):v.co=p
donorbody.modifiers.clear();donorbody.parent=None;donorbody.matrix_world=Matrix.Identity(4)
donorbody.name='M07_CompleteAnatomicalBody_Source';move_collection(donorbody,ANATOMY)
donorbody.data.materials.clear();donorbody.data.materials.append(BODYMAT)
for f in donorbody.data.polygons:f.material_index=0
names=sorted(main);nameidx={n:i for i,n in enumerate(names)}
idx=np.zeros((len(remapped),8),dtype=np.int32);wt=np.zeros((len(remapped),8))
for i,ws in enumerate(remapped):
    vals=sorted(ws.items(),key=lambda it:-it[1])[:8];total=sum(v for _,v in vals)
    for j,(n,w) in enumerate(vals):idx[i,j]=nameidx[n];wt[i,j]=w/total
assign_quantised(donorbody,names,idx,wt);bind(donorbody)

bodyids=np.unique(triangles[face_labels==0].ravel());tree=KDTree(len(bodyids))
for i,srcid in enumerate(bodyids):tree.insert(Vector(points[srcid]),int(srcid))
tree.balance();nearest=[];dist=[]
for v in donorbody.data.vertices:
    _,srcid,d=tree.find(v.co);nearest.append(srcid);dist.append(d)
layer=donorbody.data.uv_layers.active or donorbody.data.uv_layers.new(name='UVMap')
for loop in donorbody.data.loops:layer.data[loop.index].uv=uvs[nearest[loop.vertex_index]]
donorbody['whole_anatomy_source']=str(DONOR);donorbody['source_fitting']='Whole-body skin deformation, no transplanted feet or hands'
fill=donorbody.copy();fill.data=donorbody.data.copy();fill.name='M07_HiddenAnatomyFill';VISIBLE.objects.link(fill)
bm=bmesh.new();bm.from_mesh(fill.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if all(dist[v.index]<.045 for v in f.verts)],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(fill.data);bm.free()
donorbody.hide_render=True;donorbody.hide_set(True)
for o in imported:
    if o!=donorbody:bpy.data.objects.remove(o,do_unlink=True)

def segment_weights(o):
    p=np.array([v.co[:] for v in o.data.vertices])
    segments=[]
    for n in names:
        a=arm.bones[n].head_local.copy()
        if n in nextbone:b=arm.bones[nextbone[n]].head_local.copy()
        else:
            children=[c for c in arm.bones[n].children if c.name in main]
            b=children[0].head_local.copy() if children else arm.bones[n].tail_local.copy()
        segments.append((np.array(a),np.array(b)))
    distances=np.empty((len(p),len(names)),dtype=np.float32)
    for j,(a,b) in enumerate(segments):
        ab=b-a;t=np.clip((p-a)@ab/max(float(ab@ab),1e-10),0,1)
        distances[:,j]=np.linalg.norm(p-(a+t[:,None]*ab),axis=1)
    indices=np.argpartition(distances,3,axis=1)[:,:4]
    selected=np.take_along_axis(distances,indices,axis=1)
    weights=1/np.maximum(selected,.015)**4;weights/=weights.sum(axis=1)[:,None]
    assign_quantised(o,names,indices,weights);bind(o)

segment_weights(parts[0]);proxies=[]
for i,o in enumerate(parts[1:],1):
    chain=gillbones[i];top=arm.bones[chain[0]].head_local;tip=arm.bones[chain[-1]].tail_local
    def gill_weights(obj):
        p=np.array([v.co[:] for v in obj.data.vertices]);a=np.array(top);ab=np.array(tip-top)
        t=np.clip((p-a)@ab/max(float(ab@ab),1e-10),0,.99999)*2
        low=np.floor(t).astype(np.int32);high=np.minimum(low+1,2)
        weights=np.c_[1-(t-low),t-low]
        assign_quantised(obj,chain,np.c_[low,high],weights);bind(obj)
    gill_weights(o)
    data=np.load(OUT/f'cloth_proxy_{i:02d}.npz')
    material=bpy.data.materials.new(f'M07_GillSimulationProxy_{i:02d}')
    proxy=mesh_object(f'M07_GillSimulationProxy_{i:02d}',data['positions'],data['triangles'],SIM,material)
    gill_weights(proxy);pin=proxy.vertex_groups.new(name='M07_Pin')
    for j,w in enumerate(data['pin']):
        if w>0:pin.add([j],float(w),'REPLACE')
    colors=proxy.data.color_attributes.new(name='ClothMaxDistance',type='FLOAT_COLOR',domain='POINT')
    colors.data.foreach_set('color',np.c_[data['max_distance_cm']/10,np.zeros((len(data['positions']),2)),np.ones(len(data['positions']))].astype(np.float32).ravel())
    cm=proxy.modifiers.new('M07_Cloth','CLOTH');cm.settings.vertex_group_mass='M07_Pin';cm.settings.mass=.22
    cm.settings.quality=6;cm.settings.air_damping=3;cm.settings.tension_stiffness=18;cm.settings.compression_stiffness=18
    cm.settings.shear_stiffness=12;cm.settings.bending_stiffness=.65
    cm.collision_settings.use_collision=True;cm.collision_settings.distance_min=.012;cm.collision_settings.use_self_collision=False
    # Author Blender passive cloth configuration without stepping simulation.
    cm.show_viewport=False;cm.show_render=False;proxy.hide_render=True;proxy.hide_set(True)
    proxy['simulate_after_review']=True;proxy['display_export_excluded']=True
    proxies.append(proxy)
print('Authored complete anatomy, humanoid/finger rig and six pinned cloth proxies',flush=True)

# Cloth collision capsules are authored from actual skeletal segments in local
# bone coordinates, independent of the outer mantle silhouette.
capsules=[]
for n,nxt,radius in [('pelvis','spine_02',.19),('spine_02','spine_05',.20),('neck_01','head',.13)]+[
        (a+'_'+s,b+'_'+s,r) for s in ['l','r'] for a,b,r in [('upperarm','lowerarm',.09),('lowerarm','hand',.075),('thigh','calf',.11),('calf','foot',.075)]]:
    b=arm.bones[n];inv=b.matrix_local.inverted();a=inv@b.head_local;c=inv@arm.bones[nxt].head_local
    # FBX -> UE right/left handedness conversion is Y reflection.
    capsules.append({'bone':n,'a_cm':[a.x*100,-a.y*100,a.z*100],
                     'b_cm':[c.x*100,-c.y*100,c.z*100],'radius_cm':radius*100})
cloth['collision_capsules']=capsules
for panel in cloth['panels']:
    panel['vertices_cm']=[[p[0],-p[1],p[2]] for p in panel['vertices_cm']]
cloth['coordinate_frame']='FBX/UE reference mesh centimeters; Blender Y reflected'
(OUT/'cloth_ue_manifest.json').write_text(json.dumps(cloth,ensure_ascii=False,indent=2),encoding='utf-8')

# A four-second source breathing loop on dedicated gill chains; humanoid
# locomotion, combat and wall-listening remain separate later work.
scene=bpy.context.scene;scene.render.fps=30;scene.frame_start=1;scene.frame_end=121
rig.animation_data_create();action=bpy.data.actions.new('M07_GillBreathing_Source');rig.animation_data.action=action
for frame in range(1,122,4):
    t=(frame-1)/30
    for i,chain in gillbones.items():
        wave=math.sin(2*math.pi*t/4-(i-1)*.38)-math.sin(-(i-1)*.38)
        for j,n in enumerate(chain):
            pb=rig.pose.bones[n];pb.rotation_mode='XYZ';pb.rotation_euler=(wave*math.radians(1+j*.7),wave*math.radians(.5),0)
            pb.keyframe_insert(data_path='rotation_euler',frame=frame,group=n)
scene.frame_set(1)

def export(name,items,anim=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in [rig,*items]:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(DEL/name),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',
        bake_anim=anim,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS',use_mesh_modifiers=True,path_mode='COPY',embed_textures=False)
display=[*parts,fill]
export('SK_M07_ClothBuildSource.fbx',[*display,*proxies])
export('SK_M07_Display.fbx',display)
export('A_M07_GillBreathing_Source.fbx',[],True)
for o in proxies:o.hide_set(True);o.hide_render=True
donorbody.hide_set(True);donorbody.hide_render=True
for o in display:o.hide_set(False)
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M07_Separated_Master.blend'))
for material in list(bpy.data.materials):
    if material.users==0:bpy.data.materials.remove(material)
for image in list(bpy.data.images):
    if image.users==0:bpy.data.images.remove(image)
    elif image.source=='FILE':
        # Only project-local M07 textures are required by the retained display.
        # Donor library images from another drive never become M07 dependencies.
        path=Path(bpy.path.abspath(image.filepath))
        if path.drive.lower()==OUT.drive.lower():image.filepath=bpy.path.relpath(str(path),start=str(OUT))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M07_Separated_Master.blend'))
record={'stage':'separated source and cloth construction authored, untested',
        'original_source':str(ROOT/'Original/Meshy_AI_Veilwing_07_1001123357_texture.glb'),
        'full_anatomy_source':str(DONOR),'whole_body_source_preserved':True,
        'source_mesh_face_count_preserved':len(triangles),
        'identity_surface_partition':region['method'],'semantic_seams_user_accepted':False,
        'bone_count':len(arm.bones),'body_skin_method':'First-pass smooth four-bone distance weights; anatomical donor preserves normalized source weights',
        'display_parts':[o.name for o in display],
        'gill_proxies':[{'id':e['id'],'vertices':e['vertex_count'],'triangles':e['triangle_count']} for e in cloth['panels']],
        'cloth_scene_configured':True,'blender_display_to_proxy_deformation_bound':False,
        'cloth_simulation_played':False,'inter_panel_collision':False,
        'breathing_source_seconds':4,'breathing_source_fps':30,
        'ue_imported':False,'tested':False,
        'limitations':['Source region seams and anatomy fit are a first production pass, not user-accepted final geometry.',
                       'Body motion retargeting, final grip/finger weighting, UE tissue material tuning, gameplay and F6 remain later stages.']}
(OUT/'authoring_delivery.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'saved':str(OUT/'M07_Separated_Master.blend'),'exports':[str(p) for p in DEL.glob('*.fbx')],'tested':False}),flush=True)
