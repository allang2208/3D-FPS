"""Diagnostic renders of native UE final poses at the actual camera; no asset edits."""
import bpy,sys,math,json
from pathlib import Path
import numpy as np
from mathutils import Matrix
P=Path(__file__).resolve().parent;version=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'Before';P=P/version
d=np.load(P/'evaluated.npz');verts=d['vertices'];mats=d['mats'];names=list(d['names']);tri=d['triangles'];ages=d['age']
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/SteelWarhammer20261014/QuickCombatLeftWristV7/Warhammer_QuickCombat_LeftWristV7_Editable.blend')
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];weapon=bpy.data.objects['SM_SteelWarhammer']
inv=rig.data.bones['WPN_root'].matrix_local.inverted()@rig.matrix_world.inverted()@weapon.matrix_world
wp=np.array([list(inv@v.co) for v in weapon.data.vertices]);faces=[list(f.vertices) for f in weapon.data.polygons]
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=960;scene.render.resolution_y=540;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('World');scene.world.color=(.065,.07,.08)
sh=scene.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD'
scene.view_settings.view_transform='Standard'
def mesh(name,v,f,color):
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob)
 mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);me.materials.append(mat)
 for poly in me.polygons:poly.use_smooth=True
 return ob
arms=mesh('Native final arms',verts[0],tri,(.65,.40,.27));hammer=mesh('Steel hammer',wp,faces,(.24,.27,.30))
floor=None
if '--ground' in sys.argv:
 floor_verts=[];floor_faces=[]
 for x in range(-400,1800,100):
  for y in range(-900,900,100):
   k=len(floor_verts);floor_verts.extend([(x,y,0,1),(x+100,y,0,1),(x+100,y+100,0,1),(x,y+100,0,1)])
   floor_faces.append((k,k+1,k+2,k+3))
 floor_world=np.array(floor_verts);floor=mesh('Diagnostic ground grid',floor_world[:,:3],floor_faces,(.16,.18,.20))
 alternate=bpy.data.materials.new('Alternate ground tile');alternate.diffuse_color=(.23,.25,.27,1);floor.data.materials.append(alternate)
 for j,poly in enumerate(floor.data.polygons):poly.material_index=(j//18+j%18)%2;poly.use_smooth=False
 canonical=np.eye(4);canonical[:3,:3]=np.array([[0,1,0],[1,0,0],[0,0,1]])*.01
camdata=bpy.data.cameras.new('75 vertical FOV');cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam)
cam.rotation_euler=(math.pi/2,0,0);camdata.type='PERSP';camdata.sensor_fit='HORIZONTAL';camdata.angle=2*math.atan(math.tan(math.radians(37.5))*16/9)
camdata.clip_start=.01;camdata.clip_end=100;scene.camera=cam
times=[0,.25,.475,.50,.55,.60,.65,.75,.9,1.10,1.12,1.15,1.20,1.25,1.28,1.35,1.40,1.5,1.6,1.75,1.83]
indices={int(np.abs(ages-t).argmin()) for t in times}
if '--full' in sys.argv:indices.update(range(0,len(ages),4))
report=json.loads((P/'surface-report.json').read_text())
for side in report['sides'].values():
 for key in ['wrist_bend_bind_deg','visible_shoulder_vertices','wrist_frame_travel_cm']:indices.add(side[key]['frame'])
for frame in sorted(indices):
 if floor:
  fv=np.einsum('ij,vj->vi',canonical@np.linalg.inv(d['camera'][frame]),floor_world)[:,:3]
  floor.data.vertices.foreach_set('co',fv.ravel());floor.data.update()
 arms.data.vertices.foreach_set('co',verts[frame].ravel());arms.data.update()
 m=mats[frame,names.index('wpn_root')].copy();m[:3,:3]/=np.linalg.norm(m[:3,:3],axis=0);hammer.matrix_world=Matrix(m.tolist())
 scene.render.filepath=str(P/f'view-{frame:03d}.png');bpy.ops.render.render(write_still=True)
(P/'render-index.json').write_text(json.dumps([{'frame':i,'age':float(ages[i]),'file':f'view-{i:03d}.png'} for i in sorted(indices)]))
print('LEAP_POSE_VIEWS',len(indices))
