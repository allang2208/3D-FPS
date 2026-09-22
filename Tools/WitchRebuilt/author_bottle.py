"""Retain the source bottle silhouette/UV; split glass, closure and liquid."""
import bpy,math
from mathutils import Matrix
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921')
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'WitchMeshy20260919/Authoring/Witch_PoisonBottle_Candidate_v01.blend'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
for o in list(bpy.context.scene.objects):
    if o not in objects:bpy.data.objects.remove(o,do_unlink=True)
for o in objects:
    world=o.matrix_world.copy();o.parent=None;o.matrix_world=Matrix.Identity(4)
    for v in o.data.vertices:v.co=world@v.co
    glass=bpy.data.materials.new('WitchRebuilt_BottleGlass');cork=bpy.data.materials.new('WitchRebuilt_BottleClosure')
    glass.diffuse_color=(.12,.30,.15,.28);cork.diffuse_color=(.14,.075,.025,1)
    o.data.materials.clear();o.data.materials.append(glass);o.data.materials.append(cork)
    for p in o.data.polygons:p.material_index=1 if sum(o.data.vertices[i].co.z for i in p.vertices)/len(p.vertices)>.154 else 0
points=[v.co.copy() for o in objects for v in o.data.vertices];N=32;verts=[];faces=[]
for j in range(17):
    z=.009+j*.0065
    shell=[p.xy.length for p in points if abs(p.z-z)<.006]
    radius=max(.007,min(shell or [.025])-.0025)
    for i in range(N):
        a=i*2*math.pi/N;verts.append((radius*math.cos(a),radius*math.sin(a),z))
for j in range(16):
    for i in range(N):a=j*N+i;b=j*N+(i+1)%N;faces.append((a,b,b+N,a+N))
faces.append(tuple(reversed(range(N))));faces.append(tuple(range(16*N,17*N)))
me=bpy.data.meshes.new('WitchRebuilt_BottleLiquid');me.from_pydata(verts,[],faces);me.update()
liquid=bpy.data.objects.new('WitchRebuilt_BottleLiquid',me);bpy.context.collection.objects.link(liquid)
mat=bpy.data.materials.new('WitchRebuilt_BottleLiquid');mat.diffuse_color=(.035,.22,.025,1);me.materials.append(mat)
for o in [*objects,liquid]:
    for p in o.data.polygons:p.use_smooth=True
    o.data.normals_split_custom_set([(0,0,0)]*len(o.data.loops))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_Bottle.blend'))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Delivery/SM_WitchRebuilt_Bottle.fbx'),use_selection=True,object_types={'MESH'},
    bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
print('AUTHORED separated bottle materials and inner liquid',flush=True)
