"""Blender background export; new hail/spike meshes, no render or test."""
import bpy, math, random
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/Blizzard20260930')
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
random.seed(930)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,radius=.5)
hail=bpy.context.object;hail.name='SM_BlizzardHail'
for v in hail.data.vertices:
    p=v.co;v.co*=1+.07*math.sin(p.x*22)*math.cos(p.y*18)+random.uniform(-.025,.025)
for p in hail.data.polygons:p.use_smooth=True
bpy.ops.export_scene.fbx(filepath=str(OUT/(hail.name+'.fbx')),use_selection=True,apply_unit_scale=True,axis_forward='-Y',axis_up='Z',add_leaf_bones=False,object_types={'MESH'})
bpy.ops.object.delete(use_global=False)
# An irregular ice spear, pointed at +Z, centered and one metre tall.
verts=[];rings=[(-.5,.16),(-.24,.23),(.08,.18),(.29,.09)]
for z,r in rings:
    for i in range(7):
        a=i*2*math.pi/7;rr=r*random.uniform(.82,1.15)
        verts.append((math.cos(a)*rr+z*.05,math.sin(a)*rr,z))
verts.append((.045,-.015,.5));faces=[tuple(reversed(range(7)))]
for ring in range(3):
    for i in range(7):faces.append((ring*7+i,ring*7+(i+1)%7,(ring+1)*7+(i+1)%7,(ring+1)*7+i))
for i in range(7):faces.append((21+i,21+(i+1)%7,28))
mesh=bpy.data.meshes.new('BlizzardSpike');mesh.from_pydata(verts,[],faces);mesh.update()
spike=bpy.data.objects.new('SM_BlizzardSpike',mesh);bpy.context.collection.objects.link(spike)
bpy.context.view_layer.objects.active=spike;spike.select_set(True)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project();bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.export_scene.fbx(filepath=str(OUT/(spike.name+'.fbx')),use_selection=True,apply_unit_scale=True,axis_forward='-Y',axis_up='Z',add_leaf_bones=False,object_types={'MESH'})
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'blizzard_meshes.blend'))
print('BLIZZARD_MESHES_EXPORTED')
