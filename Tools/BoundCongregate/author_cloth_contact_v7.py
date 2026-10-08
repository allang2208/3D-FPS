"""Continuous supported garments, bounded thickness and pose-aware flesh clearance."""
from pathlib import Path
import bpy,bmesh,numpy as np,json,heapq
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006');OUT=ROOT/'ClothContactV7';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'TentacleDynamicsV6/BoundCongregate_DynamicsV6.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');scene=bpy.context.scene
body=bpy.data.objects['BC_Flesh'];names=[b.name for b in rig.data.bones];inv={b.name:b.matrix_local.inverted() for b in rig.data.bones}
proxies=[o for o in scene.objects if o.type=='MESH' and o.name.endswith('_SimulationProxy')]
def smooth(a,b,x):
    t=float(np.clip((x-a)/(b-a),0,1));return t*t*(3-2*t)
def weights(ob,v):return {ob.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-6}
def assign(ob,index,values):
    for g in list(ob.data.vertices[index].groups):ob.vertex_groups[g.group].remove([index])
    values=sorted(values.items(),key=lambda v:v[1],reverse=True)[:8];total=sum(w for _,w in values)
    for name,w in values:
        if w>1e-7:(ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)).add([index],w/total,'REPLACE')
def adjacency(ob):
    result=[[] for _ in ob.data.vertices]
    for e in ob.data.edges:
        a,b=e.vertices;d=(ob.data.vertices[a].co-ob.data.vertices[b].co).length
        result[a].append((b,d));result[b].append((a,d))
    return result
report={'revision':'ClothContactV7','garments':{},'flesh_geometry':'unchanged V4 continuous root','attack_cooldown_seconds':2}
for ob in proxies:
    skirt='Robe' in ob.name or 'Lining' in ob.name
    if skirt:
        bm=bmesh.new();bm.from_mesh(ob.data)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.001)
        bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.0005)
        for _ in range(3):
            long=[e for e in bm.edges if e.calc_length()>.075]
            if not long:break
            bmesh.ops.subdivide_edges(bm,edges=long,cuts=1,use_grid_fill=True)
        bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.update()
        field=np.zeros((len(ob.data.vertices),len(names)))
        for v in ob.data.vertices:
            old=weights(ob,v);attach=smooth(1.18,1.55,v.co.z)
            supported={n:w for n,w in old.items() if n.startswith('attack_tentacle_') and int(n.rsplit('_',1)[1])<=8}
            supported['body']=1-sum(supported.values())
            for n,w in old.items():field[v.index,names.index(n)]+=w*(1-attach)
            for n,w in supported.items():field[v.index,names.index(n)]+=w*attach
        edges=np.array([e.vertices[:] for e in ob.data.edges]);pos=np.array([v.co[:] for v in ob.data.vertices])
        lengths=np.linalg.norm(pos[edges[:,0]]-pos[edges[:,1]],axis=1)
        # Bound weight gradients over physical distance. This keeps the lower
        # drape on its donor anatomy without a binary jump at adjacent legs.
        degree=np.bincount(edges.ravel(),minlength=len(field)).clip(1)
        for _ in range(100):
            diff=field[edges[:,1]]-field[edges[:,0]];jump=np.abs(diff).sum(axis=1)
            allowed=np.maximum(.018,2*lengths/.24)
            correction=diff*(.48*np.maximum(0,1-allowed/np.maximum(jump,1e-8)))[:,None]
            delta=np.zeros_like(field)
            np.add.at(delta,edges[:,0],correction);np.add.at(delta,edges[:,1],-correction)
            field+=delta/degree[:,None]
        for i in range(len(field)):assign(ob,i,{n:float(w) for n,w in zip(names,field[i]) if w>1e-6})
samples=[(None,1)]
for role in ('Idle','Walk','TurnLeft','TurnRight','Bite'):
    action=bpy.data.actions['A_BoundCongregate_'+role+('V2' if role in ('Walk','TurnLeft','TurnRight') else 'V3')]
    for phase in (0,.25,.5,.75):samples.append((action,1+phase*(action.frame_range[1]-1)))
surfaces=[]
for action,f in samples:
    rig.animation_data.action=action
    for pb in rig.pose.bones:pb.matrix_basis.identity()
    if action and len(action.slots):rig.animation_data.action_slot=action.slots[0]
    scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    tree=BVHTree.FromPolygons([v.co[:] for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons]);evaluated.to_mesh_clear()
    palette=np.array([np.array(rig.pose.bones[n].matrix@inv[n]) for n in names]);surfaces.append((tree,palette))
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis.identity()
bpy.context.view_layer.update()
for ob in proxies:
    skirt='Robe' in ob.name or 'Lining' in ob.name;adj=adjacency(ob)
    original=np.array([v.co[:] for v in ob.data.vertices]);points=original.copy();count=len(points)
    w=np.zeros((count,len(names)))
    for v in ob.data.vertices:
        for name,value in weights(ob,v).items():w[v.index,names.index(name)]=value
    mappings=[np.einsum('vn,nab->vab',w,palette) for _,palette in surfaces]
    inverses=[np.linalg.inv(m[:,:3,:3]) for m in mappings]
    for iteration in range(24):
        correction=np.zeros_like(points);worst=np.zeros(count)
        for (tree,_),m,inverse in zip(surfaces,mappings,inverses):
            posed=np.einsum('vab,vb->va',m[:,:3,:3],points)+m[:,:3,3]
            for i,p in enumerate(posed):
                q,n,_,_=tree.find_nearest(Vector(p));missing=.030-(Vector(p)-q).dot(n)
                if missing>worst[i]:worst[i]=missing;correction[i]=inverse[i]@np.asarray(n)*min(missing,.02)
        if worst.max()<.0001:break
        averaged=correction.copy()
        for i,neighbours in enumerate(adj):
            if neighbours:averaged[i]=correction[i]*.65+np.mean([correction[j] for j,_ in neighbours],axis=0)*.35
        points+=averaged
    # Finish the small residual contacts against all sampled tangent planes
    # together. Picking only the worst pose alternates between adjacent limbs.
    for iteration in range(6):
        planes=[];requirements=[]
        for (tree,_),m in zip(surfaces,mappings):
            posed=np.einsum('vab,vb->va',m[:,:3,:3],points)+m[:,:3,3]
            a=np.zeros_like(points);b=np.zeros(count)
            for i,p in enumerate(posed):
                q,n,_,_=tree.find_nearest(Vector(p))
                a[i]=np.asarray(n)@m[i,:3,:3];b[i]=.015-(Vector(p)-q).dot(n)
            planes.append(a);requirements.append(b)
        if max(float(b.max()) for b in requirements)<.0002:break
        delta=np.zeros_like(points)
        for _ in range(8):
            for a,b in zip(planes,requirements):
                missing=np.maximum(0,b-np.einsum('vi,vi->v',a,delta))
                delta+=a*(missing/np.maximum(1e-8,np.einsum('vi,vi->v',a,a)))[:,None]
        delta*=np.minimum(1,.025/np.maximum(1e-8,np.linalg.norm(delta,axis=1)))[:,None]
        points+=delta
    for v,p in zip(ob.data.vertices,points):v.co=Vector(p)
    ob.data.update();adj=adjacency(ob)
    if skirt:
        distance=np.full(count,np.inf);queue=[];top=max(p[2] for p in points)
        for i,p in enumerate(points):
            if p[2]>top-.10 or ('Right' in ob.name and p[2]>1.46 and p[1]>.72):
                distance[i]=0;heapq.heappush(queue,(0,i))
        while queue:
            d,i=heapq.heappop(queue)
            if d>distance[i]+1e-8:continue
            for j,length in adj[i]:
                if d+length<distance[j]:distance[j]=d+length;heapq.heappush(queue,(d+length,j))
        color=ob.data.color_attributes['ClothTravel']
        for i,p in enumerate(points):
            travel=.18*smooth(.08,.75,distance[i]) if np.isfinite(distance[i]) else 0
            travel=min(travel,max(0,float(p[2])-.10))
            color.data[i].color=(travel/.45,0,0,1)
    render=bpy.data.objects[ob.name.replace('_SimulationProxy','')]
    materials=list(render.data.materials);saved_weights=[weights(ob,v) for v in ob.data.vertices]
    render.data=ob.data.copy();render.data.name=render.name+'_ContactShellV7';render.data.materials.clear()
    for mat in materials:render.data.materials.append(mat)
    for group in list(render.vertex_groups):render.vertex_groups.remove(group)
    for group in ob.vertex_groups:render.vertex_groups.new(name=group.name)
    for i,values in enumerate(saved_weights):assign(render,i,values)
    bpy.ops.object.select_all(action='DESELECT');render.select_set(True);bpy.context.view_layer.objects.active=render
    shell=render.modifiers.new('Bounded fabric thickness V7','SOLIDIFY');shell.thickness=.004;shell.offset=1
    # Even-thickness correction divides by the crease angle and creates spikes
    # at folds. Normal offsets keep both layers at the authored 4 mm separation.
    shell.use_even_offset=False;shell.thickness_clamp=.5
    bpy.ops.object.modifier_apply(modifier=shell.name)
    for poly in render.data.polygons:poly.use_smooth=True
    report['garments'][render.name]={'proxy_vertices':count,'visible_vertices':len(render.data.vertices),
        'max_rest_clearance_adjustment_cm':float(np.linalg.norm(points-original,axis=1).max()*100),
        'max_distance_cm':float(max(c.color[0] for c in ob.data.color_attributes['ClothTravel'].data)*45)}
    print(render.name,json.dumps(report['garments'][render.name]),flush=True)
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_ClothV7.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
    if o.type in ('MESH','ARMATURE'):o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_BoundCongregate_ClothV7.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
(OUT/'authoring.json').write_text(json.dumps(report,indent=2))
