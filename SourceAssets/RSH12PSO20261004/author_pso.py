"""Retain the repaired PSO optical assembly, replace its low side foot with a rail shoe."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;OUT=O/'Exports';OUT.mkdir(exist_ok=True)
C=json.loads((O/'inputs.json').read_text())['meshes']['pso1_4x']
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'PSO1Russian20260923/PSO1_PKM_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
for ob in list(bpy.context.scene.objects):
    if ob.name not in ('PSO_ScopeBody','PSO_ScopeLens'):bpy.data.objects.remove(ob,do_unlink=True)
body=bpy.data.objects['PSO_ScopeBody'];lens=bpy.data.objects['PSO_ScopeLens']
mountmat=bpy.data.materials.new('RSH_PSO_MountSteel')
body.data.materials.append(mountmat);cap_slot=len(body.data.materials)-1
# The original integrated side-foot reaches 46 mm below the rail datum.
# Cut only below the optical tube/eyecup; close the new mounting face as steel.
cut_z=.023
bm=bmesh.new();bm.from_mesh(body.data)
cut=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,
    plane_co=(0,0,cut_z),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
edges=[e for e in cut['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
points=[v.co.copy() for e in edges for v in e.verts]
caps=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']
for face in caps:face.material_index=cap_slot
bm.to_mesh(body.data);bm.free()
if not points:raise RuntimeError('No PSO side-foot cut interface')
foot_min=min(p.x for p in points);foot_max=max(p.x for p in points);center_x=(foot_min+foot_max)*.5
axis_y=-C['sockets_cm']['AimCenter'][1]/100
shift=Vector((-center_x,-axis_y,0))
for ob in (body,lens):ob.data.transform(Matrix.Translation(shift))

def finish(ob):
    bpy.context.view_layer.objects.active=ob
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    ob.data.materials.clear();ob.data.materials.append(mountmat)
    bevel=ob.modifiers.new('Machined edges','BEVEL');bevel.width=.00022;bevel.segments=3
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    uv=ob.data.uv_layers.new(name='UV0')
    for f in ob.data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
        for li in f.loop_indices:
            p=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/.04+.5,p[axes[1]]/.04+.5)
    return ob
def extrude(name,x0,x1,section):
    n=len(section);verts=[(x,y,z) for x in (x0,x1) for y,z in section]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);ob.select_set(True);return finish(ob)
def block(name,p,size):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);ob=bpy.context.object;ob.name=name;ob.scale=size;return finish(ob)

# A slotted pedestal holds the newly closed foot, with a full-width bearing roof.
foot_length=foot_max-foot_min
block('PSO bearing roof',(0,0,cut_z-.001),(foot_length+.004,.036,.0024))
for x in (-.026,.026):
    extrude('PSO sloped support',x-.006,x+.006,[(-.009,.002),(.009,.002),(.015,cut_z-.001),(-.015,cut_z-.001)])
block('PSO rail bearing',(0,0,.0015),(.072,.023,.003))
# Match the 20.8 mm crown / 22.8 mm sloped shoulders of the RSH common adapter.
for x in (-.025,.025):
    for sign in (-1,1):
        extrude('PSO split rail jaw',x-.008,x+.008,[(sign*y,z) for y,z in ((.01045,.0001),(.01155,-.0025),(.0079,-.0046),(.014,-.0046),(.0145,.0022),(.0105,.003))])
        bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.0026,depth=.0018,location=(x,sign*.015,-.0005),rotation=(math.pi/2,0,0))
        ob=bpy.context.object;ob.name='PSO clamp screw';finish(ob)
# The 78 mm RSH saddle teeth are centered at -36 + n*10 mm.
for x in (-.021,.019):block('PSO recoil key',(x,0,-.0011),(.0035,.012,.0023))
parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:
    ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
    tri=ob.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.context.view_layer.objects.active=body
file=OUT/'SM_RSH12_PSO1.fbx'
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'RSH12_PSO1_Editable.blend'))
sockets={}
for target,source in [('AimCenter','AimCenter'),('SightRear','AimCenter'),('SightFront','AimFront')]:
    p=C['sockets_cm'][source];sockets[target]=[p[0]+shift.x*100,p[1]-shift.y*100,p[2]]
r=sockets['SightRear'];sockets['SightUp']=[r[0],r[1],r[2]+1]
(O/'authoring.json').write_text(json.dumps(dict(fbx=str(file),sockets_cm=sockets,source=C['source'],source_blend='PSO1Russian20260923/PSO1_PKM_Editable.blend',shift_m=list(shift),foot_cut_z_m=cut_z,foot_bearing_length_m=foot_length,rail_mesh='/Game/Weapons/RSH12/Optics20261004/Meshes/SM_RSH12_Rail_holographic',runtime_tested=False),indent=2))
print('RSH_PSO_AUTHORED',file,foot_length,flush=True)
