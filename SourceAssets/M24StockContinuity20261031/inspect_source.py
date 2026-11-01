import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ReceiverGripRebuild20261031/M24_ReceiverGrip_Editable.blend'),load_ui=False,use_scripts=False)
R={}
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 p=np.array([list(ob.matrix_world@v.co) for v in ob.data.vertices]);R[ob.name]={'vertices':len(p),'faces':len(ob.data.polygons),'bounds':[p.min(0).tolist(),p.max(0).tolist()],'materials':[m.name if m else None for m in ob.data.materials]}
stock=bpy.data.objects['M24_SkeletonStock_ReferenceProportion'];p=np.array([list(v.co) for v in stock.data.vertices])
R['stock_slices']=[]
for y in np.linspace(-.36,-.04,33):
 q=p[np.abs(p[:,1]-y)<.002]
 if len(q):R['stock_slices'].append({'y':float(y),'x_quantiles':np.quantile(q[:,0],[0,.1,.5,.9,1]).tolist(),'z_quantiles':np.quantile(q[:,2],[0,.1,.25,.5,.75,.9,1]).tolist()})
(O/'source_dimensions.json').write_text(json.dumps(R,indent=2))
# Side orthographic source view, scoped to the user's connection inspection.
scene=bpy.context.scene
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.hide_render=ob.hide_get()
scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1500;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.world=scene.world or bpy.data.worlds.new('M24InspectionWorld')
scene.world.use_nodes=True;nodes=scene.world.node_tree.nodes;nodes.clear();background=nodes.new('ShaderNodeBackground');output=nodes.new('ShaderNodeOutputWorld');scene.world.node_tree.links.new(background.outputs[0],output.inputs[0]);background.inputs[0].default_value=(.13,.15,.18,1);background.inputs[1].default_value=.6
for loc,power,size in [((.6,-.05,.8),100,1.),((-.3,.2,.5),70,.7)]:
 bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(Vector((0,.05,.05))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(1.5,.045,.095));camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=.90;camera.rotation_euler=(Vector((0,.045,.095))-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera=camera
scene.view_settings.view_transform='AgX';scene.render.filepath=str(O/'before_side.png');bpy.ops.render.render(write_still=True)
print('M24_CONTINUITY_SOURCE_READ',flush=True)
