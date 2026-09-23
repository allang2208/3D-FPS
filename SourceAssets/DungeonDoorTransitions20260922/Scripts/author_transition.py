"""Retain the authored narrow entry and build a sealed four-surface expansion to the route socket."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
ROUTES=PROJECT/'SourceAssets/DungeonRoutes20260922'
config=json.loads((ROUTES/'Config/rooms.json').read_text(encoding='utf-8'))
link=next(x for x in config['links'] if x['id']=='Threshold')
depth=config['style']['wall_thickness']
width=link['width']-depth;height=link['height']
# Width in the existing authoring recipe is wall-centre spacing. Connect to its actual inner face.
recipe=dict(length_m=4,transition_start_m=1.4,entry_clear_m=[1.32,2.38],exit_clear_m=[width,height],
            entry_wall_m=.18,exit_wall_m=depth,overlap_m=0,
            mesh='/Game/Dungeons/DoorTransitions20260922/Meshes/SM_StartServiceTransition',
            actor='DGN_Link_A_B',map='/Game/GameMaps/L_Dungeon_Randomized')
(ROOT/'Config').mkdir(exist_ok=True)
(ROOT/'Config/transition.json').write_text(json.dumps(recipe,indent=2))
(ROUTES/'Config/start_connection.json').write_text(json.dumps(recipe,indent=2))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
source=PROJECT/'SourceAssets/DungeonAuthoredExpansion20260922/Authored/AuthoredSpace_Connections.blend'
with bpy.data.libraries.load(str(source),link=False) as (src,dst):dst.objects=['SM_Sample_ServiceLink']
obj=dst.objects[0];bpy.context.scene.collection.objects.link(obj)
obj.name='SM_StartServiceTransition'
bm=bmesh.new();bm.from_mesh(obj.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,
                      plane_co=(0,recipe['transition_start_m'],0),plane_no=(0,1,0),clear_outer=True,clear_inner=False)
bm.to_mesh(obj.data);bm.free();obj.data.update()
materials={m.name.removeprefix('V2_'):m for m in obj.data.materials}
verts=[];faces=[];mats=[];uvs=[]
start=recipe['transition_start_m'];end=recipe['length_m'];over=recipe['overlap_m']
def shape(y):
    t=max(0,min(1,(y-start)/(end-start)))
    return .66+(width/2-.66)*t,2.38+(height-2.38)*t,.18+(depth-.18)*t
def poly(vs,fs,material):
    base=len(verts);verts.extend(vs)
    for f in fs:faces.append(tuple(base+i for i in f));mats.append(material)
def solid(a,b,material):
    # Two same-order cross sections; recalculate normals on the resulting closed solid.
    n=len(a);poly(a+b,[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],material)
def side_section(y,side,z0,z1,offset=0,thickness=None):
    w,h,d=shape(y);z1=min(z1,h)
    a=side*(w+offset);b=side*(w+offset+(d if thickness is None else thickness))
    return [(a,y,z0),(b,y,z0),(b,y,z1),(a,y,z1)]
for side in (-1,1):
    solid(side_section(start,side,0,shape(start)[1]),side_section(end+over,side,0,height),'Concrete')
    # Continuous skirting following the actual sloped side wall.
    solid(side_section(start,side,0,.14,-.026,.026),side_section(end+over,side,0,.14,-.026,.026),'PaintedSteel')
    count=math.ceil((end-start)/.4)
    for iy in range(count):
        y0=start+(end-start)*iy/count+.0035;y1=start+(end-start)*(iy+1)/count-.0035
        for iz in range(9):
            z0=iz*.2+.0035;z1=(iz+1)*.2-.0035
            solid(side_section(y0,side,z0,z1,-.012,.012),side_section(y1,side,z0,z1,-.012,.012),'IvoryTile')
def floor_section(y):
    w,h,d=shape(y);return [(-w-d,y,0),(w+d,y,0),(w+d,y,-.22),(-w-d,y,-.22)]
def ceiling_section(y):
    w,h,d=shape(y);return [(-w-d,y,h),(w+d,y,h),(w+d,y,h+.18),(-w-d,y,h+.18)]
solid(floor_section(start),floor_section(end+over),'Concrete')
solid(ceiling_section(start),ceiling_section(end+over),'Concrete')
# Fixture remains over the preserved narrow section, clear of the rising ceiling.
def box(center,size,material):
    x,y,z=center;a,b,c=[s/2 for s in size]
    solid([(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y-b,z+c),(x-a,y-b,z+c)],
          [(x-a,y+b,z-c),(x+a,y+b,z-c),(x+a,y+b,z+c),(x-a,y+b,z+c)],material)
box((0,.8,2.25),(.55,.18,.07),'BareSteel');box((0,.8,2.205),(.46,.12,.02),'WarmGlass')
mesh=bpy.data.meshes.new('ContinuousDoorTransition');mesh.from_pydata(verts,[],faces);mesh.update()
extension=bpy.data.objects.new('TransitionShell',mesh);bpy.context.scene.collection.objects.link(extension)
names=list(materials)
for name in names:mesh.materials.append(materials[name])
for face,mat in zip(mesh.polygons,mats):face.material_index=names.index(mat)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
uv=mesh.uv_layers.new(name='UVMap')
for face in mesh.polygons:
    axis=max(range(3),key=lambda i:abs(face.normal[i]));dims=[i for i in range(3) if i!=axis]
    for li in face.loop_indices:
        co=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(co[dims[0]]/2,co[dims[1]]/2)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);extension.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
tri=obj.modifiers.new('ExportTriangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
fbx=OUT/(obj.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StartServiceTransition.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=[dict(name=obj.name,fbx=str(fbx),materials={m.name:'/Game/Dungeons/AtmosphereV2/Materials/M_'+m.name.removeprefix('V2_') for m in obj.data.materials})]),indent=2))
print('START_TRANSITION_AUTHORED',recipe['entry_clear_m'],recipe['exit_clear_m'])
