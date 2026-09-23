"""Geometric preview of saved UE compressed poses. Not a gameplay screenshot."""
import bpy,sys,json,math
from pathlib import Path
import numpy as np
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'Saved/MeleeArmOpeningReview20260923/GeometryCapture';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).parent))
# Keep the matrix helper local so loading the renderer does not rerun reports.
def matrix(t):
    from mathutils import Matrix,Quaternion
    return np.array(Matrix.LocRotScale(Vector(t['p']),Quaternion(t['q']),Vector(t['s'])))
poses=json.loads((OUT.parent/'evaluated-poses.json').read_text())
for family in ('Standard',):
    base=ROOT/'SourceAssets/MeleeArmOpening20260923'/family
    source=json.loads((base/'source.json').read_text());g=json.loads((base/'geometry.json').read_text())
    inv={n:np.linalg.inv(matrix(t)) for n,t in source['rest'].items()}
    p=np.array([[*v,1] for v in g['vertices']]);groups={}
    for n in {n for row in g['weights'] for n in row}:
        indices=np.array([i for i,row in enumerate(g['weights']) if n in row])
        groups[n]=(indices,p[indices]@inv[n].T,np.array([g['weights'][i][n] for i in indices]))
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
    # The FBX-to-UE mapping already mirrors handedness; reflecting Y below
    # returns to Blender handedness and keeps the imported triangle winding.
    mesh=bpy.data.meshes.new('CurrentArms');mesh.from_pydata(g['vertices'],[],g['triangles']);mesh.update()
    ob=bpy.data.objects.new('ArmsCompressedPose',mesh);scene.collection.objects.link(ob);ob.color=(.45,.57,.68,1)
    for face in mesh.polygons:face.use_smooth=True
    camera=bpy.data.objects.new('DiagnosticCamera',bpy.data.cameras.new('DiagnosticCamera'));scene.collection.objects.link(camera);scene.camera=camera
    camera.location=(0,0,0);camera.rotation_euler=(math.pi/2,0,0);camera.data.sensor_fit='VERTICAL';camera.data.sensor_height=24;camera.data.clip_start=1;camera.data.clip_end=10000
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
    scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
    scene.display.shading.show_backface_culling=True;scene.display.shading.background_type='WORLD'
    scene.world=bpy.data.worlds.new('DiagnosticWorld');scene.world.color=(.045,.055,.07)
    scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    for clip in ('Thrust','SprintOverhead'):
        rows=poses[family][clip]['COMPRESSED']
        for row in [min(rows,key=lambda r:abs(r['seconds']-t)) for t in ([.58,.625] if clip=='Thrust' else [1.16,1.22])]:
            v=np.zeros((len(p),3))
            for n,(idx,local,w) in groups.items():v[idx]+=(local@matrix(row['world'][n]).T)[:,:3]*w[:,None]
            v[:,1]*=-1
            mesh.vertices.foreach_set('co',v.ravel());mesh.update()
            for vfov in (75,95):
                camera.data.lens=24/(2*math.tan(math.radians(vfov*.5)))
                scene.render.filepath=str(OUT/f'{family}_{clip}_{row["seconds"]:.3f}_v{vfov}.png');bpy.ops.render.render(write_still=True)
    print('ARM_GEOMETRY_CAPTURE_COMPLETE',flush=True)
