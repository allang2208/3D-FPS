"""Export one locally culled set of registered panels per wall section."""
from pathlib import Path
import json
import bpy
R=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
stock=bpy.data.materials.new('CastBayConcrete')
out=R/'Meshes';out.mkdir(exist_ok=True)
for key,data in json.loads((R/'repairs.json').read_text('utf8')).items():
    m=bpy.data.meshes.new(key)
    points=[(x/100,-y/100,z/100) for x,y,z in data['v']]
    m.from_pydata(points,[],[f[::-1] for f in data['f']]);m.update()
    obj=bpy.data.objects.new(key,m);bpy.context.collection.objects.link(obj)
    m.materials.append(stock)
    uv=m.uv_layers.new(name='CastForm')
    for loop in m.loops:uv.data[loop.index].uv=data['uv'][loop.vertex_index]
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(out/(key+'.fbx')),use_selection=True,axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(m)
