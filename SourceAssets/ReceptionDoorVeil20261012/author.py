"""Two tiny door-local meshes and one periodic packed fog texture; no render."""
from pathlib import Path
import json, math, hashlib
import bpy
import numpy as np

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
(ROOT/'Receipts').mkdir(exist_ok=True)
BASE='/Game/Dungeons/ReceptionDoorVeil20261012'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1.

# Independent periodic fields, packed in RGB. Only two samples per fog pixel.
size=256
y,x=np.mgrid[0:size,0:size].astype(float)/size
channels=[]
for seed in (12101,12102,12103):
    rng=np.random.default_rng(seed);field=np.zeros_like(x)
    for frequency,weight in ((2,1.),(4,.52),(8,.24),(16,.10)):
        for _ in range(8):
            kx=int(rng.integers(-frequency,frequency+1));ky=int(rng.integers(-frequency,frequency+1))
            if not kx and not ky:kx=1
            field+=weight*np.sin(math.tau*(kx*x+ky*y)+rng.uniform(0,math.tau))/8
    field=(field-field.min())/(field.max()-field.min())
    channels.append(field)
pixels=np.stack((*channels,np.ones_like(x)),axis=-1).astype('float32')
image=bpy.data.images.new('T_ReceptionDoor_FogNoise',width=size,height=size,alpha=True)
image.colorspace_settings.name='Non-Color';image.pixels.foreach_set(pixels.ravel())
image.filepath_raw=str(OUT/'T_ReceptionDoor_FogNoise.png');image.file_format='PNG';image.save()

records=[]
def export(name,quads,material):
    vertices=[];faces=[]
    for q in quads:
        first=len(vertices);vertices.extend(q);faces.extend(((first,first+1,first+2),(first,first+2,first+3)))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    uv=mesh.uv_layers.new(name='UVMap')
    coords=((0,0),(1,0),(1,1),(0,1))
    for face in mesh.polygons:
        for li in face.loop_indices:uv.data[li].uv=coords[mesh.loops[li].vertex_index%4]
    mat=bpy.data.materials.new(material);mesh.materials.append(mat)
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    fbx=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,use_tspace=True,mesh_smooth_type='FACE',add_leaf_bones=False)
    records.append(dict(name=name,mesh=BASE+'/Meshes/'+name,fbx=str(fbx),material=BASE+'/Materials/'+material,
        triangles=len(faces),sha256=hashlib.sha256(fbx.read_bytes()).hexdigest()))

# Actual door recess is X=0.07..1.50, Y=+/-0.945, Z=0.029..2.88 m.
# The opaque closure at 1.31 hides spawn positions at X=0.85. The lining
# extends to the opening so an oblique view cannot reveal the lit floor/sides.
back,front,half,floor,ceiling=.075,1.475,.940,.035,2.875
export('SM_ReceptionDoor_BlackLiner',[
    [(back,-half,floor),(back,half,floor),(back,half,ceiling),(back,-half,ceiling)],
    [(back,-half,floor),(front,-half,floor),(front,-half,ceiling),(back,-half,ceiling)],
    [(front,half,floor),(back,half,floor),(back,half,ceiling),(front,half,ceiling)],
    [(back,half,floor),(back,-half,floor),(front,-half,floor),(front,half,floor)],
    [(back,-half,ceiling),(back,half,ceiling),(front,half,ceiling),(front,-half,ceiling)],
    [(1.31,-half,floor),(1.31,half,floor),(1.31,half,ceiling),(1.31,-half,ceiling)],
], 'M_ReceptionDoor_Black')
export('SM_ReceptionDoor_FogCurtain',[
    [(1.425,-half,floor),(1.425,half,floor),(1.425,half,ceiling),(1.425,-half,ceiling)],
], 'M_ReceptionDoor_Fog')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ReceptionDoorVeil.blend'))
(ROOT/'geometry.json').write_text(json.dumps(dict(meshes=records,texture_size=256,source_units='metres'),indent=2),encoding='utf8')
print('RECEPTION_DOOR_VEIL_AUTHORED',len(records),'meshes, 14 triangles, one 256-square texture',flush=True)
