"""Retain the three accepted device bodies; fit a single forward underside seat."""
import bpy, bmesh, json
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

O=Path(__file__).parent
P=O.parents[1]
S=P/'SourceAssets/DualTactical20261008/FitReview'
X=O/'Exports'
X.mkdir(exist_ok=True)
entries=json.loads((S/'Repaired/manifest.json').read_text())
host=json.loads((S/'Cache/Super90-host.json').read_text())
# Native Blender metres: barrel +Y. Runtime UE seat is (0,-32,-84) cm.
seat=Matrix(((0,-1,0,0),(1,0,0,.32),(0,0,1,-.84),(0,0,0,1)))
inv=seat.inverted()
hosttree=BVHTree.FromPolygons([inv@Vector(v) for v in host['vertices']],host['faces'])
bpy.context.preferences.filepaths.save_version=0
report={'seat_ue_cm':[0,-32,-84],'devices':{},'runtime_tested':False}

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs: ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]

def ray(tree,x,y,z,direction):
    return tree.ray_cast(Vector((x,y,z)),Vector((0,0,direction)),.35)[0]

for kind in ('laser','flashlight','blessed_laser'):
    key='Super90-'+kind+'-1'
    e=entries[key]
    bpy.ops.wm.open_mainfile(filepath=str(S/'Repaired'/(key+'.blend')))
    body=next(ob for ob in bpy.context.scene.objects if ob.type=='MESH')
    for ob in list(bpy.context.scene.objects):
        if ob!=body:bpy.data.objects.remove(ob,do_unlink=True)
    # The retained editable assembly is already canonical, with its optic along +X.
    bm=bmesh.new();bm.from_mesh(body.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if body.data.materials[f.material_index].name.startswith('Tactical_Fitted_Bearing')],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    bm.to_mesh(body.data);bm.free()
    body.data.transform(Matrix.Translation((0,0,e['body_outward_mm']/1000)))
    body.name='SM_'+kind
    x0,x1,y0,y1=e['footprint']
    tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],[list(f.vertices) for f in body.data.polygons])
    # Keep a minimum 1.5 mm bearing thickness beneath the actual native fore-end.
    gap=1.
    for x in (x0,(x0+x1)*.5,x1):
        for y in (y0,(y0+y1)*.5,y1):
            top=ray(tree,x,y,.10,-1);target=ray(hosttree,x,y,0,1)
            if top is None or target is None:raise RuntimeError('Missing underside seat for '+kind)
            gap=min(gap,target.z-top.z)
    shift=min(0.,gap-.0015)
    body.data.transform(Matrix.Translation((0,0,shift)))
    tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],[list(f.vertices) for f in body.data.polygons])
    nx,ny=24,12;lower=[];upper=[]
    for ix in range(nx+1):
        for iy in range(ny+1):
            x=x0+(x1-x0)*ix/nx;y=y0+(y1-y0)*iy/ny
            top=ray(tree,x,y,.10,-1);target=ray(hosttree,x,y,0,1)
            if top is None or target is None:raise RuntimeError('Incomplete contact footprint '+kind)
            lower.append((x,y,top.z-.00012));upper.append((x,y,target.z+.00008))
    n=len(lower);faces=[]
    for ix in range(nx):
        for iy in range(ny):
            a=ix*(ny+1)+iy;b=a+1;c=b+ny+1;d=a+ny+1
            faces.extend([(a,b,c,d),(d+n,c+n,b+n,a+n)])
    rim=list(range(ny+1))+[ix*(ny+1)+ny for ix in range(1,nx+1)]+[nx*(ny+1)+iy for iy in range(ny-1,-1,-1)]+[ix*(ny+1) for ix in range(nx-1,0,-1)]
    faces.extend((a,a+n,b+n,b) for a,b in zip(rim,rim[1:]+rim[:1]))
    mesh=bpy.data.meshes.new('Underside contact');mesh.from_pydata(lower+upper,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    pad=bpy.data.objects.new('Closed underside bearing',mesh);bpy.context.collection.objects.link(pad)
    mat=bpy.data.materials.get('Tactical_Fitted_Bearing');mesh.materials.append(mat)
    for name in [v.name for v in body.data.uv_layers] or ['UVMap']:
        layer=mesh.uv_layers.new(name=name)
        for f in mesh.polygons:
            axis=max(range(3),key=lambda a:abs(f.normal[a]));axes=[a for a in range(3) if a!=axis]
            for li in f.loop_indices:
                v=mesh.vertices[mesh.loops[li].vertex_index].co;layer.data[li].uv=(v[axes[0]]/.025,v[axes[1]]/.025)
    select([pad,body]);bpy.ops.object.join()
    select([body]);bpy.ops.object.material_slot_remove_unused()
    tri=body.modifiers.new('Contact triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    sockets={'Emitter':[0,0,shift*100],'AimGuide':[3,0,shift*100]}
    for label,pos in sockets.items():
        ob=bpy.data.objects.new('SOCKET_'+label,None);bpy.context.collection.objects.link(ob)
        ob.parent=body;ob.location=(pos[0]/100,-pos[1]/100,pos[2]/100);ob.select_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(X/(body.name+'_Editable.blend')))
    fbx=X/(body.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    report['devices'][kind]={'fbx':str(fbx),'materials':e['materials'],'sockets':sockets,'source':e['source'],'footprint':e['footprint'],'body_shift_cm':shift*100}
    (O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('UNDERSIDE_AUTHORED '+kind,flush=True)
