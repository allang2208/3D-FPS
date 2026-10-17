"""Fit the accepted three devices to M870's fixed magazine tube, ahead of the pump."""
import bpy, bmesh, gzip, json, math, os
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).parent; O=Path(os.environ.get('M870_TACTICAL_WORK_DIR',str(ROOT))); P=ROOT.parents[1]; D=P/'SourceAssets/Super90TacticalBottom20261012'
X=O/'Exports'; X.mkdir(exist_ok=True)
data=json.load(gzip.open(O/'host.json.gz','rt'))
inputs=json.loads((O/'inputs.json').read_text())
donors=json.loads((D/'authoring.json').read_text())['devices']
# Component-space UE centimetres; Blender author frame is +X along the barrel.
seat=Matrix(((0,-1,0,0),(1,0,0,.355),(0,0,1,-.805),(0,0,0,1)))
inv=seat.inverted()
vertices=[inv@Vector((p[0]/100,-p[1]/100,p[2]/100)) for p in data['positions']]
gun_materials={i for i,s in enumerate(data['slots']) if 'M_M870_OriginalSurface' in s['material']}
faces=[f for f,m in zip(data['triangles'],data['materials']) if m in gun_materials]
hosttree=BVHTree.FromPolygons(vertices,faces)
report={'input_directory':str(O),'seat_ue_cm':[0,-35.5,-80.5],'attachment_bone':'WPN_root','optical_axis':'+X','devices':{},'runtime_tested':False}
bpy.context.preferences.filepaths.save_version=0

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]

def mesh_object(name,verts,faces,material):
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(material)
    layer=mesh.uv_layers.new(name='UVMap')
    for f in mesh.polygons:
        axis=max(range(3),key=lambda a:abs(f.normal[a]));axes=[a for a in range(3) if a!=axis]
        for li in f.loop_indices:
            v=mesh.vertices[mesh.loops[li].vertex_index].co;layer.data[li].uv=(v[axes[0]]/.025,v[axes[1]]/.025)
    return ob

def upward(tree,x,y):
    p=tree.ray_cast(Vector((x,y,-.15)),Vector((0,0,1)),.35)[0]
    if p is None:raise RuntimeError('No bearing surface at '+str((x,y)))
    return p

# Isolate the tube touched from below. UV seam duplicates are joined by their
# positions only for this authoring query; the saved gun is never changed.
hit=hosttree.ray_cast(Vector((0,0,-.15)),Vector((0,0,1)),.35)
if hit[0] is None:raise RuntimeError('Cannot locate magazine tube')
keys=[tuple(round(c,6) for c in v) for v in vertices];adj={}
for i,f in enumerate(faces):
    for v in f:adj.setdefault(keys[v],[]).append(i)
connected={hit[2]};todo=[hit[2]]
while todo:
    for v in faces[todo.pop()]:
        for i in adj[keys[v]]:
            if i not in connected:connected.add(i);todo.append(i)
tubefaces=[faces[i] for i in connected];tubevertices={v for f in tubefaces for v in f}
center=Vector((0,(min(vertices[v].y for v in tubevertices)+max(vertices[v].y for v in tubevertices))*.5,
    (min(vertices[v].z for v in tubevertices)+max(vertices[v].z for v in tubevertices))*.5))
tubetree=BVHTree.FromPolygons(vertices,tubefaces)
def outer_contact(origin,direction):
    hit=tubetree.ray_cast(origin+direction*.05,-direction,.1)[0]
    if hit is None:raise RuntimeError('Missing outer tube surface')
    return hit

for kind,e in donors.items():
    bpy.ops.wm.open_mainfile(filepath=str(D/'Exports'/('SM_'+kind+'_Editable.blend')))
    body=next(ob for ob in bpy.context.scene.objects if ob.type=='MESH')
    for ob in list(bpy.context.scene.objects):
        if ob!=body:bpy.data.objects.remove(ob,do_unlink=True)
    bm=bmesh.new();bm.from_mesh(body.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if body.data.materials[f.material_index].name.startswith('Tactical_Fitted_Bearing')],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(body.data);bm.free()
    body.name='SM_'+kind
    x0,x1,y0,y1=e['footprint'];offset=-(x0+x1)*.5;x0+=offset;x1+=offset
    body.data.transform(Matrix.Translation((offset,0,0)))
    coat=bpy.data.materials.new('M870_Tactical_Seat')
    coat.diffuse_color=(.025,.025,.025,1)
    parts=[]
    # Two closed half-clamps follow the actual polygonal tube surface. A 0.4 mm
    # seam and two fasteners make a real clamping joint; no decorative spacer.
    width=.036; thickness=.0015; ring_steps=48
    for side in range(2):
        a0=.018+side*math.pi;a1=(side+1)*math.pi-.018
        vs=[]
        for x in (-width*.5,width*.5):
            for outer in (False,True):
                for j in range(ring_steps+1):
                    a=a0+(a1-a0)*j/ring_steps;direction=Vector((0,math.cos(a),math.sin(a)))
                    origin=Vector((x,center.y,center.z));hit=outer_contact(origin,direction)
                    vs.append(hit+direction*(.00006+(thickness if outer else 0)))
        n=ring_steps+1;fs=[]
        for j in range(ring_steps):
            for start,end in ((0,n),(n,3*n),(3*n,2*n),(2*n,0)):
                fs.append((start+j,start+j+1,end+j+1,end+j))
        for j in (0,ring_steps):fs.append((j,n+j,3*n+j,2*n+j))
        parts.append(mesh_object('Magazine clamp '+str(side),vs,fs,coat))
    for side in (-1,1):
        hit=outer_contact(center,Vector((0,side,0)))
        for x in (-.009,.009):
            bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.0023,depth=.0025,
                location=(x,hit.y+side*.0023,center.z),rotation=(math.pi/2,0,0))
            bolt=bpy.context.object;bolt.name='Clamp fastener';bolt.data.materials.append(coat);parts.append(bolt)
    clampverts=[];clampfaces=[]
    for ob in parts[:2]:
        base=len(clampverts);clampverts.extend(v.co for v in ob.data.vertices);clampfaces.extend(tuple(base+i for i in f.vertices) for f in ob.data.polygons)
    clamp=BVHTree.FromPolygons(clampverts,clampfaces)
    tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],[list(f.vertices) for f in body.data.polygons])
    def top(x,y):
        p=tree.ray_cast(Vector((x,y,.10)),Vector((0,0,-1)),.25)[0]
        if p is None:raise RuntimeError('Missing device bearing foot')
        return p
    gap=min(upward(clamp,x,y).z-top(x,y).z for x in (x0,(x0+x1)*.5,x1) for y in (y0,0,y1))
    shift=gap-.0015;body.data.transform(Matrix.Translation((0,0,shift)))
    tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],[list(f.vertices) for f in body.data.polygons])
    nx,ny=24,12;lower=[];upper=[]
    for ix in range(nx+1):
        for iy in range(ny+1):
            x=x0+(x1-x0)*ix/nx;y=y0+(y1-y0)*iy/ny
            lower.append((x,y,top(x,y).z-.00012));upper.append((x,y,upward(clamp,x,y).z+.00008))
    n=len(lower);fs=[]
    for ix in range(nx):
        for iy in range(ny):
            a=ix*(ny+1)+iy;b=a+1;c=b+ny+1;d=a+ny+1;fs.extend(((a,b,c,d),(d+n,c+n,b+n,a+n)))
    rim=list(range(ny+1))+[ix*(ny+1)+ny for ix in range(1,nx+1)]+[nx*(ny+1)+iy for iy in range(ny-1,-1,-1)]+[ix*(ny+1) for ix in range(nx-1,0,-1)]
    fs.extend((a,a+n,b+n,b) for a,b in zip(rim,rim[1:]+rim[:1]))
    parts.append(mesh_object('Closed saddle to device',lower+upper,fs,coat))
    select(parts+[body]);bpy.ops.object.join();select([body]);bpy.ops.object.material_slot_remove_unused()
    tri=body.modifiers.new('Final triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    sockets={name:[pos[0]+offset*100,pos[1],pos[2]+shift*100] for name,pos in e['sockets'].items()}
    for name,pos in sockets.items():
        ob=bpy.data.objects.new('SOCKET_'+name,None);bpy.context.collection.objects.link(ob);ob.parent=body;ob.location=(pos[0]/100,-pos[1]/100,pos[2]/100);ob.select_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(X/(body.name+'_Editable.blend')))
    fbx=X/(body.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    mats=dict(inputs['donors'][kind]['materials']);mats['M870_Tactical_Seat']='/Game/Weapons/M870/Optics20261016/Materials/M_M870_AdapterSteel'
    report['devices'][kind]={'fbx':str(fbx),'materials':mats,'sockets':sockets,'source':inputs['donors'][kind]['path'],'body_shift_cm':[offset*100,0,shift*100],'clamp_width_cm':width*100,'pump_front_cm':29.4902,'clamp_rear_cm':35.5-width*50}
    (O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('M870_TACTICAL_AUTHORED '+kind,flush=True)
