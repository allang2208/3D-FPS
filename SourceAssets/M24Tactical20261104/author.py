"""Fit the common devices to the M24 advanced chassis' authored right rail."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent;X=O/'Exports';X.mkdir(exist_ok=True)
D=json.loads((O/'current_sources.json').read_text())
SHIFT=Vector((.045,.532,.120));ROT=Matrix.Rotation(math.pi/2,4,'Z')
R={'devices':{},'mount':'Advanced chassis right forward dovetail rail','source_shift_blender_m':list(SHIFT),'runtime_tested':False}
bpy.context.preferences.filepaths.save_version=0

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]

def finish(ob,body):
    select([ob]);bevel=ob.modifiers.new('Machined edge radius','BEVEL');bevel.width=.00015;bevel.segments=3
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for i in range(max(1,len(body.data.uv_layers))):
        uv=ob.data.uv_layers.new(name=body.data.uv_layers[i].name if i<len(body.data.uv_layers) else 'UVMap')
        for face in ob.data.polygons:
            axis=max(range(3),key=lambda j:abs(face.normal[j]));axes=[j for j in range(3) if j!=axis]
            for li in face.loop_indices:
                v=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/.04+.5,v[axes[1]]/.04+.5)
    return ob

def bearing(body):
    # Inner faces follow the real six-point rail section; the open back clears
    # the carrier. Top and bottom lips retain the rail instead of a floating pad.
    profile=[(.0308,.111),(.032,.1088),(.043,.1088),(.043,.1312),(.032,.1312),(.0308,.129),(.032,.129),(.0362,.127),(.0362,.113),(.032,.111)]
    n=len(profile);verts=[(x,y,z) for y in (.513,.551) for x,z in profile]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh=bpy.data.meshes.new('Closed M24 dovetail clamp');mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    ob=bpy.data.objects.new('M24 fitted dovetail bearing',mesh);bpy.context.collection.objects.link(ob)
    mat=bpy.data.materials.new('M24_Tactical_Bearing');mesh.materials.append(mat)
    parts=[finish(ob,body)]
    # Positive stop occupies an actual 4.2 mm rail gap (between teeth 3 and 4).
    bpy.ops.mesh.primitive_cube_add(size=1,location=(.0345,.5308,.120))
    lug=bpy.context.object;lug.name='M24 cross-slot recoil lug';lug.dimensions=(.005,.003,.012)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);lug.data.materials.append(mat);parts.append(finish(lug,body))
    for y in (.520,.544):
        bpy.ops.mesh.primitive_cylinder_add(vertices=6,radius=.0015,depth=.0012,location=(.0385,y,.1315))
        screw=bpy.context.object;screw.name='M24 clamp hex fastener';screw.data.materials.append(mat);parts.append(finish(screw,body))
    return parts

for kind in ('laser','flashlight','blessed_laser'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    src=D['meshes'][kind]
    bpy.ops.import_scene.fbx(filepath=src['fbx'],use_custom_normals=True)
    obs=[ob for ob in bpy.context.scene.objects if ob.type=='MESH']
    for ob in obs:
        m=ob.matrix_world.copy();ob.parent=None;ob.data.transform(m);ob.matrix_world=Matrix.Identity(4)
    select(obs)
    if len(obs)>1:bpy.ops.object.join()
    body=bpy.context.object;body.name='SM_'+kind
    body.data.transform(Matrix.Translation(SHIFT)@ROT)
    for ob in list(bpy.context.scene.objects):
        if ob!=body:bpy.data.objects.remove(ob,do_unlink=True)
    parts=bearing(body);select(parts+[body]);bpy.ops.object.join()
    sockets={}
    for label,position in src['sockets'].items():
        p=Vector((position[0]/100,-position[1]/100,position[2]/100));p=SHIFT+ROT.to_3x3()@p
        sockets[label]=[p.x*100,-p.y*100,p.z*100]
        ob=bpy.data.objects.new('SOCKET_'+label,None);bpy.context.collection.objects.link(ob);ob.parent=body;ob.location=p;ob.select_set(True)
    bpy.context.view_layer.objects.active=body
    tri=body.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    fbx=X/(body.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(X/(body.name+'_Editable.blend')))
    R['devices'][kind]={'source':src['path'],'fbx':str(fbx),'sockets':sockets,'slots':[m.name for m in body.data.materials],'triangles':len(body.data.polygons)}
    print('M24_TACTICAL_AUTHORED',kind,flush=True)
(O/'authoring.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
