"""Fit the dedicated close-up head to the clothed Meshy biped in centimetres."""
import bpy,bmesh,json,math
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from pathlib import Path
import numpy as np

P=Path(__file__).resolve().parents[4];R=P/'SourceAssets/HillsVillageStable/StablemasterMeshyR3';OUT=R/'Authoring'
OUT.mkdir(exist_ok=True);bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
def import_glb(path):
    before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(path),disable_bone_shape=True)
    return [o for o in bpy.data.objects if o not in before]
source=import_glb(R/'Rig/Rig.glb');rig,=[o for o in source if o.type=='ARMATURE'];body,=[o for o in source if o.type=='MESH']
head,=[o for o in import_glb(R/'Head/Head.glb') if o.type=='MESH']
def coords(ob):
    return np.array([v.co[:] for v in ob.data.vertices])
def rest_world(name):return rig.matrix_world@rig.data.bones[name].head_local
across=rest_world('LeftArm')-rest_world('RightArm');center=(rest_world('LeftFoot')+rest_world('RightFoot'))*.5
world=body.matrix_world.copy();lo=min((world@v.co).z for v in body.data.vertices);hi=max((world@v.co).z for v in body.data.vertices)
center.z=lo
to_cm=Matrix.Scale(168./(hi-lo),4)@Matrix.Rotation(-math.atan2(across.y,across.x),4,'Z')@Matrix.Translation(-center)
def skin_to_rig(ob):
    ob.parent=rig;ob.parent_type='OBJECT';ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
    if not any(m.type=='ARMATURE' and m.object==rig for m in ob.modifiers):
        mod=ob.modifiers.new('Meshy rig','ARMATURE');mod.object=rig
body.data.transform(to_cm@world,shape_keys=True)
rw=rig.matrix_world.copy();rig.parent=None;rig.matrix_world=Matrix.Identity(4);rig.data.transform(to_cm@rw);rig.name='Armature';rig.animation_data_clear()
rig.data.pose_position='REST';skin_to_rig(body);body.name='SK_Stablemaster_Body';body.animation_data_clear()
body.data.materials[0].name='M_Stablemaster_Body_0'
# Fit axial scale to crown/chin landmarks measured on the two generated sculpts.
hm=head.matrix_world.copy();head.parent=None;head.matrix_world=Matrix.Identity(4);head.data.transform(hm,shape_keys=True)
hp=coords(head);bp=coords(body);h=hp[:,2]
scale=(168.-143.8)/((h.max()-h.min())*(1.-13.65/30.))
offset=168.-scale*h.max()
scaled=hp*scale;scaled[:,2]+=offset
xcenter=float(rig.data.bones['Head'].head_local.x)
def nose_tip(pts,cx):
    strip=pts[(abs(pts[:,0]-cx)<2.4)&(pts[:,2]>150.7)&(pts[:,2]<154.9)]
    return np.percentile(strip[strip[:,1]<np.percentile(strip[:,1],5)],50,axis=0)
h_nose=nose_tip(scaled,0.);b_nose=nose_tip(bp,xcenter)
shift=b_nose-h_nose;shift[2]=offset
head.data.transform(Matrix.Translation(Vector(shift))@Matrix.Scale(scale,4),shape_keys=True)
head.name='SK_Stablemaster_Head';head.data.materials[0].name='M_Stablemaster_Head_0'
bridge_mat=bpy.data.materials.new('M_Stablemaster_Neck');head.data.materials.append(bridge_mat)
skin_to_rig(head)
for group in body.vertex_groups:head.vertex_groups.new(name=group.name)
bone_head=head.vertex_groups['Head'].index
hp=coords(head);tree=KDTree(len(bp));body_weights={}
for v in body.data.vertices:
    if v.co.z>135.0:
        tree.insert(v.co,v.index);body_weights[v.index]=[(g.group,g.weight) for g in v.groups]
tree.balance()
for v in head.data.vertices:
    if v.co.z>=147.8:
        head.vertex_groups[bone_head].add([v.index],1.,'REPLACE');continue
    summed={}
    for _,i,dist in tree.find_n(v.co,4):
        for g,w in body_weights[i]:summed[g]=summed.get(g,0.)+w/max(.03,dist)**2
    total=sum(summed.values())
    for g,w in summed.items():head.vertex_groups[g].add([v.index],w/total,'REPLACE')

def uv_projector(ob):
    m=ob.data;m.calc_loop_triangles();uv=m.uv_layers.active
    pts=[v.co.copy() for v in m.vertices];fs=[tuple(t.vertices) for t in m.loop_triangles]
    atlas=[[uv.data[i].uv.copy() for i in t.loops] for t in m.loop_triangles]
    tree=BVHTree.FromPolygons(pts,fs,all_triangles=True)
    def sample(p):
        hit,_,i,_=tree.find_nearest(p)
        a,b,c=[pts[k] for k in fs[i]];v0=b-a;v1=c-a;v2=hit-a
        d00=v0.dot(v0);d01=v0.dot(v1);d11=v1.dot(v1);d20=v2.dot(v0);d21=v2.dot(v1)
        denom=d00*d11-d01*d01
        if abs(denom)<1e-12:return atlas[i][0]
        v=(d11*d20-d01*d21)/denom;w=(d00*d21-d01*d20)/denom
        q,r,s=atlas[i];return q*(1-v-w)+r*v+s*w
    return sample
skin_uv=uv_projector(head);collar_uv=uv_projector(body)
# The linen collar rises towards the nape. These planes pass below chin and bun.
normal=Vector((0.,-.15,1.)).normalized();mid_y=rig.data.bones['neck'].head_local.y
def cut(ob,height,keep_above):
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
    p=Vector((xcenter,mid_y,height))
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=p,plane_no=normal,dist=.00004,clear_inner=False,clear_outer=not keep_above)
    if keep_above:
        # The tips of the tied hair dip below this inclined plane behind the
        # neck. Remove the connected bust below the cut; retain the closed bun.
        remaining={f for f in bm.faces if (f.calc_center_median()-p).dot(normal)<-1e-6}
        drop=[]
        while remaining:
            first=remaining.pop();stack=[first];patch=[first];lowest=first.calc_center_median().z
            while stack:
                face=stack.pop()
                for edge in face.edges:
                    for other in edge.link_faces:
                        if other in remaining:
                            remaining.remove(other);stack.append(other);patch.append(other)
                            lowest=min(lowest,other.calc_center_median().z)
            if lowest<height-6:drop.extend(patch)
        bmesh.ops.delete(bm,geom=drop,context='FACES')
    edges={e for e in bm.edges if e.is_boundary and all(abs((v.co-p).dot(normal))<.001 for v in e.verts)}
    loops=[]
    while edges:
        e=edges.pop();start,end=e.verts;ring=[start]
        while end!=start:
            ring.append(end)
            options=[other for other in end.link_edges if other in edges]
            if len(options)!=1:raise ValueError('Open or branching neck contour on '+ob.name)
            e=options[0];edges.remove(e);end=e.other_vert(end)
        loops.append(ring)
    if len(loops)!=1:
        for ring in loops:
            xyz=np.array([v.co[:] for v in ring]);print('SECTION',ob.name,len(ring),xyz.min(0),xyz.max(0),flush=True)
        raise ValueError(f'{ob.name} has {len(loops)} cut contours at {height}')
    ring=loops[0]
    area=sum(a.co.x*b.co.y-b.co.x*a.co.y for a,b in zip(ring,ring[1:]+ring[:1]))
    if area<0:ring=ring[::-1]
    # Start both loops on the same radial meridian, then stitch by their arc length.
    cx=sum(v.co.x for v in ring)/len(ring);cy=sum(v.co.y for v in ring)/len(ring)
    start=min(range(len(ring)),key=lambda i:abs(math.atan2(ring[i].co.x-cx,cy-ring[i].co.y)))
    return bm,ring[start:]+ring[:start]
bb,lower=cut(body,142.25,False);hb,upper=cut(head,143.4,True)
bd=bb.verts.layers.deform.active;hd=hb.verts.layers.deform.active
bottom=[]
for v in lower:
    nv=hb.verts.new(v.co)
    for g,w in v[bd].items():nv[hd][g]=w
    bottom.append(nv)
def arc(ring):
    ds=np.array([(b.co-a.co).length for a,b in zip(ring,ring[1:]+ring[:1])])
    return np.r_[0,np.cumsum(ds)/ds.sum()]
a=arc(bottom);b=arc(upper);i=j=0;nb,nu=len(bottom),len(upper)
uv0=hb.loops.layers.uv.active;uv1=hb.loops.layers.uv.new('CollarUV');blend=hb.loops.layers.uv.new('HeadMix')
upperset=set(upper)
while i<nb or j<nu:
    v=bottom[i%nb];w=upper[j%nu]
    if j==nu or (i<nb and a[i+1]<=b[j+1]):
        face=hb.faces.new((v,bottom[(i+1)%nb],w));i+=1
    else:
        face=hb.faces.new((v,upper[(j+1)%nu],w));j+=1
    face.material_index=1;face.smooth=True
    for loop in face.loops:
        co=loop.vert.co;loop[uv0].uv=skin_uv(co);loop[uv1].uv=collar_uv(co);loop[blend].uv=(float(loop.vert in upperset),.5)
for bm,ob in [(bb,body),(hb,head)]:
    bm.normal_update();bm.to_mesh(ob.data);bm.free();ob.data.update()
# Keep the editable master and the engine material on the same three UV sets.
bridge_mat.use_nodes=True
nt=bridge_mat.node_tree;nodes=nt.nodes;link=nt.links.new
base=nodes.get('Principled BSDF')
mix=nodes.new('ShaderNodeMixRGB')
for ob,uv_name,slot in [(body,'CollarUV',1),(head,head.data.uv_layers[0].name,2)]:
    src=ob.data.materials[0]
    bs=next(n for n in src.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    src_tex=next(n for n in src.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.colorspace_settings.name=='sRGB')
    tex=nodes.new('ShaderNodeTexImage');tex.image=src_tex.image
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map=uv_name
    link(uv.outputs['UV'],tex.inputs['Vector']);link(tex.outputs['Color'],mix.inputs[slot])
weight=nodes.new('ShaderNodeUVMap');weight.uv_map='HeadMix'
sep=nodes.new('ShaderNodeSeparateXYZ');link(weight.outputs[0],sep.inputs[0])
link(sep.outputs['X'],mix.inputs[0]);link(mix.outputs[0],base.inputs['Base Color'])
rig.data.pose_position='POSE'
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
for ob in list(bpy.context.scene.objects):
    if ob not in (head,body,rig):bpy.data.objects.remove(ob,do_unlink=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StablemasterMeshy.blend'),compress=True)
for ob in (body,head):
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);ob.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/(ob.name+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=False,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='Y',axis_up='Z',use_mesh_modifiers=False,mesh_smooth_type='FACE',path_mode='STRIP',embed_textures=False)
(OUT/'fitting.json').write_text(json.dumps(dict(height_cm=168,head_source='Head/Head.glb',body_source='Rig/Rig.glb',neck_shared_vertices=nb,upper_ring=nu,bones=[v.name for v in rig.data.bones],head_triangles=sum(len(p.vertices)-2 for p in head.data.polygons),body_triangles=sum(len(p.vertices)-2 for p in body.data.polygons)),indent=2))
