import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent;OLD=P.parent/'PhantomRearGripIntegration20260913'
family=sys.argv[sys.argv.index('--')+1]
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P/(family+'_Assembly_Editable.blend')))
grip=bpy.data.objects['SM_PhantomRearGrip'];factory=bpy.data.objects['FactoryMountReference']
# Copy the actual factory mating surface, tapering only its lower skirt into the accepted head.
shift={'M4':(-.011,.012),'AKM':(-.005,.012),'QBZ191':(-.010,.011)}[family]
for v in grip.data.vertices:
    t=max(0,min(1,(v.co.z+.045)/.030));t=t*t*(3-2*t)
    v.co.y+=shift[0]*t;v.co.z+=shift[1]*t
    if family=='M4' and v.co.z>.020:
        tail=max(0,min(1,(v.co.y-.008)/.014));v.co.z+=.0045*tail
floor={'M4':.004,'AKM':-.002,'QBZ191':.009}[family]
adapter=factory.copy();adapter.data=factory.data.copy();bpy.context.collection.objects.link(adapter);adapter.name='ReceiverFitCollar';adapter.hide_set(False);adapter.hide_render=False
bm=bmesh.new();bm.from_mesh(adapter.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,floor),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
boundary=[e for e in bm.edges if e.is_boundary];bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(adapter.data);bm.free()
# At the lowest 6 mm the collar narrows toward the generated head, leaving its holes untouched.
head=[v.co for v in grip.data.vertices if floor-.002<v.co.z<floor+.003]
if head:
    ymin=min(p.y for p in head);ymax=max(p.y for p in head);xmin=min(p.x for p in head);xmax=max(p.x for p in head)
    for v in adapter.data.vertices:
        t=max(0,min(1,(floor+.006-v.co.z)/.006));t=t*t*(3-2*t)
        v.co.x=v.co.x*(1-t)+max(xmin+.001,min(xmax-.001,v.co.x))*t
        v.co.y=v.co.y*(1-t)+max(ymin+.001,min(ymax-.001,v.co.y))*t
        if family=='AKM':v.co.y=min(v.co.y,ymax+.002)
# Preserve the accepted grip UV/PBR material; give the new collar its own material slot.
with bpy.data.libraries.load(str(OLD/family/'PhantomRearGrip_Fitted_Editable.blend'),link=False) as (a,b):b.materials=['M_PhantomRearGrip']
grip.data.materials.clear();grip.data.materials.append(b.materials[0])
collar=bpy.data.materials.new('M_PhantomRearGrip_Collar');collar.use_nodes=True
bs=next(n for n in collar.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.014,.017,.019,1);bs.inputs['Metallic'].default_value=.35;bs.inputs['Roughness'].default_value=.48
adapter.data.materials.clear();adapter.data.materials.append(collar)
bpy.ops.object.select_all(action='DESELECT');adapter.select_set(True);bpy.context.view_layer.objects.active=adapter
bev=adapter.modifiers.new('Small mating edge bevel','BEVEL');bev.width=.00035;bev.segments=2
bpy.ops.object.modifier_apply(modifier=bev.name)
bm=bmesh.new();bm.from_mesh(adapter.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update()
uv=bm.loops.layers.uv.verify()
for face in bm.faces:
    axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(face.normal[j]))]
    for loop in face.loops:loop[uv].uv=(loop.vert.co[axes[0]]*10,loop.vert.co[axes[1]]*10)
bm.to_mesh(adapter.data);bm.free()
grip.select_set(True);bpy.context.view_layer.objects.active=grip;bpy.ops.object.join()
for ob in bpy.context.scene.objects:
    if ob.type=='MESH':ob.hide_render=not(ob==grip or ob.name.startswith('Receiver_'))
out=P/family;out.mkdir(exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(out/'SM_PhantomRearGrip.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'PhantomRearGrip_ReceiverFit_Editable.blend'))
print('MOUNT_EXPORTED',family,flush=True)
