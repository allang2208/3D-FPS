"""Fit cloth in rest space against sampled skinned poses; keep each binding fixed."""
from pathlib import Path
import bpy, numpy as np, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/RigRepairV3')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'BoundCongregate_RigV3.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE');body=bpy.data.objects['BC_Flesh']
names=[b.name for b in rig.data.bones];restinv={b.name:b.matrix_local.inverted() for b in rig.data.bones}
cloth=[o for o in scene.objects if o.type=='MESH' and o.name.startswith(('BC_LeftTornRobe','BC_RightLining','BC_DonorSleeve')) and not o.hide_render]
frames=[(None,1)]
for role in ('Idle','Walk','TurnLeft','TurnRight','Bite','Hit','Death'):
    a=bpy.data.actions['A_BoundCongregate_'+role+('V2' if role in ('Walk','TurnLeft','TurnRight') else 'V3')]
    frames.extend((a,f) for f in sorted(set(range(1,round(a.frame_range[1])+1,6))|{round(a.frame_range[1])}))
surfaces=[]
for action,f in frames:
    rig.animation_data.action=action
    if action is None:
        for pb in rig.pose.bones:pb.matrix_basis.identity()
    scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    bvh=BVHTree.FromPolygons([v.co[:] for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons]);evaluated.to_mesh_clear()
    palette=np.array([np.array(rig.pose.bones[n].matrix@restinv[n]) for n in names])
    surfaces.append((action.name if action else 'rest',float(f),bvh,palette))
report={}
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis.identity()
bpy.context.view_layer.update()
for ob in cloth:
    # Render shells and proxies have the same exterior vertex order. Move the
    # complete solid shell by its exterior displacement to preserve thickness.
    proxy=bpy.data.objects[ob.name+'_SimulationProxy'];count=len(proxy.data.vertices)
    original=np.array([v.co[:] for v in proxy.data.vertices]);points=original.copy()
    weights=np.zeros((count,len(names)))
    for v in proxy.data.vertices:
        for g in v.groups:
            name=proxy.vertex_groups[g.group].name
            if name in names:weights[v.index,names.index(name)]=g.weight
    mappings=[np.einsum('vn,nab->vab',weights,palette) for _,_,_,palette in surfaces]
    inverses=[np.linalg.inv(m[:,:3,:3]) for m in mappings]
    for iteration in range(12):
        changed=0;worst=0.
        for (_,_,bvh,_),m,inv in zip(surfaces,mappings,inverses):
            posed=np.einsum('vab,vb->va',m[:,:3,:3],points)+m[:,:3,3]
            for i,p in enumerate(posed):
                hit,normal,_,_=bvh.find_nearest(Vector(p));gap=(Vector(p)-hit).dot(normal)
                if gap>=.022:continue
                push=np.array(normal)*(.025-gap)
                # Surface normal projection can be trapped between adjoining
                # donor limbs. Late passes let the side robe clear that crevice.
                if iteration>=6 and ob.name in ('BC_LeftTornRobe','BC_RightLining'):
                    direction=Vector((-1 if ob.name=='BC_LeftTornRobe' else 1,0,0))
                    hit2,_,_,_=bvh.ray_cast(Vector(p)+direction*2,-direction,4)
                    if hit2 is not None:push=np.array(hit2+direction*.03)-p
                delta=inv[i]@push;length=np.linalg.norm(delta)
                if length>.07:delta*=.07/length
                points[i]+=delta;changed+=1;worst=max(worst,.025-gap)
        print('FIT',ob.name,iteration,changed,round(worst,4),flush=True)
        if changed==0:break
    delta=points-original
    for v,d in zip(proxy.data.vertices,delta):v.co+=Vector(d)
    # Narrow original strips trapped between two independently moving limbs are
    # cut into the ragged hem instead of stretching them into outward spikes.
    remove=set(np.where(np.linalg.norm(delta,axis=1)>.12)[0].tolist()) if 'Sleeve' not in ob.name else set()
    for (_,_,bvh,_),m in zip(surfaces,mappings):
        posed=np.einsum('vab,vb->va',m[:,:3,:3],points)+m[:,:3,3]
        for i,p in enumerate(posed):
            hit,normal,_,_=bvh.find_nearest(Vector(p))
            if (Vector(p)-hit).dot(normal)<.012:remove.add(i)
    import bmesh
    bm=bmesh.new();bm.from_mesh(proxy.data);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.verts[i] for i in remove],context='VERTS')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(proxy.data);bm.free();proxy.data.update()
    material=ob.data.materials[0];ob.data=proxy.data.copy();ob.data.materials[0]=material
    bpy.context.view_layer.objects.active=ob
    if ob.name!='BC_RightLining':
        solid=ob.modifiers.new('RealFabricThickness','SOLIDIFY');solid.thickness=.004;solid.offset=1
        bpy.ops.object.modifier_apply(modifier=solid.name)
    ob.data.update()
    remaining=[i for i in range(count) if i not in remove]
    report[ob.name]=dict(vertices=len(proxy.data.vertices),trimmed_vertices=len(remove),max_rest_adjustment_cm=float(np.linalg.norm(delta[remaining],axis=1).max()*100),samples=len(surfaces))
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis.identity()
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'BoundCongregate_RigV3.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in scene.objects:
    if ob.type in ('MESH','ARMATURE'):ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'SK_BoundCongregate_RigV3.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,
    use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
(ROOT/'cloth_fit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('MOTION_CLOTH_FIT_SAVED',flush=True)
