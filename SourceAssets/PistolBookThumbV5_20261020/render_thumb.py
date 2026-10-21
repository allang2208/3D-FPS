"""Targeted thumb diagnosis/preview requested by the user; no UE launch."""
import bpy,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;V4=P.parent/'PistolBookPoseV4_20261020'
tag=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'before'
bpy.ops.wm.open_mainfile(filepath=str(V4/'PistolBook_V4_StaticCandidate.blend'))
s=bpy.context.scene;s.frame_set(2);s.cycles.samples=32
s.render.resolution_x=900;s.render.resolution_y=650
left=bpy.data.objects['left_native_V9']
# Fixed-pose mesh avoids carrying custom normals from the hip Shape Key into ADS.
left.shape_key_clear()
x=np.load(P/(tag+'.npz'))['X'] if (P/(tag+'.npz')).exists() else np.load(V4/'aim_left.npz')['X']
x=x*np.array([1,-1,1])*.01
left.data.vertices.foreach_set('co',x.reshape(-1));left.data.update()
left.data.calc_loop_triangles();t=np.array([f.vertices[:] for f in left.data.loop_triangles])
_,weld=np.unique(np.round(x,7),axis=0,return_inverse=True)
f=np.cross(x[t[:,1]]-x[t[:,0]],x[t[:,2]]-x[t[:,0]])
n=np.zeros((weld.max()+1,3))
for k in range(3):np.add.at(n,weld[t[:,k]],f)
n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1.e-12)
left.data.normals_split_custom_set(n[weld[t]].reshape(-1,3).tolist())
bpy.data.objects['right_native_V9'].hide_render=True
bpy.data.objects['Actual M1911 contact geometry'].hide_render=True
d=json.loads((V4/'candidate.json').read_text());book=np.array(d['book_frames']['aim'])
target=np.array(d['poses']['aim']['left']['thumb_02_l'])[:3,3]
target=Vector(target*np.array([1,-1,1])*.01)
camera=s.camera;camera.data.animation_data_clear();camera.data.lens=52
camera.data.sensor_fit='HORIZONTAL';camera.data.sensor_width=36
for name,offset in [('palm',[-.15,-.13,-.15]),('side',[.10,-.25,-.05])]:
    camera.location=target+Vector(offset)
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=str(P/(tag+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
print('THUMB_PREVIEW_SAVED',tag,flush=True)
if tag=='after':
    right=bpy.data.objects['right_native_V9'];right.hide_render=False
    bpy.data.objects['Actual M1911 contact geometry'].hide_render=False
    # Also remove the stale hip normals from the unchanged right-arm preview.
    right.shape_key_clear();rx=np.load(V4/'aim_right.npz')['X']*np.array([1,-1,1])*.01
    right.data.vertices.foreach_set('co',rx.reshape(-1));right.data.update();right.data.calc_loop_triangles()
    rt=np.array([f.vertices[:] for f in right.data.loop_triangles]);_,rw=np.unique(np.round(rx,7),axis=0,return_inverse=True)
    rf=np.cross(rx[rt[:,1]]-rx[rt[:,0]],rx[rt[:,2]]-rx[rt[:,0]]);rn=np.zeros((rw.max()+1,3))
    for k in range(3):np.add.at(rn,rw[rt[:,k]],rf)
    rn/=np.maximum(np.linalg.norm(rn,axis=1,keepdims=True),1.e-12)
    right.data.normals_split_custom_set(rn[rw[rt]].reshape(-1,3).tolist())
    camera.location=(0,0,0);camera.rotation_euler=Matrix(((0,0,-1),(-1,0,0),(0,1,0))).to_euler()
    camera.data.sensor_fit='VERTICAL';camera.data.sensor_height=24
    camera.data.lens=24/(2*np.tan(np.radians(55/2)))
    s.render.resolution_x=1280;s.render.resolution_y=720
    s.render.filepath=str(P/'aim.png');bpy.ops.render.render(write_still=True)
    s.frame_start=s.frame_end=2
    s['status']='Thumb-only repair on V4 book-down pose; static author preview, not game capture'
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(P/'PistolBook_ThumbV5.blend'))
