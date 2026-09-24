import bpy, json
import numpy as np
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'SourceAssets/InfectedDogMeshy20260924'
OUT=BASE/'LocalRig'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(BASE/'Meshy/candidate01_quad50k/downloads/model.fbx'))
print('FBX_STRUCTURE',json.dumps([{'name':o.name,'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'quads':sum(len(p.vertices)==4 for p in o.data.polygons),'dimensions':list(o.dimensions)} for o in bpy.context.scene.objects if o.type=='MESH']))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BASE/'Meshy/candidate01_quad50k/downloads/model.glb'))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
v=np.array([list(obj.matrix_world@p.co) for p in obj.data.vertices])
origin=np.array([(v[:,0].min()+v[:,0].max())/2,0,v[:,2].min()])
v=(v-origin)/(v[:,2].max()-v[:,2].min())
np.savez_compressed(str(OUT/'anatomy_source.npz'),vertices=v,edges=np.array([list(e.vertices) for e in obj.data.edges]))
print('ANATOMY_SOURCE_SAVED')
