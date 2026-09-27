"""Scoped inspection of the current upper-riser grasp (offline, centimetres)."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent;ROOT=P.parents[1];OUT=P/'Review';OUT.mkdir(parents=True,exist_ok=True)
version='after' if '--after' in sys.argv else 'before'
case=P if version=='after' else P.parent/'BowQuickCombatPush20260927'
script=case/('generated_contact_v4.py' if version=='after' else 'generated_push_v3.py')
ns={'__file__':str(script)}
exec(compile(script.read_text().split('bpy.ops.wm.open_mainfile')[0],str(script),'exec'),ns)
data=ns['ns']['data'];R=ns['R'];rest=ns['rest'];w=ns['pose'](.32)
skin={n:w['bow_grip'].inverted()@m@rest[n].inverted() for n,m in w.items()}
hand_ids=[i for i,weights in enumerate(data['weights']) if sum(v for n,v in weights.items() if n=='hand_r' or (n.endswith('_r') and n.split('_')[0] in ('index','middle','ring','pinky','thumb')))>0.8]
points={i:sum((skin[n]@(R@Vector(data['positions'][i]))*v for n,v in data['weights'][i].items()),Vector()) for i in hand_ids}
with bpy.data.libraries.load(str(P.parent/'BowModular20260926/Bow_ModularParts.blend'),link=False) as (a,b):b.objects=['SM_Bow_BodyModular']
body=b.objects[0]
verts=[Vector((v.x,-v.y,v.z)) for v in [body.matrix_world@v.co for v in body.data.vertices]]
polys=[tuple(reversed(p.vertices)) for p in body.data.polygons]
import numpy as np
envelope=np.load(P/'contact-envelope.npz')
bvh=BVHTree.FromPolygons(envelope['vertices'].tolist(),envelope['faces'].tolist())
groups={}
for i,p in points.items():
    co,no,idx,dist=bvh.find_nearest(p)
    group=max(data['weights'][i],key=data['weights'][i].get).split('_')[0]
    signed=dist if (p-co).dot(no)>=0 else -dist
    groups.setdefault(group,[]).append((signed,i,list(p)))
result={'right_wrist':list(w['bow_grip'].inverted()@w['hand_r'].translation),'groups':{}}
for group,rows in groups.items():
    rows.sort();result['groups'][group]={'min_signed_cm':rows[0][0],'inside_vertices':sum(r[0]<-.05 for r in rows),'count':len(rows),'deepest':rows[:5]}
result['hand_bounds']=[[min(p[a] for p in points.values()),max(p[a] for p in points.values())] for a in range(3)]
result['bow_sections']={}
for z in (24.,28.,30.8,34.,38.):
    pts=[p for p in verts if abs(p.z-z)<1.5]
    result['bow_sections'][z]=[[min(p[a] for p in pts),max(p[a] for p in pts)] for a in range(2)]
(P/f'contact-{version}.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))

# Frame the right grip in the actual skinned animation, along three axes.
bpy.ops.wm.open_mainfile(filepath=str(case/'Bow_QuickCombat.blend'))
rig=bpy.data.objects['Bow_V7_Native'];arms=bpy.data.objects['SK_Bow_BareArmsV7']
for o in list(bpy.data.objects):
    if o not in (rig,arms):bpy.data.objects.remove(o,do_unlink=True)
for o in (rig,arms):o.hide_render=False
with bpy.data.libraries.load(str(P.parent/'BowModular20260926/Bow_ModularParts.blend'),link=False) as (a,b):b.objects=[n for n in a.objects if n.startswith('SM_Bow_')]
parts=[]
for o in b.objects:
    if o and o.type=='MESH':bpy.context.collection.objects.link(o);o.parent=None;o.animation_data_clear();parts.append(o)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
scene.render.resolution_x=700;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.world=bpy.data.worlds.new('ContactWorld');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.16,.18,.20,1);bg.inputs[1].default_value=.7
for m in arms.data.materials:
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(.42,.23,.14,1)
    p.inputs['Roughness'].default_value=.65
scene.frame_set(round(.32*240))
bow=ns['world_to_blender'](w['bow_grip'])
for o in parts:o.matrix_world=bow@Matrix.Scale(.01,4)
center=bow@Vector((-.04,0,.278))
cam_data=bpy.data.cameras.new('Contact');cam=bpy.data.objects.new('Contact',cam_data);scene.collection.objects.link(cam);scene.camera=cam
cam_data.type='ORTHO';cam_data.ortho_scale=.24;cam_data.clip_start=.001
for name,offset in [('side',Vector((.3,-.3,.1))),('palm',Vector((-.3,.2,.07))),('top',Vector((.1,.1,.4)))]:
    cam.location=center+bow.to_3x3()@offset;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    ld=bpy.data.lights.new(name,'AREA');ld.energy=35;ld.size=.5;lo=bpy.data.objects.new(name,ld);scene.collection.objects.link(lo)
    lo.location=cam.location;lo.rotation_euler=cam.rotation_euler
    scene.render.filepath=str(OUT/f'{version}_{name}.png');bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(lo,do_unlink=True)
