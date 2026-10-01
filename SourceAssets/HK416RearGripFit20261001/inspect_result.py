"""User-requested inspection of the repaired grip seam; no gameplay tests."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.kdtree import KDTree
O=Path(__file__).parent;H=O.parent/'HK416Reworked20260930'
R=Matrix(json.loads((H/'authoring.json').read_text())['root_matrix'])
parts=json.loads((O/'models.json').read_text())['parts']
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(H/'HK416_Gameplay_Editable.blend'),link=False) as (a,b):b.objects=['Lower_body_low','Hand_grip_low','Triger_low']
native=None
for ob in b.objects:
    bpy.context.collection.objects.link(ob);ob.data.transform(R.inverted()@ob.matrix_world)
    ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear();ob.hide_set(False);ob.color=(.2,.23,.24,1)
    ob.hide_render=ob.name=='Hand_grip_low'
    if ob.name=='Hand_grip_low':native=ob
tree=KDTree(len(native.data.vertices))
for i,v in enumerate(native.data.vertices):tree.insert(v.co,i)
tree.balance()
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=1000;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('Inspection world');scene.world.color=(.055,.055,.055)
cd=bpy.data.cameras.new('Seam inspection');cam=bpy.data.objects.new('Seam inspection',cd);scene.collection.objects.link(cam)
scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=.148
report={}
for key,part in parts.items():
    with bpy.data.libraries.load(str(Path(part['file']).with_suffix('.blend')),link=False) as (a,b):b.objects=a.objects
    ob=next(o for o in b.objects if o.type=='MESH');bpy.context.collection.objects.link(ob)
    ob.data.transform(R.inverted()@ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.hide_set(False);ob.hide_render=False;ob.color=(.42,.46,.47,1)
    neck_slot=next(i for i,m in enumerate(ob.data.materials) if m.name.startswith('HK416_InterfaceSteel'))
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=neck_slot],context='FACES')
    distances=[tree.find(v.co)[2] for v in bm.verts if v.link_faces and v.co.z>.01001]
    report[key]={'native_contact_max_delta_m':max(distances),'neck_boundary_edges':sum(e.is_boundary for e in bm.edges),'neck_nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'body_cut_m':part['fit']['body_cut_z_m']}
    bm.free()
    target=Vector((0,.016,-.009))
    for label,offset in [('side',(.4,.10,.06)),('opposite',(-.4,.10,.045))]:
        cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(O/('after_'+key+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
    ob.hide_render=True
(O/'seam_inspection.json').write_text(json.dumps(report,indent=2))
print('HK416_LOCAL_SEAM_INSPECTION',json.dumps(report),flush=True)
