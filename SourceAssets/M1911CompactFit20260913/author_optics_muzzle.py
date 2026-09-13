"""Resize accepted attachment bodies and rebuild contacts for the M1911 slide/bore."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O=Path(__file__).parent; S=O.parent
bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.open_mainfile(filepath=str(S/'M1911RearRain20260913/M1911_RearFinish_Editable.blend'))
except RuntimeError:
    if 'SK_M1911_Manny' not in bpy.data.objects:raise
rig=bpy.data.objects['SK_M1911_Manny']
root=rig.matrix_world @ rig.data.bones['WPN_root'].matrix_local
slide=bpy.data.objects['M1911_Slide']
slide_surface=BVHTree.FromPolygons([root.inverted() @ slide.matrix_world @ v.co for v in slide.data.vertices],
                                 [list(p.vertices) for p in slide.data.polygons])
bpy.ops.wm.read_factory_settings(use_empty=True)
sources=json.loads((S/'M1911Attachments20260913/sources.json').read_text())['parts']
previous=json.loads((S/'M1911Attachments20260913/authoring.json').read_text())
report={}

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=ob

def finish(ob,width=.0003):
    select(ob)
    modifier=ob.modifiers.new('Machined edge','BEVEL');modifier.width=width;modifier.segments=3
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return ob

def block(name,center,size,material):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center)
    ob=bpy.context.object;ob.name=name;ob.dimensions=size
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);ob.data.materials.append(material)
    return finish(ob)

def mesh_object(name,verts,faces,material):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(material)
    return ob

def coating_uv(ob,index):
    mesh=ob.data
    while len(mesh.uv_layers)<=index:mesh.uv_layers.new(name='UV'+str(len(mesh.uv_layers)))
    uv=mesh.uv_layers[index];uv.name='M1911CoatingPhysicalUV' if index else 'UVMap'
    for face in mesh.polygons:
        axis=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=axis]
        for li in face.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=(p[axes[0]]/.1+.5,p[axes[1]]/.1+.5)

def sight_foot(side,material):
    # Local optic +X is pistol forward, +Y is pistol right. The mount is at
    # WPN_root (0, .030, .0495) metres. Sample the actual curved slide shoulders.
    nx,ny=12,4;top=[];bottom=[]
    for ix in range(nx+1):
        for iy in range(ny+1):
            x=-.014+.028*ix/nx;y=side*(.0075+.0043*iy/ny)
            hit,_,_,_=slide_surface.ray_cast(Vector((y,.030-x,.08)),Vector((0,0,-1)),.07)
            if hit is None:raise RuntimeError('No slide shoulder under optic foot')
            top.append((x,y,-.0015));bottom.append((x,y,hit.z-.0495-.0001))
    count=len(top);faces=[]
    for ix in range(nx):
        for iy in range(ny):
            a=ix*(ny+1)+iy;b=a+1;c=b+ny+1;d=a+ny+1
            faces.extend([(a,b,c,d),(d+count,c+count,b+count,a+count)])
    edge=list(range(ny+1))+[ix*(ny+1)+ny for ix in range(1,nx+1)]+[nx*(ny+1)+iy for iy in range(ny-1,-1,-1)]+[ix*(ny+1) for ix in range(nx-1,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]):faces.append((a,a+count,b+count,b))
    ob=mesh_object('M1911_ContouredSlideFoot',top+bottom,faces,material);coating_uv(ob,0)
    return finish(ob,.00018)

def tube(name,profile,material):
    n=96
    verts=[(r*math.cos(2*math.pi*i/n),y,r*math.sin(2*math.pi*i/n)) for y,r in profile for i in range(n)]
    faces=[(j*n+i,j*n+(i+1)%n,((j+1)%len(profile))*n+(i+1)%n,((j+1)%len(profile))*n+i) for j in range(len(profile)) for i in range(n)]
    ob=mesh_object(name,verts,faces,material)
    bm=bmesh.new();bm.from_mesh(ob.data)
    for face in bm.faces:face.smooth=True
    for edge in bm.edges:edge.smooth=edge.is_manifold and edge.calc_face_angle(0)<.6
    bm.to_mesh(ob.data);bm.free();coating_uv(ob,0)
    return finish(ob,.00015)

for key,info in sources.items():
    before=set(bpy.context.scene.objects);bpy.ops.import_scene.fbx(filepath=info['fbx'])
    obs=[ob for ob in bpy.context.scene.objects if ob not in before and ob.type=='MESH']
    select(obs[0])
    for ob in obs:ob.select_set(True)
    if len(obs)>1:bpy.ops.object.join()
    ob=bpy.context.object;ob.name='M1911_'+key
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    original_slots=[m.name for m in ob.data.materials]
    adapter=bpy.data.materials.get('M1911_AdapterSteel') or bpy.data.materials.new('M1911_AdapterSteel')
    parts=[ob]
    if key=='suppressor':
        # Compact 34 mm exterior / 130.2 mm can. Preserve an open 13 mm passage
        # by remapping radii independently of the exterior size reduction.
        for vertex in ob.data.vertices:
            p=vertex.co;r=math.hypot(p.x,p.z)
            if r>0:
                radius=r*(.0065/.0055) if r<=.0055 else .0065+(r-.0055)*(.017-.0065)/(.024-.0055)
                p.x*=radius/r;p.z*=radius/r
            p.y*=.70
        parts.append(tube('M1911_CompactThreadExtension',[
            (-.0124,.0104),(-.011,.0107),(-.005,.0107),(-.003,.0112),(.001,.0112),(.001,.0065),(-.0124,.0065)],adapter))
        for y in [-.0095,-.007,-.0045]:
            parts.append(tube('M1911_CollarRidge',[(y-.0003,.01065),(y-.00012,.01095),(y+.00012,.01095),(y+.0003,.01065)],adapter))
        sizing={'axial_scale':.70,'outer_diameter_m':.034,'exit_bore_m':.013,'extension_m':.012,
                'mount_root_m':[0,-.16787465,.02898],'muzzle_tip_ue_cm':[0,-13.02,0]}
    else:
        scale=.55 if key=='holographic' else .62
        for vertex in ob.data.vertices:vertex.co*=scale
        parts.append(block('M1911_CompactOpticPlate',(0,0,-.00075),
                           (.056,.031,.0015) if key=='holographic' else (.038,.035,.0015),adapter))
        parts.extend(sight_foot(side,adapter) for side in [-1,1])
        aim=Vector((-.653782,0,5.175324) if key=='holographic' else (2.125,0,3.25))*scale
        sizing={'body_scale':scale,'mount_root_m':[0,.030,.0495],'aim_point_ue_cm':list(aim),
                'contact':'curved slide shoulders; retained rear sight relief; chamber opening forward of base'}
    select(ob)
    for part in parts:part.select_set(True)
    bpy.ops.object.join();coating_uv(ob,previous[key]['uv_index'])
    ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
    sockets={'MountForward':(0,.03,0) if key=='suppressor' else (.03,0,0),'MountUp':(0,0,.03)}
    sockets['Muzzle' if key=='suppressor' else 'AimCenter']=(0,.1302,0) if key=='suppressor' else tuple(aim/100.)
    for name,point in sockets.items():
        socket=bpy.data.objects.new('SOCKET_'+name,None);bpy.context.collection.objects.link(socket)
        socket.parent=ob;socket.location=point;socket.select_set(True)
    folder=O/'FBX';folder.mkdir(exist_ok=True);file=folder/(key+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',
                            bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    coords=[v.co.copy() for v in ob.data.vertices]
    report[key]={'file':str(file),'uv_index':previous[key]['uv_index'],'physical_tile_m':.1,
                 'source_export_slots':original_slots,'export_slots':[m.name for m in ob.data.materials],
                 'bounds_m':{'min':[min(v[i] for v in coords) for i in range(3)],'max':[max(v[i] for v in coords) for i in range(3)]},**sizing}
    # Socket names are per FBX. Free them before the next variant so Blender
    # does not add .001 suffixes which UE would expose as different sockets.
    for child in list(ob.children):
        if child.type=='EMPTY':bpy.data.objects.remove(child,do_unlink=True)
    ob.hide_set(True);ob.hide_render=True
(O/'optics_authoring.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_CompactOptics_Editable.blend'))
print('M1911_COMPACT_OPTICS_AUTHORED',flush=True)
