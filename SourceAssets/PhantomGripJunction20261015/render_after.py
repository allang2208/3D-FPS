import bpy,json,sys,numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;key=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.open_mainfile(filepath=str(O/'Working'/(key+'_assembly.blend')));old=bpy.data.objects['Current_Phantom'];mat=old.data.materials[0];old.hide_render=True
with bpy.data.libraries.load(str(O/'Exports'/(key+'.blend')),link=False) as (a,b):b.objects=a.objects
ob=next(o for o in b.objects if o and o.type=='MESH');bpy.context.collection.objects.link(ob);ob.hide_set(False);ob.hide_render=False
for i in range(len(ob.data.materials)):ob.data.materials[i]=mat
scene=bpy.context.scene;suffix='_after'
if 'opposite' in sys.argv:
 d=np.load(O/'Working'/(key+'.npz'));p=d['host_positions'];t=d['host_triangles'];ids=np.isin(d['host_mids'],d['factory_slots']);fp=p[np.unique(t[ids])];top=fp[:,2].max();near=fp[fp[:,2]>top-.02];center=Vector(((near[:,0].min()+near[:,0].max())*.5,(near[:,1].min()+near[:,1].max())*.5,top-.022));scene.camera.location=center+Vector((-.4,-.055,.025));scene.camera.rotation_euler=(center-scene.camera.location).to_track_quat('-Z','Y').to_euler();suffix='_opposite'
scene.render.filepath=str(O/'Preview'/(key+suffix+'.png'));bpy.ops.render.render(write_still=True);print('JUNCTION_RENDERED',key,flush=True)
