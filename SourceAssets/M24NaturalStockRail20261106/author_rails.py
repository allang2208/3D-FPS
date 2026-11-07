"""Native and advanced receiver saddles in the unchanged M24 source frame."""
from pathlib import Path
import bpy,bmesh,numpy as np,json,math
O=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
records={}
for kind in ('native','advanced'):
    xs=np.linspace(-.00865 if kind=='native' else -.00945,.00865 if kind=='native' else .00945,33)
    ys=np.unique(np.r_[np.linspace(.108,.281,60),.1155,.140,.145,.220,.225,.2345,.245])
    verts=[];faces=[];nx=len(xs);ny=len(ys)
    for layer in range(2):
        for y in ys:
            for x in xs:
                if kind=='advanced':
                    z=.13895 if layer else .115+math.sqrt(.0208**2-x*x)-.00025
                    if not layer and x>=.005 and .1155<=y<=.2345:z=max(z,.1355)
                else:
                    rear=.1139+math.sqrt(.01424**2-x*x)-.00035
                    arch=.1147+math.sqrt(.013**2-x*x)+.0002
                    t=max(0,min(1,(y-.140)/.005));t=t*t*(3-2*t)
                    z=rear*(1-t)+arch*t
                    t=max(0,min(1,(y-.220)/.025));t=t*t*(3-2*t)
                    z=z*(1-t)+.1368*t
                    if layer:z=.14198
                verts.append((x,y,z))
    layer=nx*ny
    for j in range(ny-1):
        for i in range(nx-1):
            q=j*nx+i
            faces.extend(((q,q+nx,q+nx+1,q+1),(q+layer,q+1+layer,q+nx+1+layer,q+nx+layer)))
    boundary=list(range(nx))+[j*nx+nx-1 for j in range(1,ny)]+list(range(layer-2,layer-nx-1,-1))+[j*nx for j in range(ny-2,0,-1)]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):faces.append((a,b,b+layer,a+layer))
    me=bpy.data.meshes.new('Fitted rail saddle '+kind);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new('SM_M24_m24_rail_seat_'+kind,me);bpy.context.collection.objects.link(ob)
    mat=bpy.data.materials.new('RailSeat_'+kind);me.materials.append(mat);uv=me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        p.use_smooth=p.index%2==0 and p.index<(nx-1)*(ny-1)*2
        for li in p.loop_indices:
            v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v.x*24+.5,v.y*12)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bevel=ob.modifiers.new('Subtle machined edge','BEVEL');bevel.width=.00016;bevel.segments=2;bevel.limit_method='ANGLE';bevel.angle_limit=.5
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    bpy.ops.export_scene.fbx(filepath=str(O/'Exports'/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',use_tspace=True,add_leaf_bones=False,bake_anim=False,use_triangles=True,mesh_smooth_type='FACE',path_mode='STRIP')
    records[kind]={'path':'/Game/Weapons/M24/RailSeats20261106/Meshes/'+ob.name,'slot':'RailSeat_'+kind,'length_m':.173,'bolt_corridor':'arched underside; existing moving bolt unchanged','scope_transform_changed':False}
    ob.hide_render=kind=='advanced'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_RailSeats.blend'),compress=True)
(O/'rail_construction.json').write_text(json.dumps(records,indent=2))
print('M24_RAIL_SEATS_AUTHORED',records)
