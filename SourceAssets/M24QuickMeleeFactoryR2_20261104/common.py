"""Current M24 inputs and original factory-branch pose composition."""
import bpy,json,gzip,math,bisect,ast
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion,Euler
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent;S=O.parent
exec(compile((S/'M24QuickMeleeGrip20261104/author.py').read_text().split('# Read physical assembly geometry')[0],'native M24 pose helpers','exec'))
def smooth(x):
    x=max(0.,min(1.,x));return max(0.,min(1.,x*x*x*(10+x*(-15+6*x))))
def clone(row):return {n:m.copy() for n,m in row.items()}
def local(row,n):return row[parents[n]].inverted()@row[n] if parents[n] else row[n]
def grip_weight(t):return smooth((t-.03)/.11)*(1-smooth((t-.45)/.23))
def setup_geometry():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry={}
    for key,spec in json.loads((O/'assembly.json').read_text()).items():
        before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=spec['fbx'],use_custom_normals=True)
        points=[];faces=[]
        for ob in set(bpy.data.objects)-before:
            if ob.type!='MESH':continue
            k=len(points);points.extend([ob.matrix_world@v.co for v in ob.data.vertices]);ob.data.calc_loop_triangles()
            faces.extend([tuple(k+i for i in f.vertices) for f in ob.data.loop_triangles])
        geometry[key]=(points,faces)
        for ob in list(set(bpy.data.objects)-before):bpy.data.objects.remove(ob,do_unlink=True)
    return geometry
