"""Fit the selected Meshy game body to each existing stock mount, then export."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix
P=Path(__file__).resolve().parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P/'CoreStock_Low_Editable.blend'))
low=bpy.data.objects['CoreStock_Game_Body'];base=low.data.copy()
points=np.array([tuple(v.co) for v in base.vertices]);zgrid=np.linspace(points[:,2].min(),points[:,2].max(),200)
rear_profile=[]
for z in zgrid:
    section=points[np.abs(points[:,2]-z)<.0015]
    rear_profile.append(float(section[:,0].max()) if len(section) else .2)
labels=[]
for f in base.polygons:
    rear=float(np.interp(f.center.z,zgrid,rear_profile))
    labels.append(1 if f.center.x>rear-.007 and f.center.x>.15 else 0)
body=base.materials[0].copy();body.name='CoreStockBody'
rubber=body.copy();rubber.name='CoreStockRubber'
bs=next(n for n in rubber.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
for socket,value in [('Metallic',0.),('Roughness',.85)]:
    for link in list(bs.inputs[socket].links):rubber.node_tree.links.remove(link)
    bs.inputs[socket].default_value=value
adapter=bpy.data.materials.new('CoreStockAdapter');adapter.use_nodes=True
bs=next(n for n in adapter.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
bs.inputs['Base Color'].default_value=(.025,.028,.032,1);bs.inputs['Metallic'].default_value=.8;bs.inputs['Roughness'].default_value=.45
report={'source':'CoreStock_Low_Editable.blend','body_length_m':.2,'uv0':'retained source atlas and game normal','uv1':'per-rifle receiver coating','variants':{},'runtime_tested':False}
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o

for family in ['M4','AKM','QBZ191']:
    ob=bpy.data.objects.new('SM_CoreStock',base.copy());bpy.context.collection.objects.link(ob)
    ob.data.materials.clear();ob.data.materials.append(body);ob.data.materials.append(rubber)
    for f,label in zip(ob.data.polygons,labels):f.material_index=label
    leading={'M4':.007,'AKM':.0028,'QBZ191':0.}[family]
    ob.data.transform(Matrix.Translation((leading+.006,0,0)))
    # Short annular collar joins the existing gun tube to the new 40 mm outer socket.
    n=96;xs=[leading,leading+.001,leading+.007,leading+.008]
    outer=[.0137,.014,.0194,.0194];inner=[.0118,.0118,.0156,.0156]
    vertices=[];faces=[]
    for radii in [outer,inner]:
        for x,r in zip(xs,radii):vertices.extend([(x,r*math.cos(i*2*math.pi/n),r*math.sin(i*2*math.pi/n)) for i in range(n)])
    for shell in [0,1]:
        start=shell*len(xs)*n
        for row in range(len(xs)-1):
            for i in range(n):
                j=(i+1)%n;f=(start+row*n+i,start+row*n+j,start+(row+1)*n+j,start+(row+1)*n+i);faces.append(f if shell==0 else tuple(reversed(f)))
    off=len(xs)*n
    for row in [0,len(xs)-1]:
        for i in range(n):
            j=(i+1)%n;f=(row*n+i,off+row*n+i,off+row*n+j,row*n+j);faces.append(f if row==0 else tuple(reversed(f)))
    mesh=bpy.data.meshes.new('CoreStock_MountCollar');mesh.from_pydata(vertices,[],faces);mesh.update()
    ring=bpy.data.objects.new('NewSocket_Transition',mesh);bpy.context.collection.objects.link(ring);parts=[ring]
    for f in ring.data.polygons:f.use_smooth=f.index<2*(len(xs)-1)*n
    def cube(name,loc,size):
        bpy.ops.mesh.primitive_cube_add(size=1,location=loc);a=bpy.context.object;a.name=name;a.dimensions=size;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);parts.append(a);return a
    if family=='AKM':
        a=cube('AKM_receiver_cover',(.0016,0,-.0025),(.005,.041,.038))
        bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.0135,depth=.015,location=(.0016,0,0),rotation=(0,math.pi/2,0));cut=bpy.context.object
        active(a);mod=a.modifiers.new('Tube passage','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
    if family=='QBZ191':
        frame=Matrix.Translation((.000688,.065,.0615))@Matrix.Rotation(math.pi/2,4,'Z');ob.data.transform(frame);ring.data.transform(frame)
        cube('QBZ_receiver_adapter',(.000688,.0585,.0615),(.034,.014,.042))
        cube('QBZ_adapter_shoulder',(.000688,.0645,.0615),(.029,.006,.033))
    for a in parts:
        a.data.materials.clear();a.data.materials.append(adapter);active(a)
        if a!=ring:
            mod=a.modifiers.new('Adapter edge radius','BEVEL');mod.width=.0005;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
        bm=bmesh.new();bm.from_mesh(a.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(a.data);bm.free()
        # New adapter UV0 has valid tangents but never samples the stock normal.
        if not a.data.uv_layers:a.data.uv_layers.new(name='GeneratedUV0')
        a.data.uv_layers[0].name='GeneratedUV0'
        for f in a.data.polygons:
            axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
            for li in f.loop_indices:
                co=a.data.vertices[a.data.loops[li].vertex_index].co;a.data.uv_layers[0].data[li].uv=(co[axes[0]]/.1,co[axes[1]]/.1)
    active(ob)
    for a in parts:a.select_set(True)
    bpy.ops.object.join()
    uv=ob.data.uv_layers.new(name='ReceiverUV1');tile={'M4':(.12,.05),'AKM':(.12,.025),'QBZ191':(.1,.1)}[family]
    for f in ob.data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
        for li in f.loop_indices:
            co=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]/tile[0],co[axes[1]]/tile[1])
    ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
    for o in bpy.context.scene.objects:
        if o!=ob:o.hide_render=True;o.hide_set(True)
    active(ob);out=P/family;out.mkdir(exist_ok=True)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'CoreStock_Game_Editable.blend'))
    bpy.ops.export_scene.fbx(filepath=str(out/'SM_CoreStock.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    report['variants'][family]={'triangles':sum(len(f.vertices)-2 for f in ob.data.polygons),'body_front_m':leading+.006,'adapter_front_m':leading,'asset':'/Game/Weapons/CoreStock20260914/Meshy0914005605/'+family+'/SM_CoreStock'}
    bpy.data.objects.remove(ob,do_unlink=True);print('VARIANT_EXPORTED',family,flush=True)
(P/'variant_authoring.json').write_text(json.dumps(report,indent=2))
