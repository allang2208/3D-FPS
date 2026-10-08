"""Rebind the continuous right lining to its actual shoulder/root support."""
from pathlib import Path
import bpy, numpy as np, json, heapq
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
OUT=ROOT/'TentacleDynamicsV6';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'TentacleWhipV4/BoundCongregate_TentacleV4.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
if rig.animation_data:rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis.identity()
flesh=bpy.data.objects['BC_Flesh'];flesh.data.calc_loop_triangles()
def smooth(a,b,x):
    t=float(np.clip((x-a)/(b-a),0,1));return t*t*(3-2*t)
def weights(ob,v):return {ob.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-6}
def support(name):
    return name in ('body','body_front','body_rear') or (name.startswith('attack_tentacle_') and int(name.rsplit('_',1)[1])<=12)
fw=[weights(flesh,v) for v in flesh.data.vertices]
positions=[v.co.copy() for v in flesh.data.vertices]
triangles=[tuple(t.vertices) for t in flesh.data.loop_triangles
           if sum(sum(w for n,w in fw[i].items() if support(n)) for i in t.vertices)>2.35
           and sum(positions[i].z for i in t.vertices)>3.2]
tree=BVHTree.FromPolygons(positions,triangles,all_triangles=True)
def binding(point):
    q,normal,index,distance=tree.find_nearest(point)
    ids=triangles[index];a,b,c=[np.asarray(positions[i]) for i in ids]
    matrix=np.column_stack((b-a,c-a));uv=np.linalg.lstsq(matrix,np.asarray(q)-a,rcond=None)[0]
    bary=np.clip([1-uv.sum(),uv[0],uv[1]],0,1);bary/=sum(bary)
    result={}
    for i,t in zip(ids,bary):
        for name,w in fw[i].items():
            if support(name):result[name]=result.get(name,0)+float(t)*w
    total=sum(result.values());result={n:w/total for n,w in result.items()}
    return q,normal,distance,result
def assign(ob,index,values):
    for g in list(ob.data.vertices[index].groups):ob.vertex_groups[g.group].remove([index])
    values=sorted(values.items(),key=lambda x:x[1],reverse=True)[:8]
    total=sum(w for _,w in values)
    for name,w in values:
        if w>1e-5:(ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)).add([index],w/total,'REPLACE')
proxy=bpy.data.objects['BC_RightLining_SimulationProxy']
new_weights=[];changed=0
for v in proxy.data.vertices:
    blend=smooth(1.15,1.56,v.co.z);old=weights(proxy,v)
    if blend<=0:new_weights.append(old);continue
    q,n,d,target=binding(v.co)
    result={name:w*(1-blend) for name,w in old.items()}
    for name,w in target.items():result[name]=result.get(name,0)+w*blend
    new_weights.append(result);changed+=1
    # Refit the attached upper strip. Preserve the authored long/torn lower edge.
    fit=smooth(1.43,1.70,v.co.z)
    if d<.25:v.co=v.co.lerp(q+n*.028,fit)
adj=[[] for v in proxy.data.vertices]
for edge in proxy.data.edges:
    a,b=edge.vertices;distance=(proxy.data.vertices[a].co-proxy.data.vertices[b].co).length
    adj[a].append((b,distance));adj[b].append((a,distance))
# Smooth the transition on the actual cloth graph, leaving the attached top
# exactly surface-bound and retaining donor-leg weights at the existing hem.
for _ in range(5):
    updated=[]
    for i,v in enumerate(proxy.data.vertices):
        strength=.35*(1-smooth(1.5,1.65,v.co.z))*smooth(1.05,1.22,v.co.z)
        if not adj[i] or strength<=0:updated.append(new_weights[i]);continue
        values={n:w*(1-strength) for n,w in new_weights[i].items()}
        for j,_ in adj[i]:
            for n,w in new_weights[j].items():values[n]=values.get(n,0)+w*strength/len(adj[i])
        updated.append(values)
    new_weights=updated
for v,w in zip(proxy.data.vertices,new_weights):assign(proxy,v.index,w)
# A broad supported seam with a geodesic release, shared by render and solver.
distance=np.full(len(proxy.data.vertices),np.inf);queue=[]
for v in proxy.data.vertices:
    if v.co.z>1.70 or (v.co.z>1.46 and v.co.y>.72):
        distance[v.index]=0;heapq.heappush(queue,(0,v.index))
while queue:
    d,i=heapq.heappop(queue)
    if d>distance[i]+1e-8:continue
    for j,length in adj[i]:
        nd=d+length
        if nd<distance[j]:distance[j]=nd;heapq.heappush(queue,(nd,j))
color=proxy.data.color_attributes.get('ClothTravel')
for v in proxy.data.vertices:
    d=distance[v.index]
    travel=.12*smooth(.07,.60,d) if np.isfinite(d) else .02
    # Keep lower close-fitting cloth clear of the moving donor legs.
    travel=min(travel,.045+.075*smooth(.60,1.25,v.co.z))
    color.data[v.index].color=(travel/.45,0,0,1)
proxy.data.update()
render=bpy.data.objects['BC_RightLining']
render.data=proxy.data.copy();render.data.name='BC_RightLining_ContinuousShellV6'
render.data.materials.clear();render.data.materials.append(bpy.data.materials['BC_Lining'])
for group in list(render.vertex_groups):render.vertex_groups.remove(group)
for group in proxy.vertex_groups:render.vertex_groups.new(name=group.name)
for v,w in zip(render.data.vertices,new_weights):assign(render,v.index,w)
# Add a thin outward shell, including rims, to the same continuous support mesh.
bpy.ops.object.select_all(action='DESELECT');render.select_set(True);bpy.context.view_layer.objects.active=render
shell=render.modifiers.new('Lining fabric thickness V6','SOLIDIFY');shell.thickness=.004;shell.offset=1
shell.use_even_offset=True;bpy.ops.object.modifier_apply(modifier=shell.name)
for ob in (render,proxy):
    for polygon in ob.data.polygons:polygon.use_smooth=True
report={'revision':'TentacleDynamicsV6','root_lining_rebound_vertices':changed,
        'proxy_vertices':len(proxy.data.vertices),'visible_vertices':len(render.data.vertices),
        'pinned_proxy_vertices':sum(c.color[0]<1e-6 for c in color.data),
        'root_gap_m':.028,'fabric_thickness_m':.004,'max_free_travel_m':.12,
        'flesh_topology':'V4 continuous welded root retained','tested':False}
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_DynamicsV6.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type in ('MESH','ARMATURE'):o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_BoundCongregate_DynamicsV6.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
(OUT/'authoring.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
