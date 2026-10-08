"""Fit supported garments to the same full flesh envelopes used by Chaos."""
from pathlib import Path
import bpy,bmesh,numpy as np,json,heapq
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006');OUT=ROOT/'ClothContactV9';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ClothMotionV8/BoundCongregate_ClothV8.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE');body=bpy.data.objects['BC_Flesh']
rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis.identity()
bpy.context.view_layer.update()
names=[b.name for b in rig.data.bones];indices={n:i for i,n in enumerate(names)};inv={b.name:b.matrix_local.inverted() for b in rig.data.bones}
def weights(ob,v):return {ob.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-6}
def assign(ob,i,values):
    for g in list(ob.data.vertices[i].groups):ob.vertex_groups[g.group].remove([i])
    kept=sorted(values.items(),key=lambda p:p[1],reverse=True)[:8];total=sum(w for _,w in kept)
    for n,w in kept:
        if w>1e-7:(ob.vertex_groups.get(n) or ob.vertex_groups.new(name=n)).add([i],w/total,'REPLACE')
body.data.calc_loop_triangles();triangles=[tuple(t.vertices) for t in body.data.loop_triangles]
flesh=np.array([v.co[:] for v in body.data.vertices]);skin=BVHTree.FromPolygons(flesh.tolist(),triangles,all_triangles=True)
flesh_weights=[weights(body,v) for v in body.data.vertices]
dominant=np.array([indices[max(w,key=w.get)] for w in flesh_weights])
directions=np.array([(x,y,z) for x in (-1,0,1) for y in (-1,0,1) for z in (-1,0,1) if x or y or z])
hulls={}
for n in names:
    if not (n in ('body','body_front','body_rear') or n.startswith('leg_') or n.startswith('attack_tentacle_') and int(n.rsplit('_',1)[1])<=9):continue
    all_points=flesh[dominant==indices[n]]
    if len(all_points)<8:continue
    torso=n in ('body','body_front','body_rear');center=all_points.mean(axis=0)
    for patch in range(4 if torso else 1):
        p=all_points
        if torso:
            keep=((p[:,0]-center[0])*(1 if patch&1 else -1)>=-.08)&((p[:,1]-center[1])*(1 if patch&2 else -1)>=-.08)
            p=p[keep]
        if len(p)<8:continue
        support=p[np.unique(np.argmax(p@directions.T,axis=0))];out=support-p.mean(axis=0)
        support+=out/np.maximum(1e-8,np.linalg.norm(out,axis=1))[:,None]*.02
        bm=bmesh.new();verts=[bm.verts.new(Vector(v)) for v in support]
        bmesh.ops.convex_hull(bm,input=verts,use_existing_faces=False);bm.normal_update()
        patch_center=support.mean(axis=0);planes=[]
        for f in bm.faces:
            normal=np.asarray(f.normal[:]);point=np.asarray(f.verts[0].co[:])
            if np.dot(normal,point-patch_center)<0:normal=-normal
            planes.append(np.r_[normal,-np.dot(normal,point)])
        bm.free();hulls[(n,patch)]=np.array(planes)
samples=[(None,1)]
for role in ('Idle','Walk','TurnLeft','TurnRight','Bite'):
    action=bpy.data.actions['A_BoundCongregate_'+role+('V2' if role in ('Walk','TurnLeft','TurnRight') else 'V3')]
    for phase in (0,.25,.5,.75):samples.append((action,1+phase*(action.frame_range[1]-1)))
surfaces=[]
for action,f in samples:
    rig.animation_data.action=action
    for b in rig.pose.bones:b.matrix_basis.identity()
    if action and len(action.slots):rig.animation_data.action_slot=action.slots[0]
    scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    palette=np.array([np.array(rig.pose.bones[n].matrix@inv[n]) for n in names])
    posed_hulls={}
    for key,planes in hulls.items():
        world=planes@np.linalg.inv(palette[indices[key[0]]]);world/=np.linalg.norm(world[:,:3],axis=1)[:,None];posed_hulls[key]=world
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    tree=BVHTree.FromPolygons([v.co[:] for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons]);evaluated.to_mesh_clear()
    surfaces.append((palette,posed_hulls,tree))
rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis.identity()
bpy.context.view_layer.update()
report={'revision':'V9','source':'ClothV8','gameplay_tested':False,'garments':{}}
for ob in [o for o in scene.objects if o.type=='MESH' and o.name.endswith('_SimulationProxy')]:
    panel='Robe' in ob.name or 'Lining' in ob.name;left='Left' in ob.name or 'Sleeve1_' in ob.name;stem='leg_L2_' if left else 'leg_R4_'
    active=[key for key in hulls if panel or key[0].startswith(stem)]
    # Long triangles can cut across flesh even when their vertices sit outside.
    # Add contact vertices only where the earlier fitting stretched mesh edges.
    bm=bmesh.new();bm.from_mesh(ob.data)
    for _ in range(2):
        long=[e for e in bm.edges if e.calc_length()>.065]
        if not long:break
        bmesh.ops.subdivide_edges(bm,edges=long,cuts=1,use_grid_fill=True)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.update()
    points=np.array([v.co[:] for v in ob.data.vertices]);original=points.copy();count=len(points)
    adj=[[] for _ in points]
    for e in ob.data.edges:
        a,b=e.vertices;adj[a].append(b);adj[b].append(a)
    field=np.zeros((count,len(names)));nearest_gap=np.zeros(count)
    for i,p in enumerate(points):
        q,normal,face,distance=skin.find_nearest(Vector(p));nearest_gap[i]=(Vector(p)-q).dot(normal)
        old=weights(ob,ob.data.vertices[i]);attached={}
        tri=triangles[face];a,b,c=[Vector(flesh[j]) for j in tri]
        bary=barycentric_transform(q,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        bary=np.clip(np.array(bary),0,1);bary/=max(1e-8,bary.sum())
        for j,factor in zip(tri,bary):
            for n,w in flesh_weights[j].items():attached[n]=attached.get(n,0)+w*factor
        # Contact zones follow the actual underlying surface, including its
        # joint blend. Preserve the existing hanging-panel support farther away.
        blend=float(np.clip((p[2]-1.05)/.35,0,1)*np.clip((.14-distance)/.08,0,1)) if panel else .8
        for n,w in old.items():field[i,indices[n]]+=w*(1-blend)
        for n,w in attached.items():field[i,indices[n]]+=w*blend
    for _ in range(10):
        field=np.array([w*.8+np.mean([field[j] for j in adj[i]],axis=0)*.2 if adj[i] else w for i,w in enumerate(field)])
    for i in range(count):assign(ob,i,{n:float(w) for n,w in zip(names,field[i]) if w>1e-6})
    field[:]=0
    for v in ob.data.vertices:
        for n,w in weights(ob,v).items():field[v.index,indices[n]]=w
    mappings=[np.einsum('vn,nab->vab',field,palette) for palette,_,_ in surfaces]
    inverses=[np.linalg.inv(m[:,:3,:3]) for m in mappings]
    # Contact fitting is authoring: solve the cloth shape against the animated
    # flesh plus the exact rigid hulls that the runtime collision will use.
    for iteration in range(22):
        correction=np.zeros_like(points);priority=np.zeros(count)
        for (_,posed_hulls,tree),m,inverse in zip(surfaces,mappings,inverses):
            posed=np.einsum('vab,vb->va',m[:,:3,:3],points)+m[:,:3,3]
            for n in active:
                planes=posed_hulls[n];dist=posed@planes[:,:3].T+planes[:,3]
                face=dist.argmax(axis=1);signed=dist[np.arange(count),face];missing=.040-signed
                take=missing>priority
                if np.any(take):
                    normal=planes[face[take],:3];correction[take]=np.einsum('vab,vb->va',inverse[take],normal)*np.minimum(.025,missing[take])[:,None];priority[take]=missing[take]
            for i,p in enumerate(posed):
                q,normal,_,_=tree.find_nearest(Vector(p));missing=.035-(Vector(p)-q).dot(normal)
                if missing>priority[i]:correction[i]=inverse[i]@np.array(normal)*min(.025,missing);priority[i]=missing
        if priority.max()<.0002:break
        delta=np.array([v*.8+np.mean([correction[j] for j in adj[i]],axis=0)*.2 if adj[i] else v for i,v in enumerate(correction)])
        points+=delta
        if iteration%5==0:print(ob.name,'fit',iteration,flush=True)
    for v,p in zip(ob.data.vertices,points):v.co=Vector(p)
    ob.data.update()
    # Consistent outward winding is necessary for the backstop hemisphere.
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
    facing=0
    for f in bm.faces:
        q,n,_,_=skin.find_nearest(f.calc_center_median());facing+=f.normal.dot(n)*f.calc_area()
    if facing<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(ob.data);bm.free();ob.data.update()
    color=ob.data.color_attributes['ClothTravel'];travel=[]
    for i,p in enumerate(points):
        q,n,_,_=skin.find_nearest(Vector(p));gap=max(0,float((Vector(p)-q).dot(n)))
        previous=float(color.data[i].color[0])*.45
        if panel:
            hem=float(np.clip((1.18-p[2])/.65,0,1))
            # Upper cloth stays on the body; the lower hanging edge keeps its
            # physical movement, limited by the actual space available.
            permitted=min(.012+.075*hem,max(.008,gap*.55))
        else:permitted=min(.014,max(.008,gap*.4))
        amount=min(previous,permitted)
        if panel and p[2]>1.48:amount=0
        c=color.data[i].color;color.data[i].color=(amount/.45,c[1],c[2],1);travel.append(amount)
    visible=bpy.data.objects[ob.name.replace('_SimulationProxy','')];materials=list(visible.data.materials)
    visible.data=ob.data.copy();visible.data.name=visible.name+'_ContactV9';visible.data.materials.clear()
    for mat in materials:visible.data.materials.append(mat)
    for g in list(visible.vertex_groups):visible.vertex_groups.remove(g)
    for g in ob.vertex_groups:visible.vertex_groups.new(name=g.name)
    for v in ob.data.vertices:
        for g in v.groups:visible.vertex_groups[g.group].add([v.index],g.weight,'REPLACE')
    bpy.ops.object.select_all(action='DESELECT');visible.select_set(True);bpy.context.view_layer.objects.active=visible
    shell=visible.modifiers.new('Bounded 4mm shell V9','SOLIDIFY');shell.thickness=.004;shell.offset=1;shell.use_even_offset=False;shell.thickness_clamp=.5
    bpy.ops.object.modifier_apply(modifier=shell.name)
    for p in visible.data.polygons:p.use_smooth=True
    report['garments'][visible.name]={'collider_bones':active,'max_travel_cm':max(travel)*100,'fixed_vertices':sum(t<.0075 for t in travel),'source_vertices':count,'fit_adjustment_max_cm':float(np.linalg.norm(points-original,axis=1).max()*100)}
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_ClothV9.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
    if o.type in ('MESH','ARMATURE'):o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_BoundCongregate_ClothV9.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
