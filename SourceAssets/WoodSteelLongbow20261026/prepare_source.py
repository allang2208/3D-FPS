"""Archive the supplied GLB and expose its authored geometry for part selection."""
import bpy, json, shutil, hashlib, struct
from pathlib import Path
from mathutils import Vector
from collections import defaultdict

P=Path(__file__).parent
SRC=Path(r'C:\Users\allan\Downloads\Meshy_AI_Ancient_Elven_Longbow_1026044130_texture.glb')
for name in ('Source','Textures','Export','Icons','Authoring'):
    (P/name).mkdir(exist_ok=True)
copy=P/'Source'/SRC.name
if not copy.exists(): shutil.copy2(SRC,copy)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.import_scene.gltf(filepath=str(copy))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
obj.name='Source_AncientElvenLongbow'
for im in bpy.data.images:
    if im.packed_file:
        im.filepath_raw=str(P/'Textures'/(im.name.replace('/','_')+'.png'))
        im.file_format='PNG';im.save();im.unpack(method='USE_ORIGINAL')

# Weld only in the connectivity map. Source geometry, corners and UVs stay intact.
parents=list(range(len(obj.data.vertices)))
def root(i):
    while parents[i]!=i:
        parents[i]=parents[parents[i]];i=parents[i]
    return i
def union(a,b):
    a,b=root(a),root(b)
    if a!=b:parents[b]=a
positions={}
for v in obj.data.vertices:
    key=tuple(round(c,6) for c in v.co)
    if key in positions:union(v.index,positions[key])
    else:positions[key]=v.index
for edge in obj.data.edges:union(*edge.vertices)
groups=defaultdict(list)
for v in obj.data.vertices:groups[root(v.index)].append(v.index)
records=[]
for ids in sorted(groups.values(),key=len,reverse=True):
    xyz=[obj.data.vertices[i].co for i in ids]
    records.append({'vertices':len(ids),'min':[min(v[i] for v in xyz) for i in range(3)],
                    'max':[max(v[i] for v in xyz) for i in range(3)],'sample_indices':ids[:6]})
sections=[]
for z in [-.9,-.7,-.5,-.3,-.2,-.15,-.1,-.05,0,.05,.1,.15,.2,.3,.5,.7,.9]:
    xyz=[v.co for v in obj.data.vertices if abs(v.co.z-z)<.012]
    if xyz:sections.append({'z':z,'n':len(xyz),'bounds':[[min(v[i] for v in xyz),max(v[i] for v in xyz)] for i in range(3)]})
info={'source':str(SRC),'sha256':hashlib.sha256(copy.read_bytes()).hexdigest(),
      'vertices':len(obj.data.vertices),'triangles':sum(len(f.vertices)-2 for f in obj.data.polygons),
      'bounds':[list(obj.bound_box[0]),list(obj.bound_box[6])],
      'components':records,'sections':sections,
      'textures':[{'name':im.name,'path':im.filepath,'size':list(im.size)} for im in bpy.data.images if im.type=='IMAGE'],
      'license':'User-supplied Meshy output; retained locally. Redistribution not assumed.'}
(P/'source_geometry.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Source/Longbow_Original.blend'))

# Model authoring references to locate the existing rest and string in the source.
scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='TEXTURE'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.background_type='WORLD'
scene.world=bpy.data.worlds.new('AuthoringWorld');scene.world.color=(.16,.16,.16)
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
data=bpy.data.cameras.new('AuthoringCamera');data.type='ORTHO'
cam=bpy.data.objects.new('AuthoringCamera',data);scene.collection.objects.link(cam);scene.camera=cam
for name,center,eye,scale,size in [
    ('source_side',(0,0,0),(0,-5,0),2.12,(600,1400)),
    ('source_grip',(-.07,0,0),(-1.5,-3,1),.46,(1200,1200))]:
    center=Vector(center);cam.location=center+Vector(eye)
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
    scene.render.resolution_x,scene.render.resolution_y=size
    scene.render.filepath=str(P/'Authoring'/(name+'.png'))
    bpy.ops.render.render(write_still=True)
print(json.dumps({'components':records[:12],'sections':sections,'textures':info['textures']},indent=2))
