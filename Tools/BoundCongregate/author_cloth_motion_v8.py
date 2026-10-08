"""Bridge shallow cloth cavities without moving the contact-fitted shell inward."""
from pathlib import Path
import bpy,numpy as np,heapq,json
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006');OUT=ROOT/'ClothMotionV8';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ClothContactV7/BoundCongregate_ClothV7.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
report={'revision':'V8','source':'ClothV7','garments':{},'tested':False}
for proxy in [o for o in scene.objects if o.type=='MESH' and o.name.endswith('_SimulationProxy')]:
    mesh=proxy.data;count=len(mesh.vertices);points=np.array([v.co[:] for v in mesh.vertices]);old=points.copy()
    neighbors=[[] for _ in range(count)];edge_counts={}
    for p in mesh.polygons:
        for a,b in p.edge_keys:edge_counts[tuple(sorted((a,b)))]=edge_counts.get(tuple(sorted((a,b))),0)+1
    for e in mesh.edges:
        a,b=e.vertices;d=float(np.linalg.norm(points[a]-points[b]));neighbors[a].append((b,d));neighbors[b].append((a,d))
    distances=np.full(count,np.inf);queue=[]
    for (a,b),uses in edge_counts.items():
        if uses==1:
            for i in (a,b):
                if distances[i]!=0:distances[i]=0;heapq.heappush(queue,(0,i))
    while queue:
        d,i=heapq.heappop(queue)
        if d>distances[i]+1e-8:continue
        for j,length in neighbors[i]:
            if d+length<distances[j]:distances[j]=d+length;heapq.heappush(queue,(d+length,j))
    is_panel='Robe' in proxy.name or 'Lining' in proxy.name
    if is_panel:
        normals=np.array([v.normal[:] for v in mesh.vertices]);smooth=points.copy()
        for _ in range(18):
            smooth=np.array([p*.35+np.mean([smooth[j] for j,_ in neighbors[i]],axis=0)*.65 if neighbors[i] else p for i,p in enumerate(smooth)])
        for _ in range(6):
            normals=np.array([n*.5+np.mean([normals[j] for j,_ in neighbors[i]],axis=0)*.5 if neighbors[i] else n for i,n in enumerate(normals)])
        normals/=np.maximum(1e-8,np.linalg.norm(normals,axis=1))[:,None]
        # Fill the valleys of the upper panels; keep their supported peaks,
        # sleeve fit, hem positions and previously repaired skin weights.
        envelope=np.clip(distances/.12,0,1)*np.clip((points[:,2]-.7)/.65,0,1)
        amount=np.clip(np.sum((smooth-points)*normals,axis=1),0,.065)*envelope
        points+=normals*amount[:,None]
        for v,p in zip(mesh.vertices,points):v.co=Vector(p)
        mesh.update()
    color=mesh.color_attributes.get('ClothTravel')
    low,high=float(points[:,2].min()),float(points[:,2].max())
    for i,c in enumerate(color.data):
        # R remains the existing cloth travel map. G/B are appearance only.
        edge=float(np.clip(distances[i]/.1,0,1));hem=float(np.clip(1-(points[i,2]-low)/max(.2,(high-low)*.38),0,1))
        c.color=(c.color[0],edge,hem,1)
    visible=bpy.data.objects[proxy.name.replace('_SimulationProxy','')];materials=list(visible.data.materials)
    visible.data=mesh.copy();visible.data.name=visible.name+'_ClothV8';visible.data.materials.clear()
    for m in materials:visible.data.materials.append(m)
    for g in list(visible.vertex_groups):visible.vertex_groups.remove(g)
    for g in proxy.vertex_groups:visible.vertex_groups.new(name=g.name)
    for v in proxy.data.vertices:
        for g in v.groups:visible.vertex_groups[g.group].add([v.index],g.weight,'REPLACE')
    bpy.ops.object.select_all(action='DESELECT');visible.select_set(True);bpy.context.view_layer.objects.active=visible
    shell=visible.modifiers.new('Normal-offset 4mm cloth V8','SOLIDIFY');shell.thickness=.004;shell.offset=1;shell.use_even_offset=False;shell.thickness_clamp=.5
    bpy.ops.object.modifier_apply(modifier=shell.name)
    for p in visible.data.polygons:p.use_smooth=True
    report['garments'][visible.name]={'proxy_vertices':count,'outward_bridge_max_cm':float(np.linalg.norm(points-old,axis=1).max()*100)}
    print(visible.name,flush=True)
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_ClothV8.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
    if o.type in ('MESH','ARMATURE'):o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_BoundCongregate_ClothV8.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
