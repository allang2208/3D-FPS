"""Adapt the existing optical heads to an independently fitted steel mounting seat."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent;S=P.parent
bpy.ops.wm.open_mainfile(filepath=str(P/'WoodSteelLongbow_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
for im in bpy.data.images:
    p=P/'Textures'/(im.name.split('.')[0]+'.png')
    if p.exists():im.filepath=str(p);im.reload()
info=json.loads((P/'authoring.json').read_text())
names={'SM_WoodSteelLongbow_Optic2x','SM_WoodSteelLongbow_Optic4x'}
for name in names:
    previous=bpy.data.objects.get(name)
    if previous:bpy.data.objects.remove(previous,do_unlink=True)
info['assets']=[row for row in info['assets'] if row['name'] not in names]
body=bpy.data.objects['SK_WoodSteelLongbow_Original']
tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],[list(f.vertices) for f in body.data.polygons])
metal=bpy.data.materials['M_WoodSteelLongbow_Steel']
# Preserve the hunter bow's full-draw hand-to-lens height/lateral clearance.
# The new arrow rest is 3.1 cm farther forward; add that to eye relief below.
shift=Vector((3.1,.123,info['draw_anchor_cm'][2]-1.5))
center=Vector((-3.5,10.1,16.5))+shift

def finish(obj):
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    obj.data.materials.clear();obj.data.materials.append(metal)
    if obj.data.uv_layers.active:obj.data.uv_layers.active.name='UVMap'
    for f in obj.data.polygons:f.use_smooth=True
    obj.select_set(False);return obj
def rod(a,b,r):
    d=b-a;bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=d.length,location=(a+b)*.5)
    o=bpy.context.object;o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized())
    return finish(o)

for power,old in [(2,'SM_Bow_Clearfield2x'),(4,'SM_Bow_Farwatch4x')]:
    with bpy.data.libraries.load(str(S/'BowSingleLensOptics20260927/Bow_SingleLensOptics.blend'),link=False) as (a,b):b.objects=[old]
    obj=b.objects[0];bpy.context.scene.collection.objects.link(obj);obj.data=obj.data.copy();obj.name='SM_WoodSteelLongbow_Optic'+str(power)+'x'
    obj.data.transform(obj.matrix_world);obj.parent=None;obj.matrix_world=Matrix.Identity(4)
    bm=bmesh.new();bm.from_mesh(obj.data)
    remove=[f for f in bm.faces if obj.data.materials[f.material_index].name.startswith(('BracketBowWood','BracketWaxedLinen'))]
    bmesh.ops.delete(bm,geom=remove,context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    bm.to_mesh(obj.data);bm.free()
    for v in obj.data.vertices:v.co+=shift
    # A thin closed saddle follows this bow's actual upper metal socket.
    points=[];faces=[];nx,nz=9,19
    for layer in [0,1]:
        for iz in range(nz):
            z=center.z-2.3+4.6*iz/(nz-1)
            for ix in range(nx):
                x=1.0+1.1*(ix/(nx-1)*2-1)
                hit,_,_,_=tree.ray_cast(Vector((x,12,z)),Vector((0,-1,0)),24)
                if hit is None:raise RuntimeError('Sight seat misses upper socket '+str((x,z)))
                points.append(hit+Vector((0,.015+.22*layer,0)))
    count=nx*nz
    for off in [0,count]:
        for z in range(nz-1):
            for x in range(nx-1):
                i=off+z*nx+x;faces.append((i,i+1,i+1+nx,i+nx))
    border=list(range(nx))+[z*nx+nx-1 for z in range(1,nz)]+list(range(count-2,count-nx-1,-1))+[z*nx for z in range(nz-2,0,-1)]
    for a,b in zip(border,border[1:]+border[:1]):faces.append((a,b,b+count,a+count))
    me=bpy.data.meshes.new('FittedSteelSeat');me.from_pydata(points,[],faces)
    seat=bpy.data.objects.new('FittedSteelSeat',me);bpy.context.scene.collection.objects.link(seat);finish(seat)
    attach,_,_,_=tree.ray_cast(Vector((1,12,center.z)),Vector((0,-1,0)),24)
    a=attach+Vector((0,.12,0));b=center+Vector((.65,-1.7,0));c=center+Vector((0,-1.7,0))
    pieces=[seat,rod(a,b,.23),rod(b,c,.23)]
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    for o in pieces:o.select_set(True)
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
    # Write only the new steel mount corners. Edit-mode selection propagation
    # previously smart-projected the glass too, moving its reticle off centre.
    uv=obj.data.uv_layers.active
    for f in obj.data.polygons:
        if obj.data.materials[f.material_index]!=metal:continue
        for i in f.loop_indices:
            v=obj.data.vertices[obj.data.loops[i].vertex_index].co
            uv.data[i].uv=(v.x*.2,(v.z-center.z)*.2)
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,use_tspace=True)
    info['assets'].append({'name':obj.name,'skeletal':False,'materials':[m.name.split('.')[0] for m in obj.data.materials],
                          'triangles':sum(len(f.vertices)-2 for f in obj.data.polygons)})
    obj.hide_render=True;obj.hide_set(True)
info['optic_aim_center_cm']=[round(center.x,5),round(-center.y,5),round(center.z,5)]
info['optic_eye_distance_cm']=63.1
(P/'authoring.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'WoodSteelLongbow_Editable.blend'))
print('WOOD_STEEL_OPTICS_AUTHORED')
