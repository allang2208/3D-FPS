"""Reuse accepted tactical devices; author the Super90's curved side seats.

No previews or gameplay tests. Other long-gun mount pivots are derived from
the existing host geometry in its attachment coordinate frame.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;P=O.parents[1];S=P/'SourceAssets'
X=O/'Exports';X.mkdir(exist_ok=True)
auth=json.loads((S/'BlessedLaser20261006/Model/authoring.json').read_text())
ash=json.loads((S/'ASH12TacticalDevices20260920/installed.json').read_text())['parts']
bpy.context.preferences.filepaths.save_version=0
report={'opposite_pivots_cm':{},'super90':{},'game_tested':False}

for family in ('M4','AKM','QBZ191','M16','A762','SVD','PKM','LMG201','HK416'):
    entry=auth[family];e=Vector(entry['emitter_blender_m']);f=Vector(entry['forward_blender'])
    footprints=entry['contact_geometry']['footprints_m']
    along=sum((b[0]+b[1])*.5 for b in footprints)/len(footprints)
    c=e+f*along
    geo=json.loads((S/'BlessedLaser20261006/Model/MountRepair/Hosts'/(family+'-geometry.json')).read_text())
    tree=BVHTree.FromPolygons(geo['vertices'],geo['faces']);centers=[];contacts=[]
    for dy in (-.003,0,.003):
        for dz in (-.003,0,.003):
            a=tree.ray_cast(Vector((.3,c.y+dy,c.z+dz)),Vector((-1,0,0)),.6)[0]
            b=tree.ray_cast(Vector((-.3,c.y+dy,c.z+dz)),Vector((1,0,0)),.6)[0]
            if a is not None and b is not None:
                centers.append((a.x+b.x)*.5);contacts.append([a.x,b.x])
    if not centers:raise RuntimeError('No physical side seat for '+family)
    # The pair of actual lateral surfaces supplies the pivot, independently of
    # inherited sight bones (some converted rigs retain their donor anchors).
    center=sorted(centers)[len(centers)//2]
    report['opposite_pivots_cm'][family]=[center*100,0,c.z*100]
    report.setdefault('host_surface_samples_m',{})[family]=contacts

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]

for kind in ('laser','flashlight','blessed_laser'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source=(S/'BlessedLaser20261006/Model/Exports/SM_BlessedLaser_ASH12.fbx') if kind=='blessed_laser' else Path(ash[kind]['fbx'])
    bpy.ops.import_scene.fbx(filepath=str(source),use_custom_normals=True)
    obs=[ob for ob in bpy.context.scene.objects if ob.type=='MESH']
    for ob in obs:
        matrix=ob.matrix_world.copy();ob.parent=None;ob.data.transform(matrix);ob.matrix_world=Matrix.Identity(4)
    select(obs)
    if len(obs)>1:bpy.ops.object.join()
    body=bpy.context.object;body.name='SM_Super90_'+kind
    # Canonical UE centimetres: +X forward, +Y outboard, +Z up.
    # Native Super90 fore-end ellipse: 21.3 mm lateral / 25 mm vertical.
    # The existing clamp sits 3.5 mm outside the lateral tangent plane.
    zs=[-1.12+i*2.24/16 for i in range(17)]
    profile=[(.10,-1.12),(.10,1.12)]+[(2.13*math.sqrt(1-(z/2.5)**2)-2.48-.012,z) for z in reversed(zs)]
    n=len(profile)
    verts=[(x/100,-y/100,z/100) for x in (-1.85,1.85) for y,z in profile]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh=bpy.data.meshes.new('Super90 closed curved bearing');mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    seat=bpy.data.objects.new('Super90 curved side seat',mesh);bpy.context.collection.objects.link(seat)
    mat=bpy.data.materials.new('Super90_Tactical_Seat');mesh.materials.append(mat)
    select([seat]);bevel=seat.modifiers.new('Machined edge radius','BEVEL');bevel.width=.00015;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name)
    for i in range(max(1,len(body.data.uv_layers))):
        uv=seat.data.uv_layers.new(name=body.data.uv_layers[i].name if i<len(body.data.uv_layers) else 'UVMap')
        for face in seat.data.polygons:
            axis=max(range(3),key=lambda j:abs(face.normal[j]));axes=[j for j in range(3) if j!=axis]
            for li in face.loop_indices:
                v=seat.data.vertices[seat.data.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/.04+.5,v[axes[1]]/.04+.5)
    select([seat,body]);bpy.ops.object.join()
    for ob in list(bpy.context.scene.objects):
        if ob!=body:bpy.data.objects.remove(ob,do_unlink=True)
    sockets=auth['ASH12']['sockets_ue_cm'] if kind=='blessed_laser' else {'Emitter':ash[kind]['emitter_cm'],'AimGuide':ash[kind]['guide_cm']}
    for label,pos in sockets.items():
        ob=bpy.data.objects.new('SOCKET_'+label,None);bpy.context.collection.objects.link(ob);ob.parent=body;ob.location=(pos[0]/100,-pos[1]/100,pos[2]/100);ob.select_set(True)
    tri=body.modifiers.new('Export triangles','TRIANGULATE');bpy.context.view_layer.objects.active=body;bpy.ops.object.modifier_apply(modifier=tri.name)
    path=X/(body.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(X/(body.name+'_Editable.blend')))
    report['super90'][kind]={'source':str(source),'fbx':str(path),'sockets_ue_cm':sockets,'slots':[m.name for m in body.data.materials]}

(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DUAL_TACTICAL_AUTHORED',json.dumps(report['opposite_pivots_cm']),flush=True)
