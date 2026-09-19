"""Fit the repaired low mesh to existing per-rifle stock mounting frames."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P/'SkeletonStock_Game_Low_Editable.blend'))
low=bpy.data.objects['SkeletonStock_Game_Low'];low.hide_set(False)
# Normalize low-mesh data left by decimation before exporting. This performs
# an authoring cleanup of invalid/duplicate primitives, not an acceptance test.
low.data.validate(verbose=True,clean_customdata=False);low.data.update()
base=low.data.copy();verts=[v.co.copy() for v in base.vertices]
# The real opening was restored on x=-0.50099456, about z=.239. No bounds-center
# proxy is used for the stock mount. The body length is an authoring choice.
front=-.5009945631027222;origin=Vector((front,0,.239));factor=.200/(.5009791851043701-front)
for v in base.vertices:v.co=(v.co-origin)*factor
original=[u.uv.copy() for u in base.uv_layers[0].data];bake=[u.uv.copy() for u in base.uv_layers[1].data]
for i,(a,b) in enumerate(zip(original,bake)):base.uv_layers[0].data[i].uv=b;base.uv_layers[1].data[i].uv=a
base.uv_layers[0].name='GameBakeUV0';base.uv_layers[1].name='SourceProjectionUV1'
base.uv_layers.active_index=0;base.uv_layers[0].active_render=True

def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o

def material(kind):
    m=low.data.materials[0].copy();m.name='Stock'+kind
    for n in m.node_tree.nodes:
        if n.type in {'UVMAP','NORMAL_MAP'}:n.uv_map='GameBakeUV0'
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    if kind in {'Polymer','Rubber'}:
        for link in list(bs.inputs['Metallic'].links):m.node_tree.links.remove(link)
        bs.inputs['Metallic'].default_value=0
    if kind=='Rubber':
        for link in list(bs.inputs['Roughness'].links):m.node_tree.links.remove(link)
        bs.inputs['Roughness'].default_value=.82
    if kind=='Adapter':
        for socket in ['Normal','Base Color','Metallic','Roughness']:
            for link in list(bs.inputs[socket].links):m.node_tree.links.remove(link)
        bs.inputs['Base Color'].default_value=(.025,.03,.035,1);bs.inputs['Metallic'].default_value=.8;bs.inputs['Roughness'].default_value=.5
    return m

mats={k:material(k) for k in ['Metal','Polymer','Rubber','Adapter']}
labels=[]
points=np.array([tuple(v.co) for v in low.data.vertices]);zgrid=np.linspace(points[:,2].min(),points[:,2].max(),180)
rear_profile=[]
for z in zgrid:
    sample=points[np.abs(points[:,2]-z)<.006]
    rear_profile.append(float(sample[:,0].max()) if len(sample) else .5)
for f in low.data.polygons:
    c=f.center;x,z=c.x,c.z
    # A slim curved strip follows the source buttpad silhouette. The receiver
    # housing and brace remain separate material identities.
    rear=float(np.interp(z,zgrid,rear_profile))
    rubber=x>rear-.044
    polymer=z>.110 and x<.420
    labels.append(2 if rubber else 1 if polymer else 0)
report={'source':'SkeletonStock_Game_Low_Editable.blend','opening_center_generator':list(origin),'body_length_m':.2,'source_uv_kept':1,'baked_uv':0,'receiver_uv':2,'variants':{},'tested':False,'preview_rendered':False}

for family in ['M4','AKM','QBZ191']:
    ob=bpy.data.objects.new('SM_SkeletonStock',base.copy());bpy.context.collection.objects.link(ob);ob.data.materials.clear()
    for key in ['Metal','Polymer','Rubber','Adapter']:ob.data.materials.append(mats[key])
    for f,label in zip(ob.data.polygons,labels):f.material_index=label
    leading={'M4':.007,'AKM':.0028,'QBZ191':0}[family]
    ob.data.transform(Matrix.Translation((leading+.006,0,0)))
    parts=[]
    # Annular transition: front radius matches the existing gun-side tube,
    # rear radius blends into this candidate's wider, measured front socket.
    n=96;xs=[leading,leading+.001,leading+.008,leading+.009]
    outer=[.0137,.0140,.0214,.0214];inner=[.0118,.0118,.0156,.0156]
    vertices=[]
    for radii in [outer,inner]:
        for x,r in zip(xs,radii):
            vertices.extend([(x,r*math.cos(i*2*math.pi/n),r*math.sin(i*2*math.pi/n)) for i in range(n)])
    faces=[]
    for shell in [0,1]:
        start=shell*len(xs)*n
        for row in range(len(xs)-1):
            for i in range(n):
                j=(i+1)%n;f=(start+row*n+i,start+row*n+j,start+(row+1)*n+j,start+(row+1)*n+i);faces.append(f if shell==0 else tuple(reversed(f)))
    off=len(xs)*n
    for row in [0,len(xs)-1]:
        for i in range(n):
            j=(i+1)%n;f=(row*n+i,off+row*n+i,off+row*n+j,row*n+j);faces.append(f if row==0 else tuple(reversed(f)))
    mesh=bpy.data.meshes.new('Mount_transition');mesh.from_pydata(vertices,[],faces);mesh.update()
    ring=bpy.data.objects.new('Gun_side_annular_transition',mesh);bpy.context.collection.objects.link(ring);parts.append(ring)
    def cube(name,loc,size):
        bpy.ops.mesh.primitive_cube_add(size=1,location=loc);a=bpy.context.object;a.name=name;a.dimensions=size;bpy.ops.object.transform_apply(location=True,rotation=False,scale=True);parts.append(a);return a
    if family=='AKM':
        a=cube('AKM_receiver_cover',(.0016,0,-.0025),(.005,.041,.038))
        bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.0135,depth=.015,location=(.0016,0,0),rotation=(0,math.pi/2,0));cut=bpy.context.object;active(a);mod=a.modifiers.new('Tube passage','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
    if family=='QBZ191':
        # The current QBZ stock assets use pretransformed gun-root metres.
        frame=Matrix.Translation((.000688,.065,.0615))@Matrix.Rotation(math.pi/2,4,'Z')
        ob.data.transform(frame);ring.data.transform(frame)
        cube('QBZ_receiver_adapter',(.000688,.0585,.0615),(.034,.014,.042))
        cube('QBZ_adapter_shoulder',(.000688,.0645,.0615),(.029,.006,.033))
    for a in parts:
        a.data.materials.clear();a.data.materials.append(mats['Adapter']);active(a)
        bm=bmesh.new();bm.from_mesh(a.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(a.data);bm.free()
        if a!=ring:
            mod=a.modifiers.new('Adapter edge radius','BEVEL');mod.width=.0005;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
        for name in ['GameBakeUV0','SourceProjectionUV1']:
            uv=a.data.uv_layers.new(name=name)
            for f in a.data.polygons:
                axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
                for li in f.loop_indices:
                    co=a.data.vertices[a.data.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]/.1,co[axes[1]]/.1)
    active(ob)
    for a in parts:a.select_set(True)
    bpy.ops.object.join()
    ob.data.validate(verbose=True,clean_customdata=False);ob.data.update()
    uv=ob.data.uv_layers.new(name='ReceiverUV2');tile={'M4':(.12,.05),'AKM':(.12,.025),'QBZ191':(.1,.1)}[family]
    for f in ob.data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
        for li in f.loop_indices:
            co=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]/tile[0],co[axes[1]]/tile[1])
    ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
    for o in list(bpy.context.scene.objects):
        if o!=ob:o.hide_render=True;o.hide_set(True)
    active(ob);out=P/family;out.mkdir(exist_ok=True);bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'SkeletonStock_Game_Editable.blend'))
    bpy.ops.export_scene.fbx(filepath=str(out/'SM_SkeletonStock.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    # Per-rifle FBX is the engine delivery; a compact low-model GLB is useful
    # for external editing. It keeps the baked atlas and working materials.
    bpy.ops.export_scene.gltf(filepath=str(out/'SkeletonStock_Game.glb'),use_selection=True,export_apply=True)
    report['variants'][family]={'asset_dir':'/Game/Weapons/ReferenceStock5080/Refined91379/'+family,'body_start_m':leading+.006,'adapter_front_m':leading,'triangles':sum(len(f.vertices)-2 for f in ob.data.polygons),'materials':[m.name for m in ob.data.materials]}
    bpy.data.objects.remove(ob,do_unlink=True);print('VARIANT_EXPORTED',family,flush=True)
(P/'variant_authoring.json').write_text(json.dumps(report,indent=2))
