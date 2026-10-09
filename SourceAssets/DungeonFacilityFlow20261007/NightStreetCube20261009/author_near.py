"""Physical door reveals, canopy lip and drainage; within the original vestibule."""
from pathlib import Path
import bpy,sys,json,hashlib
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent.parents[1]
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE='/Game/Dungeons/FacilityFlow20261007/NightStreetCube20261009'
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonReceptionHall20261006/Scripts'));import geometry as g
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC';g.ROOM='Portico'
for side in (-1,1):
    # The real return walls cover the close oblique view; the cube supplies all
    # directions through the remaining opening, with no rectangular photo edge.
    g.box('NearPortico',(-25.77,side*1.99,1.76),(2.02,.26,3.24),'Concrete')
    for x in (-24.85,-26.68):
        g.box('NearPortico',(x,side*1.84,1.75),(.24,.34,3.20),'Concrete')
        g.box('NearPortico',(x,side*1.84,.19),(.31,.41,.25),'Paint')
    g.box('NearPortico',(-25.77,side*1.846,.40),(1.59,.024,.24),'Paint')
    g.rounded_pipe('NearPortico',[(-26.45,side*1.76,3.21),(-26.45,side*1.76,.24),(-26.22,side*1.76,.15)],.043,'Steel',16)
    for z in (.7,1.8,2.9):
        g.ring('NearPortico',(-26.45,side*1.76,z),(0,0,1),.053,.043,.024,'Paint',16)
        g.box('NearPortico',(-26.45,side*1.813,z),(.11,.09,.035),'Steel')
g.box('NearPortico',(-26.69,0,3.26),(.21,4.02,.19),'Paint')
g.box('NearPortico',(-26.575,0,3.15),(.018,3.78,.022),'Steel')
for y in (-1.6,-.8,0,.8,1.6):g.bolt('NearPortico',(-26.574,y,3.25),(1,0,0),.012)

data=g.G[(g.ROOM,'NearPortico')];mesh=bpy.data.meshes.new('NearPortico');mesh.from_pydata(data['v'],[],data['f']);mesh.update()
obj=bpy.data.objects.new('SM_ReceptionCube_NearPortico',mesh);bpy.context.collection.objects.link(obj)
paths={'Concrete':'/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete',
 'Paint':'/Game/Dungeons/ReceptionHall20261006/Materials/M_Reception_Teal',
 'Steel':'/Game/Dungeons/SeamMetal20260923/Materials/MI_BareSteel'}
slots=list(dict.fromkeys(data['m']));materials={}
for name in slots:
    mat=bpy.data.materials.new('PC_'+name);mesh.materials.append(mat);materials[mat.name]=paths[name]
uv=mesh.uv_layers.new(name='UVMap')
for face,mat,smooth in zip(mesh.polygons,data['m'],data['smooth']):
    face.material_index=slots.index(mat);face.use_smooth=smooth
    axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(face.normal[a]))]
    for li in face.loop_indices:
        p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]],p[axes[1]])
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bevel=obj.modifiers.new('Physical cast and folded edges','BEVEL');bevel.width=.006;bevel.segments=2
bpy.ops.object.modifier_apply(modifier=bevel.name)
tri=obj.modifiers.new('Triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
file=OUT/(obj.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
records=[dict(name=obj.name,kind='NearPortico',mesh=BASE+'/Meshes/'+obj.name,fbx=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),materials=materials,collision=False,nanite=False,cast_shadow=True,triangles=len(obj.data.polygons))]
# Give the unchanged enclosure its own default cube material, so loading it no
# longer pulls the obsolete photograph in through the old mesh's material slot.
with bpy.data.libraries.load(str(ROOT.parent/'NightStreet20261009/Authored/ReceptionNightStreet.blend'),link=False) as (src,dst):dst.objects=['SM_ReceptionNight_Background']
obj=dst.objects[0];bpy.context.collection.objects.link(obj);obj.name='SM_ReceptionCube_Background'
obj.data.materials.clear();mat=bpy.data.materials.new('PC_Cube');obj.data.materials.append(mat)
for face in obj.data.polygons:face.material_index=0
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
file=OUT/(obj.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
records.append(dict(name=obj.name,kind='Background',mesh=BASE+'/Meshes/'+obj.name,fbx=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),materials={'PC_Cube':BASE+'/Materials/M_Reception_IndustrialNightCube'},collision=False,nanite=False,cast_shadow=False,triangles=len(obj.data.polygons)))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ReceptionPortico.blend'))
(ROOT/'geometry.json').write_text(json.dumps(dict(meshes=records),indent=2),encoding='utf8')
print('RECEPTION_NEAR_PORTICO_AUTHORED')
