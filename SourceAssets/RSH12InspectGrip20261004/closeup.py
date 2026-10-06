"""Offline close-up for the specifically requested grip-penetration diagnosis."""
import sys,json,math
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O))
from grip_scene import *
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
kind=args[0] if args else 'inspect'
rig,D,profile,meta=load()
if len(args)>1 and args[1]=='after':profile=json.loads((O/'Single/profile.json').read_text())
sample=min(D['clips'][kind]['samples'],key=lambda s:abs(s['time']-(1.2 if kind=='inspect' else 0)))
p=pose(rig,D,profile,kind,sample)
if len(args)>1 and args[1]=='final':
    from held_grip import HeldGrip
    HeldGrip(rig,D,profile,meta).authored(p,kind)
    results,_,_=report(Skin(rig,'r'),p,meta,grip_trees()[0][1]);print('FINAL_CONTACT',json.dumps(results),flush=True)
if len(args)>1 and args[1]=='held':
    from grip_motion import correct
    idle=pose(rig,D,profile,'idle',D['clips']['idle']['samples'][0])
    correct(idle,rig,meta,json.loads((O/'wrap_single_r_idle.json').read_text()))
    for n in p:
        if n.endswith('_r') and n.startswith(('middle','ring','pinky')) and 'metacarpal' not in n:
            par=rig.data.bones[n].parent.name;p[n]=p[par]@idle[par].inverted()@idle[n]
    results,_,_=report(Skin(rig,'r'),p,meta,grip_trees()[0][1]);print('HELD_FIT',json.dumps(results),flush=True)
if len(args)>1 and args[1] in ('fit','natural','wrap','production'):
    from grip_motion import correct
    correct(p,rig,meta,json.loads((O/(args[1]+'_single_r_'+kind+'.json')).read_text()))
    results,_,_=report(Skin(rig,'r'),p,meta,grip_trees()[0][1]);print('EXACT_FIT',json.dumps(results),flush=True)
set_pose(rig,p)
deps=bpy.context.evaluated_depsgraph_get();canonical=canonical_pose(p,meta)
for ob in list(bpy.data.objects):
    if ob.type!='MESH':continue
    mesh=bpy.data.meshes.new_from_object(ob.evaluated_get(deps));obj=bpy.data.objects.new('Contact_'+ob.name,mesh);bpy.context.collection.objects.link(obj)
    obj.matrix_world=canonical@rig.matrix_world.inverted()@ob.matrix_world;ob.hide_render=True
    for m in mesh.materials:
        if m:m.diffuse_color=(.58,.32,.18,1) if 'Manny' in m.name else (.20,.23,.26,1)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1100;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.world=bpy.data.worlds.new('GripDiagnosticWorld');scene.world.color=(.1,.12,.15);scene.display.shading.background_type='WORLD'
raw=json.loads((O.parent/'RSH12Integration20261003/canonical_parts.json').read_text());g=next(p for p in raw if p['name']=='9_l')
vv=np.array(g['verts']);print('GRIP BOUNDS',vv.min(0).tolist(),vv.max(0).tolist(),flush=True)
target=Vector((0,float(vv[:,1].mean()),-.025))
for name,offset in [('right',(.26,.12,.08)),('left',(-.26,.12,.08)),('front',(.04,-.27,.03))]:
    camdata=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,camdata);bpy.context.collection.objects.link(cam)
    cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=.20;camdata.clip_start=.001
    scene.camera=cam;scene.render.filepath=str(O/(kind+'_'+('after' if len(args)>1 else 'before')+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
