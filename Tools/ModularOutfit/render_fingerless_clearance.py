"""Isolated geometry review requested by the user; no UE/editor or gameplay."""
import json,sys,math,os
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector,Matrix
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';OUT=R/('ClearanceAfter' if '--final' in sys.argv else 'ClearanceReview')
def read(p):return json.loads(p.read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
side=os.environ.get('FINGERLESS_RENDER_SIDE','l')
frame=read(P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy'][side]
basis=Matrix([frame['across'],frame['forward'],frame['dorsal']]);wrist=Vector(frame['wrist'])
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=.6
    return m
def obj(d,name,mat,skin=False):
    points=[tuple(basis@(Vector(p)-wrist)*.01) for p in d['positions']]
    left=[sum(w for n,w in weights.items() if n.endswith('_'+side))>.5 for weights in d['weights']]
    faces=[f[::-1] for i,f in enumerate(d['triangles']) if (not skin or d['triangle_materials'][i] in (2,4)) and all(left[v] for v in f)]
    m=bpy.data.meshes.new(name);m.from_pydata(points,[],faces);m.update();o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o);m.materials.append(mat)
    for f in m.polygons:f.use_smooth=True
name=os.environ.get('FINGERLESS_RENDER_PROFILE','PKM' if '--pose' in sys.argv else 'M4');profile=name
skin=read(R/'SkinCoverage'/(name+'_review.json')) if '--coverage' in sys.argv else read(OUT/(name+'_skin.json'))
glove=read(R/'Authored'/(name+'.json')) if '--authored' in sys.argv else read(OUT/(name+'_glove.json'))
sleeve=read(OUT/(name+'_shirt.json')) if '--sleeve' in sys.argv else None
if '--pose' in sys.argv:
    ns={};exec((P/'Tools/ModularOutfit/check_fingerless_clearance.py').read_text().split('report=dict(')[0],ns)
    label=os.environ.get('FINGERLESS_RENDER_LABEL','angled_A_PKM_angled_reload' if name=='PKM' else 'vertical_A_A762_vertical_reload')
    row=read(OUT/(name+'__'+label+'_poses.json'));pi=int(os.environ.get('FINGERLESS_RENDER_POSE',str(len(row['poses'])//2)));pose=row['poses'][pi]['bones']
    # Return the posed hand to the inspection camera's local frame; preserve
    # all finger/metacarpal deformation and the shared glove/skin seam.
    back=ns['matrix'](skin['bones']['hand_'+side])@np.linalg.inv(ns['matrix'](pose['hand_'+side]))
    for d in [skin,glove]+([sleeve] if sleeve else []):
        data=ns['prepare'](d);p=ns['deform'](data,pose);out=np.array(d['positions']);out[data['original_ids']]=p
        d['positions']=(np.c_[out,np.ones(len(out))]@back.T)[:,:3].tolist()
obj(skin,'ActualV7Skin',material('Skin',(.32,.12,.065)),True)
obj(glove,'Glove',material('Leather',(.038,.011,.004)))
if sleeve:obj(sleeve,'FittedSleeve',material('Sleeve',(.13,.16,.15)))
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.background_type='WORLD'
s.render.resolution_x=720;s.render.resolution_y=720;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.20,.22,.25,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.5
def point(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
for pos in [(.13,.04,.20),(-.15,.12,.13)]:
    l=bpy.data.lights.new('Softbox','AREA');l.energy=14;l.size=.18;o=bpy.data.objects.new(l.name,l);bpy.context.collection.objects.link(o);o.location=pos;point(o,(0,.06,0))
c=bpy.data.cameras.new('Review');c.type='ORTHO';c.ortho_scale=.215;o=bpy.data.objects.new('Review',c);bpy.context.collection.objects.link(o);s.camera=o
for name,pos in [('back',(.035,.045,.25)),('thumb',(.21,.045,.065)),('palm',(.025,.06,-.25))]:
    o.location=pos;point(o,(0,.07,0));s.render.filepath=str(OUT/(profile+'-'+side+'-'+('sleeve-' if sleeve else '')+('posed-' if '--pose' in sys.argv else 'rest-')+name+'.png'));bpy.ops.render.render(write_still=True)
