import bpy,json,math
from pathlib import Path
from mathutils import Vector
out=Path('D:/FPS3D/FPSGAME/SourceAssets/M4FoldingSights20260909');out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4Replacement/m4_source_imported.blend')
obj=bpy.data.objects['M4 Body']
pts=[obj.matrix_world@v.co for v in obj.data.vertices]
parent=list(range(len(pts)))
def find(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def union(a,b):parent[find(a)]=find(b)
positions={}
for i,p in enumerate(pts):
 key=tuple(round(v,6) for v in p)
 if key in positions:union(i,positions[key])
 else:positions[key]=i
for e in obj.data.edges:union(*e.vertices)
groups={}
for i in range(len(pts)):groups.setdefault(find(i),[]).append(i)
rows=[]
for ids in groups.values():
 pp=[pts[i] for i in ids];lo=[min(p[a] for p in pp) for a in range(3)];hi=[max(p[a] for p in pp) for a in range(3)]
 rows.append(dict(vertices=len(ids),lo=lo,hi=hi,indices=ids))
rows.sort(key=lambda r:r['hi'][2],reverse=True)
(out/'body-components.json').write_text(json.dumps(rows,indent=2))
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Review');scene.world.color=(.2,.2,.2)
for o in scene.objects:o.hide_render=o!=obj
for location in [(0.3,.1,.4),(-.1,-.2,.3)]:
 bpy.ops.object.light_add(type='AREA',location=location);bpy.context.object.data.energy=15;bpy.context.object.data.size=.3
bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.09
for name,center in [('rear',Vector((.037,.1247,.073))),('front',Vector((.037,-.1888,.073)))]:
 cam.location=center+Vector((.17,.04,.06));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
print('M4_IRON_COMPONENTS',json.dumps([{k:v for k,v in r.items() if k!='indices'} for r in rows[:35]]))
