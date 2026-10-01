"""Inspect only the reported HK416 rear-grip interface, in weapon coordinates."""
import bpy, json
from pathlib import Path
from mathutils import Matrix, Vector
O=Path(__file__).parent; S=O.parent; H=S/'HK416Reworked20260930'
R=Matrix(json.loads((H/'authoring.json').read_text())['root_matrix'])
sources=json.loads((S/'M16UniversalAttachments20260920/sources.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
report={}; objects={}

def freeze(ob, transform):
    bpy.context.collection.objects.link(ob)
    ob.data.transform(transform @ ob.matrix_world)
    ob.parent=None; ob.matrix_world=Matrix.Identity(4); ob.modifiers.clear()
    ob.hide_set(False); ob.hide_render=True; ob.data.update()
    return ob

def describe(ob):
    points=[v.co for v in ob.data.vertices]
    slices={}
    for z in [-.035,-.012,-.008,0,.004,.008,.010,.012,.015,.018,.020,.022,.024]:
        hits=[]
        for e in ob.data.edges:
            a,b=[ob.data.vertices[i].co for i in e.vertices]
            if (a.z-z)*(b.z-z)<=0 and abs(b.z-a.z)>1e-9:
                hits.append(a.lerp(b,(z-a.z)/(b.z-a.z)))
        slices[str(z)]={'count':len(hits),'bounds':[[min(p[i] for p in hits),max(p[i] for p in hits)] for i in range(2)]} if hits else None
    return {'bounds':[[min(v[i] for v in points),max(v[i] for v in points)] for i in range(3)],'slices':slices,'materials':[m.name for m in ob.data.materials]}

with bpy.data.libraries.load(str(H/'HK416_Gameplay_Editable.blend'),link=False) as (a,b):
    b.objects=['Lower_body_low','Hand_grip_low','Triger_low']
for ob in b.objects:
    if ob:
        name=ob.name; objects[name]=freeze(ob,R.inverted()); report[name]=describe(ob)

for key in ['phantom_reargrip','stable_antislip_reargrip','balanced_reargrip']:
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=sources[key]['fbx'],use_custom_normals=True)
    obs=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH' and not o.name.startswith(('UCX_','UBX_','USP_','UCP_'))]
    for ob in obs:
        ob.data.transform(ob.matrix_world); ob.parent=None; ob.matrix_world=Matrix.Identity(4)
        ob.hide_render=True; ob.data.update(); report['donor_'+key]=describe(ob)
    file=S/'HK416CommonAttachments20260930/Meshes'/('SM_HK416_'+key+'.blend')
    with bpy.data.libraries.load(str(file),link=False) as (a,b): b.objects=a.objects
    ob=next(o for o in b.objects if o.type=='MESH')
    objects[key]=freeze(ob,R.inverted()); report['current_'+key]=describe(ob)

(O/'geometry_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

# Neutral studio inspection makes the physical shoulder and old adapter visible.
scene=bpy.context.scene; scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=1000; scene.render.resolution_y=850; scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO'; scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH'; scene.display.shading.show_specular_highlight=True
scene.display.shading.background_type='WORLD'; scene.world=bpy.data.worlds.new('Inspection world'); scene.world.color=(.055,.055,.055)
camdata=bpy.data.cameras.new('Interface inspection'); cam=bpy.data.objects.new('Interface inspection',camdata)
scene.collection.objects.link(cam); scene.camera=cam; camdata.type='ORTHO'; camdata.ortho_scale=.148
target=Vector((0,.016,-.009)); cam.location=target+Vector((.4,.10,.06))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
for n in ('Lower_body_low','Triger_low'):
    if n in objects: objects[n].hide_render=False; objects[n].color=(.20,.23,.24,1)
for key in ['Hand_grip_low','phantom_reargrip','stable_antislip_reargrip','balanced_reargrip']:
    ob=objects[key]; ob.hide_render=False; ob.color=(.42,.46,.47,1)
    scene.render.filepath=str(O/('before_'+key+'.png')); bpy.ops.render.render(write_still=True)
    ob.hide_render=True
print('HK416_REARGRIP_INPUTS_AND_INTERFACE_VIEWS_SAVED',flush=True)
