"""Authoring diagnostic only; final acceptance uses the runtime capture rig."""
from pathlib import Path
import ast,json,sys,bpy,numpy as np
from mathutils import Vector
HERE=Path(__file__).resolve().parent
filename=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'before_idle'
d=np.load(HERE/(filename+'.npz'));p=d['v']*[1,-1,1];f=d['f'];s=d['s'];names=d['names'].tolist();dominant=d['dominant'];slots=json.loads((HERE/'slots.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=1000;scene.render.resolution_y=760;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('World');scene.world.color=(.075,.075,.075)
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
tree=ast.parse((HERE.parent.parent/'M249Orpind20261107/Wrist37/render_final.py').read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'existing-render-helpers','exec'))
skin=mat('Skin',(.58,.34,.22));metal=mat('Gun',(.14,.19,.23))
sk=np.array([x.startswith('Skin_') for x in slots])[s];left=np.array([n.endswith('_l') for n in names])[dominant]
hidden=np.array([any(t in x for t in ['Foregrip','Glass','Reticle','Magazine_New','Belt_New']) for x in slots])[s]
center=p[dominant==names.index('hand_l')].mean(0)
for view,offset in [('outside',[60,10,25]),('palm',[-60,-20,18]),('front',[0,-65,8])]:
    for ob in list(scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
    mesh('Skin',p,f[sk&left[f].any(1)],skin);mesh('Gun',p,f[~sk&~hidden],metal)
    cam=bpy.data.cameras.new('Camera');co=bpy.data.objects.new('Camera',cam);scene.collection.objects.link(co);scene.camera=co
    co.location=center+np.array(offset);co.rotation_euler=(Vector(center)-co.location).to_track_quat('-Z','Y').to_euler();cam.type='ORTHO';cam.ortho_scale=34;cam.clip_start=.1
    scene.render.filepath=str(HERE/(filename+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
