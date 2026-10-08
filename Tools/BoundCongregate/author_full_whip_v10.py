"""Release the thick appendage's skin while retaining its continuous root seam."""
from pathlib import Path
import bpy,numpy as np,json,heapq
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006');OUT=ROOT/'FullWhipV10';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ClothContactV9/BoundCongregate_ClothV9.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE');body=bpy.data.objects['BC_Flesh']
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
def weights(ob,v):return {ob.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-6}
def assign(ob,i,w):
    for g in list(ob.data.vertices[i].groups):ob.vertex_groups[g.group].remove([i])
    entries=sorted(w.items(),key=lambda p:p[1],reverse=True)[:8];total=sum(v for _,v in entries)
    for name,value in entries:
        if value>1e-7:(ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)).add([i],float(value/total),'REPLACE')
def smooth(a,b,x):
    t=float(np.clip((x-a)/(b-a),0,1));return t*t*(3-2*t)
points=np.array([v.co[:] for v in body.data.vertices]);selected=set();torso=set()
for face in body.data.polygons:
    (selected if body.data.materials[face.material_index].name=='BC_AttackTentacle' else torso).update(face.vertices)
seam=selected&torso;tag=body.data.attributes.get('BCRootJoin')
if tag:seam.update(i for i in selected if tag.data[i].value)
adj={i:[] for i in selected}
for edge in body.data.edges:
    a,b=edge.vertices
    if a in selected and b in selected:
        distance=float(np.linalg.norm(points[a]-points[b]));adj[a].append((b,distance));adj[b].append((a,distance))
distance={i:float('inf') for i in selected};queue=[]
for i in seam:distance[i]=0;heapq.heappush(queue,(0,i))
while queue:
    d,i=heapq.heappop(queue)
    if d>distance[i]+1e-9:continue
    for j,length in adj[i]:
        if d+length<distance[j]:distance[j]=d+length;heapq.heappush(queue,(d+length,j))
nodes=np.array([rig.data.bones[f'attack_tentacle_{i:02d}'].head_local[:] for i in range(57)]+[rig.data.bones['attack_tentacle_56'].tail_local[:]])
segments=np.diff(nodes,axis=0);lengths=np.linalg.norm(segments,axis=1);arc=np.r_[0,np.cumsum(lengths)]
changed=fixed=blended=0
for i in selected:
    # Project only semantically isolated appendage vertices onto its centreline.
    t=np.clip(np.sum((points[i]-nodes[:-1])*segments,axis=1)/(lengths*lengths),0,1)
    nearest=int(np.argmin(np.linalg.norm(nodes[:-1]+segments*t[:,None]-points[i],axis=1)))
    along=arc[nearest]+t[nearest]*lengths[nearest]
    position=along/arc[-1]*57-.5
    ids=np.arange(max(0,int(np.floor(position))-1),min(57,int(np.floor(position))+3))
    values=np.exp(-((ids-position)/.9)**2);values/=values.sum()
    release=0 if i in seam else smooth(.035,.32,distance[i])
    w={'body':1-release}
    for bone,value in zip(ids,values):w[f'attack_tentacle_{bone:02d}']=float(value*release)
    assign(body,i,w);changed+=1;fixed+=release==0;blended+=0<release<1
# The root lining must inherit the newly mobile flesh beneath it; otherwise its
# old fixed shoulder strip would hold still while the appendage moves through it.
body.data.calc_loop_triangles();triangles=[tuple(t.vertices) for t in body.data.loop_triangles]
tree=BVHTree.FromPolygons(points.tolist(),triangles,all_triangles=True)
report={'revision':'FullWhipV10','appendage_vertices':changed,'fixed_seam_vertices':fixed,'gradient_vertices':blended,'cloth_root_weights':{},'geometry':'V9 flesh, cloth, UVs and continuous seam preserved','gameplay_tested':False}
def fit_root_weights(ob):
    changed=0
    for vertex in ob.data.vertices:
        q,n,face,gap=tree.find_nearest(vertex.co)
        if gap>=.16:continue
        ids=triangles[face]
        if not all(i in selected for i in ids):continue
        a,b,c=[Vector(points[i]) for i in ids]
        bary=np.clip(np.array(barycentric_transform(q,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))),0,1);bary/=max(1e-8,bary.sum())
        attached={}
        for i,factor in zip(ids,bary):
            for name,value in weights(body,body.data.vertices[i]).items():attached[name]=attached.get(name,0)+value*factor
        # Never couple clothes to the travelling tip or remote thin strand.
        if any(name.startswith('attack_tentacle_') and int(name.rsplit('_',1)[1])>9 and value>.01 for name,value in attached.items()):continue
        blend=1-smooth(.075,.16,gap);old=weights(ob,vertex);result={name:value*(1-blend) for name,value in old.items()}
        for name,value in attached.items():result[name]=result.get(name,0)+value*blend
        assign(ob,vertex.index,result);changed+=1
    return changed
for proxy in [o for o in scene.objects if o.type=='MESH' and o.name.endswith('_SimulationProxy')]:
    changed=fit_root_weights(proxy);report['cloth_root_weights'][proxy.name]=changed
    if not changed:continue
    visible=bpy.data.objects[proxy.name.replace('_SimulationProxy','')];materials=list(visible.data.materials)
    visible.data=proxy.data.copy();visible.data.materials.clear()
    for m in materials:visible.data.materials.append(m)
    for g in list(visible.vertex_groups):visible.vertex_groups.remove(g)
    for g in proxy.vertex_groups:visible.vertex_groups.new(name=g.name)
    for v in proxy.data.vertices:
        for g in v.groups:visible.vertex_groups[g.group].add([v.index],g.weight,'REPLACE')
    bpy.ops.object.select_all(action='DESELECT');visible.select_set(True);bpy.context.view_layer.objects.active=visible
    shell=visible.modifiers.new('Bounded 4mm cloth V10','SOLIDIFY');shell.thickness=.004;shell.offset=1;shell.use_even_offset=False;shell.thickness_clamp=.5
    bpy.ops.object.modifier_apply(modifier=shell.name)
    for p in visible.data.polygons:p.use_smooth=True
strap=bpy.data.objects.get('BC_ShoulderRestraint')
if strap:report['cloth_root_weights'][strap.name]=fit_root_weights(strap)
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_FullWhipV10.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
    if o.type in ('MESH','ARMATURE'):o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_BoundCongregate_FullWhipV10.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report),flush=True)
