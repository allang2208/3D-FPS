"""Requested source/rig inspection of HeQue, without launching the game."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/RigV01')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/HeQue_refined_rig_motion_v01.blend'))
rig=bpy.data.objects['HeQueRig'];body=bpy.data.objects['HeQueBody'];chain=bpy.data.objects['HeQueRigidChain']
report={'actions':list(a.name for a in bpy.data.actions),'weights':{},'poses':{}}
for ob in (body,chain):
    sums=[sum(g.weight for g in v.groups) for v in ob.data.vertices]
    report['weights'][ob.name]={'unweighted':sum(v<1e-5 for v in sums),'max_sum_error':max(abs(v-1) for v in sums),'max_influences':max(len(v.groups) for v in ob.data.vertices)}
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('HeQueInspection');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.4,.4,.4,1);bg.inputs[1].default_value=.7
for pos,power in [((-3,-4,5),500),((4,-1,3),300),((0,3,4),350)]:
    d=bpy.data.lights.new('Softbox','AREA');d.energy=power;d.size=4
    ob=bpy.data.objects.new('Softbox',d);scene.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,0,.8))-ob.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('InspectionCamera');d.type='ORTHO';d.ortho_scale=2.0
cam=bpy.data.objects.new('InspectionCamera',d);scene.collection.objects.link(cam);scene.camera=cam
cam.location=(2,-5,1.);cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler()
for role,seconds in [('Idle',0.),('Move',1.55),('Stun',.65),('Land',.65)]:
    rig.animation_data.action=bpy.data.actions['A_HeQue_'+role]
    scene.frame_set(round(seconds*60)+1);bpy.context.view_layer.update()
    row={}
    for ob in (body,chain):
        ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();p=np.array([v.co[:] for v in m.vertices]);ev.to_mesh_clear()
        row[ob.name]={'finite':bool(np.isfinite(p).all()),'lo':p.min(0).tolist(),'hi':p.max(0).tolist()}
    report['poses'][role]=row
    scene.render.filepath=str(ROOT/'Inspection'/('refined_'+role+'.png'));bpy.ops.render.render(write_still=True)
(ROOT/'Records/rig-inspection.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('HEQUE_RIG_INSPECTION '+json.dumps(report),flush=True)
