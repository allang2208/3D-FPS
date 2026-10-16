"""Replace the baked 72-degree prop with a readable, physically mounted meter. No render."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'ModelV1'
sys.path.insert(0, str(SOURCE / 'Scripts'))
import geometry as g

bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'Authored/PotionWorkbench_Editable.blend'), load_ui=False, use_scripts=False)
scene = bpy.context.scene
for ob in list(scene.objects):
    if ob.type not in ('MESH', 'FONT', 'CURVE', 'EMPTY'):
        bpy.data.objects.remove(ob, do_unlink=True)
for key, name in {'atlas':'PW_SurfaceAtlas', 'wood':'PW_wood', 'display':'PW_Display', 'displaytext':'PW_DisplayGlyph'}.items():
    g.MATS[key] = bpy.data.materials[name]

old_names = ('Probe clamp', 'Probe insertion stem', 'Temperature probe enclosure', 'Probe status face', 'Temperature readout', 'Probe signal cable')
for name in old_names:
    ob = bpy.data.objects.get(name)
    if ob is None:
        raise RuntimeError('Missing source thermometer part: ' + name)
    bpy.data.objects.remove(ob, do_unlink=True)

# UE-local coordinates: the numeric component shares this exact transform.
center = (245, -106, 134)
pitch, yaw = 20, -140
screen_point = (2.06, .75, -.45)
cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
ue_rotation = Matrix(((cp*cy, -sy, -sp*cy), (cp*sy, cy, -sp*sy), (sp, 0, cp)))
mirror = Matrix.Diagonal((1, -1, 1))
frame = Matrix.Translation(mirror @ Vector(center)) @ (mirror @ ue_rotation @ mirror).to_4x4()

g.group('TemperatureInstrumentV9')
start = len(g.PARTS)
g.box('Meter rear seal', (-.35,0,0), (2.9,13.2,10.2), 'rubber', .65)
g.box('Meter ivory enclosure', (.1,0,0), (3.4,13,10), 'ivory', .6)
g.box('Meter brass bezel', (1.71,0,0), (.22,11.8,8.3), 'bronze', .22)
g.box('Meter dark display', (1.87,0,0), (.13,11.3,7.8), 'display', .2)
for y in (-5.9,5.9):
    for z in (-4.15,4.15):
        g.screw('Meter case fastener', (1.86,y,z), .18, (1,0,0), 'steel')

def face_text(name, value, position, size):
    ob = g.text(name, value, position, size, 'displaytext', (1,0,0), .004)
    # Font's horizontal axis is Blender +Y / UE -Y; vertical axis is +Z.
    ob.matrix_world = Matrix.Translation(Vector(position)) @ Matrix(((0,0,1,0),(1,0,0,0),(0,1,0,0),(0,0,0,1)))
    return ob

face_text('Temperature caption', 'TEMP', (2.01,0,2.75), .8)
face_text('Temperature unit C', 'C', (2.01,4.55,-1.15), 1.25)
g.torus('Temperature degree symbol', (2.02,3.74,-.54), .21, .06, 'displaytext', (1,0,0), 24, 8)
for ob in g.PARTS[start:]:
    ob.matrix_world = frame @ ob.matrix_world

# A clamp sits on the rolled lip at radius 22.8 cm. The probe extends below
# the lowest liquid surface (114 cm), rather than stopping above the liquid.
g.box('Thermometer rim saddle', (247.8,106,126.35), (4.8,4.6,1.0), 'steel', .2)
for x in (245.6,250.0):
    g.box('Thermometer clamp jaw', (x,106,124.9), (.6,3.6,2.5), 'steel', .12)
g.screw('Thermometer clamp lock', (250.4,106,125), .5, (1,0,0), 'brass')
g.rod('Thermometer immersed probe', (243,106,126.5), (243,106,110.5), .32, 'steel', 32)
g.rod('Thermometer probe bridge', (243,106,126.5), (247.8,106,126.5), .36, 'steel', 32)
mount = frame @ Vector((0,0,-4.7))
g.rod('Thermometer supported neck', (247.8,106,126.7), mount, .85, 'bronze', 40)
g.cylinder('Thermometer tilt pivot', mount, 1.05, 2.4, 'steel', (0,1,0), 40)
cable_start = frame @ Vector((-1.8,0,-2))
g.tube('Thermometer signal cable', [cable_start,(252,106,129),(256,112,116),(258,127,99),(259,141,89)], .18, 'rubber')

# Same static/moving split as RuntimeV2; moving utensils keep their existing assets.
objects = [o for o in scene.objects if o.type in ('MESH','FONT','CURVE')
           and not o.name.startswith(('Closed recipe folio','Folio '))
           and o.name != 'Pestle' and o.get('component') not in ('PotionSurface','HeaterRing')]
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/PotionWorkbench_Thermometer.blend'))
copies = []
for source in objects:
    ob=source.copy(); ob.data=source.data.copy(); scene.collection.objects.link(ob)
    ob.parent=None; ob.matrix_world=source.matrix_world.copy(); copies.append(ob)
bpy.ops.object.select_all(action='DESELECT')
for ob in copies: ob.select_set(True)
bpy.context.view_layer.objects.active=copies[0]
bpy.ops.object.convert(target='MESH'); bpy.ops.object.join()
ob=bpy.context.object; ob.name='SM_AlchemyBody'
scene.cursor.location=(0,0,0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
ob.location=(0,0,0); bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
mats=[]; mapping={}
for i,mat in enumerate(ob.data.materials):
    if mat not in mats: mats.append(mat)
    mapping[i]=mats.index(mat)
indices=[mapping[p.material_index] for p in ob.data.polygons]
ob.data.materials.clear()
for mat in mats: ob.data.materials.append(mat)
for p,i in zip(ob.data.polygons,indices): p.material_index=i
record={'name':ob.name,'materials':[m.name for m in mats],'lods':[]}
for level,ratio in ((0,1),(1,.52),(2,.22)):
    item=ob if level==0 else ob.copy()
    if level:
        item.data=ob.data.copy(); scene.collection.objects.link(item)
    g.select(item)
    if level:
        dec=item.modifiers.new('Distance reduction','DECIMATE'); dec.ratio=ratio
        dec.delimit={'MATERIAL','SEAM','SHARP'}; bpy.ops.object.modifier_apply(modifier=dec.name)
    file=ROOT/'Authored'/f'SM_AlchemyBody_LOD{level}.fbx'
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,
        add_leaf_bones=False,bake_anim=False,path_mode='STRIP')
    item.data.calc_loop_triangles(); record['lods'].append({'source':str(file),'triangles':len(item.data.loop_triangles)})
    if level: bpy.data.objects.remove(item,do_unlink=True)

position=Vector(center)+ue_rotation@Vector(screen_point)
header=ROOT.parents[2]/'Source/FPSGAME/Building/AlchemyThermometerLayout.h'
header.write_text('#pragma once\n#include "CoreMinimal.h"\n\n// Generated by ThermometerV9/author_thermometer.py; matches the physical screen.\nnamespace AlchemyThermometer\n{\n'
    +f'inline const FVector ReadoutPosition({position.x:.6f},{position.y:.6f},{position.z:.6f});\n'
    +f'inline const FRotator ReadoutRotation({pitch},{yaw},0);\n'
    +'inline constexpr float DigitSize=4.3f;\n}\n','utf8')
(ROOT/'asset-manifest.json').write_text(json.dumps({'parts':[record],'meter_center_ue':center,'readout_position_ue':list(position),
    'rotation_pitch_yaw_roll':[pitch,yaw,0],'body_size_cm':[3.4,13,10],'digit_size_cm':4.3,'removed_fixed_readout':'72',
    'probe_tip_z_cm':110.5,'rendered':False},indent=2),'utf8')
print('ALCHEMY_THERMOMETER_EXPORTED',flush=True)
