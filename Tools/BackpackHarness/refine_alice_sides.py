"""Open the two ALICE side-pouch mouths with a recessed liner and sewn lips."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path('D:/FPS3D/FPSGAME');SRC=P/'SourceAssets/PortableBackpackAlice20261019'
R=P/'SourceAssets/BackpacksReview20261021';R.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SRC/'AliceBackpack_uv_bevel.blend'))
ob=bpy.data.objects['SM_AliceBackpack'];bpy.context.view_layer.objects.active=ob
lining=bpy.data.materials.new('AlicePocketLining');lining.use_nodes=True
bs=next(n for n in lining.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.018,.021,.014,1);bs.inputs['Roughness'].default_value=.94
ob.data.materials.append(lining)
before=len(ob.data.polygons);details=[]
# Only cut canvas. Straps, leather fasteners and hardware bridge the mouth
# naturally and must not be sliced by the same boolean tool.
protected=ob.copy();protected.data=ob.data.copy();bpy.context.collection.objects.link(protected)
bm=bmesh.new();bm.from_mesh(protected.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==0],context='FACES')
bm.to_mesh(protected.data);bm.free()
bm=bmesh.new();bm.from_mesh(ob.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=0],context='FACES')
bm.to_mesh(ob.data);bm.free();ob.data.update()
original_bvh=BVHTree.FromObject(ob,bpy.context.evaluated_depsgraph_get())
mesh_uv=ob.data.uv_layers.active
old_uv={p.index:[tuple(mesh_uv.data[i].uv) for i in p.loop_indices] for p in ob.data.polygons}
hem_objects=[]
for side in (-1,1):
    # A shallow horizontal mouth under the pouch's existing curved top flap.
    # Its inner end stops within the pouch, before the main bag wall.
    bpy.ops.mesh.primitive_cube_add(size=1,location=(side*.228,-.063,-.015))
    cutter=bpy.context.object;cutter.name='PocketMouthCut';cutter.dimensions=(.100,.102,.0055)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bevel=cutter.modifiers.new('Rounded mouth ends','BEVEL');bevel.width=.0025;bevel.segments=4
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for vertex in cutter.data.vertices:
        y=vertex.co.y+cutter.location.y
        vertex.co.z+=.0025*math.sin(math.pi*(y+.114)/.102)
    # The cut's exposed interior belongs to lining, never a stretched canvas atlas.
    for mat in ob.data.materials:cutter.data.materials.append(mat)
    for face in cutter.data.polygons:face.material_index=4
    bpy.context.view_layer.objects.active=ob
    modifier=ob.modifiers.new('Side pocket mouth','BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    # Rounded binding follows the actual side-pouch surface above/below the slit.
    for upper in (True,False):
        points=[];uvs=[]
        for j in range(49):
            y=-.113+j*.100/48
            z=-.015+.0025*math.sin(math.pi*(y+.114)/.102)+(.0035 if upper else -.0035)
            hit,normal,fi,_=original_bvh.ray_cast(Vector((side*.30,y,z)),Vector((-side,0,0)),.14)
            if hit is None:continue
            points.append(hit+Vector((side*.00045,0,0)))
            coords=old_uv[fi];uvs.append(Vector((sum(p[0] for p in coords)/len(coords),sum(p[1] for p in coords)/len(coords))))
        if len(points)<40:raise RuntimeError('Incomplete side-pouch hem contact')
        verts=[];faces=[];face_uv=[];radius=.0010 if upper else .0008
        for j,point in enumerate(points):
            tangent=(points[min(j+1,len(points)-1)]-points[max(j-1,0)]).normalized()
            outward=Vector((side,0,0));across=tangent.cross(outward).normalized();outward=across.cross(tangent).normalized()
            for k in range(8):verts.append(point+radius*(math.cos(k*math.tau/8)*outward+math.sin(k*math.tau/8)*across))
        for j in range(len(points)-1):
            for k in range(8):
                faces.append([j*8+k,j*8+(k+1)%8,(j+1)*8+(k+1)%8,(j+1)*8+k])
                # Compact unpatterned canvas area with real along/across UV area.
                u,v=uvs[j]
                face_uv.append([(u,v),(u+.0007,v),(u+.0007,v+.001),(u,v+.001)])
        for end,reverse in ((0,True),(len(points)-1,False)):
            ids=[end*8+k for k in range(8)];faces.append(ids[::-1] if reverse else ids)
            u,v=uvs[end]
            coords=[(u+.0003*math.cos(k*math.tau/8),v+.0003*math.sin(k*math.tau/8)) for k in range(8)];face_uv.append(coords[::-1] if reverse else coords)
        me=bpy.data.meshes.new('Sewn side binding');me.from_pydata(verts,[],faces);me.materials.append(ob.data.materials[0]);me.update()
        layer=me.uv_layers.new(name=ob.data.uv_layers.active.name)
        for face,coords in zip(me.polygons,face_uv):
            face.use_smooth=True
            for li,coord in zip(face.loop_indices,coords):layer.data[li].uv=coord
        hem=bpy.data.objects.new('SideBinding',me);bpy.context.collection.objects.link(hem);hem_objects.append(hem)
    details.append(dict(side=side,mouth_width_cm=10.2,mouth_gap_cm=.55,inner_stop_x_cm=17.8))

# A dedicated planar UV on newly exposed lining avoids copying arbitrary atlas
# coordinates from unrelated buckle or canvas faces.
uv=ob.data.uv_layers.active
for face in ob.data.polygons:
    if face.material_index!=4:continue
    axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(face.normal[i]))]
    for li in face.loop_indices:
        v=ob.data.vertices[ob.data.loops[li].vertex_index].co
        uv.data[li].uv=(v[axes[0]]*8,v[axes[1]]*8)

ob.data.update()
bpy.ops.object.select_all(action='DESELECT')
for part in [ob,protected]+hem_objects:part.select_set(True)
bpy.context.view_layer.objects.active=ob;bpy.ops.object.join()
bpy.ops.wm.save_as_mainfile(filepath=str(R/'AliceBackpack_side_openings.blend'))
(R/'alice_side_author.json').write_text(json.dumps(dict(source=str(SRC/'AliceBackpack_uv_bevel.blend'),
    output=str(R/'AliceBackpack_side_openings.blend'),before_faces=before,after_faces=len(ob.data.polygons),
    details=details,materials=[m.name for m in ob.data.materials]),indent=2),encoding='utf-8')
print('ALICE_SIDE_OPENINGS',before,len(ob.data.polygons),flush=True)
