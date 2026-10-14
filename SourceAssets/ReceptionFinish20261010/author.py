"""Reuse the approved shrine breach and author only its hall interfaces."""
from pathlib import Path
import bpy,bmesh,json,sys,hashlib
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
sys.path.insert(0,str(ROOT))
from concrete_mesh import prepare_concrete,project_uv
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE='/Game/Dungeons/ReceptionFinish20261010'
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonReceptionHall20261006/Scripts'))
import geometry as g
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
g.ROOM='ReceptionFinish'
roles=json.loads((PROJECT/'SourceAssets/DungeonReceptionHall20261006/Config/materials.json').read_text('utf8'))
paths={k:v['existing_ue_path'] for k,v in roles.items()}
paths.update(BareSteel='/Game/Dungeons/SeamMetal20260923/Materials/MI_BareSteel')
records=[]

def export(obj,kind,mapping,collision=False):
    obj.name='SM_ReceptionFinish_'+kind
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    mod=obj.modifiers.new('Final triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.data.update()
    if kind=='BreachConcrete':prepare_concrete(obj.data)
    # Project after triangulation to preserve tangent bases on the fractured cut.
    project_uv(obj.data)
    path=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
    records.append(dict(name=obj.name,kind=kind,mesh=BASE+'/Meshes/'+obj.name,fbx=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),materials=mapping,collision=collision,nanite=True,cast_shadow=True,triangles=len(obj.data.polygons)))

# Exact approved source meshes, with their layered fracture and separate steel.
source=PROJECT/'SourceAssets/DungeonShrineV2_20260927/Authored/ShrineRoomV2_Editable.blend'
with bpy.data.libraries.load(str(source),link=False) as (src,dst):
    dst.objects=['SM_ShrineV2_EntranceConcrete','SM_ShrineV2_EntranceRebar']
sx=4.7/3.8;sz=3.55/3.3
left=-18.8-3.25*sx;right=-18.8+3.25*sx;top=4.56*sz
shrine_materials=dict(Concrete='/Game/Dungeons/AtmosphereV2/Materials/M_Concrete',
    FractureConcrete='/Game/Dungeons/WallUpgrade20260924/Materials/MI_BrokenConcrete',
    ServicePaint='/Game/Dungeons/AtmosphereV2/Services/Materials/M_Service_Paint',
    ServiceHardware='/Game/Dungeons/CombatExpansion20260922/Materials/M_PipeCutSteel')
for obj in dst.objects:
    bpy.context.collection.objects.link(obj)
    kind='BreachConcrete' if 'Concrete' in obj.name else 'BreachRebar'
    for v in obj.data.vertices:
        v.co.x=-18.8+(v.co.x-3.25)*sx;v.co.y-=16.66;v.co.z*=sz
    export(obj,kind,{mat.name:shrine_materials[mat.name] for mat in obj.data.materials},kind=='BreachConcrete')

# The rest of the outer walls retain their original envelope. The old fractured
# panel is replaced, not covered by a second solid wall behind the new opening.
for side in (-1,1):
    if side==1:g.box('OuterWalls',(0,16.66,5),(48.6,.32,10),'Concrete')
    for x,width in ((-24,4),(24,3)):
        span=16.5-width/2
        g.box('OuterWalls',(x,side*(width/2+span/2),5),(.36,span,10),'Concrete')
for x,width,height in ((-24,4,3.4),(24,3,3)):
    g.box('OuterWalls',(x,0,(height+10)/2),(.36,width,10-height),'Concrete')
for lo,hi in ((-24.3,left),(right,24.3)):
    g.box('OuterWalls',((lo+hi)/2,-16.66,5),(hi-lo,.32,10),'Concrete')
g.box('OuterWalls',((left+right)/2,-16.66,(top+10)/2),(right-left,.32,10-top),'Concrete')

# Thin mounting pads close the 1.7 cm offset required to align the supplementary
# diffuser undersides with the original corridor light plane at 377.8 cm.
for side in (-1,1):
    for x in (-14,-2,12):
        for dx in (-.46,.46):g.box('GalleryMounts',(x+dx,side*13.25,4.1115),(.13,.14,.017),'Steel')

# Hall vent now meets the gallery slab (4.12 m) and the actual wall at Y=16.50 m.
# A four-sided collar and wall fixing rails make the connection legible.
cx,cy=-5.4,15.81
for side in (-1,1):
    g.box('VentMounts',(cx+side*.715,cy,4.105),(.07,1.50,.05),'BareSteel')
    g.box('VentMounts',(cx,cy+side*.715,4.105),(1.36,.07,.05),'BareSteel')
    g.box('VentMounts',(cx+side*.725,16.475,3.43),(.095,.07,1.42),'Teal')
    for z in (2.87,3.47,4.04):
        g.bolt('VentMounts',(cx+side*.725,16.433,z),(0,-1,0),.012)
for z in (2.765,4.095):g.box('VentMounts',(cx,16.475,z),(1.54,.07,.09),'Teal')

for (_,kind),data in g.G.items():
    mesh=bpy.data.meshes.new(kind);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
    order=list(dict.fromkeys(data['m']))
    for role in order:
        mat=bpy.data.materials.get('RF_'+role) or bpy.data.materials.new('RF_'+role)
        mesh.materials.append(mat)
    for face,role in zip(mesh.polygons,data['m']):face.material_index=order.index(role)
    obj=bpy.data.objects.new(kind,mesh);bpy.context.collection.objects.link(obj)
    export(obj,kind,{'RF_'+role:paths[role] for role in order},kind=='OuterWalls')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ReceptionFinish.blend'))
(ROOT/'geometry.json').write_text(json.dumps(dict(meshes=records,shrine_source=str(source),breach_width_m=4.7,breach_height_m=3.55,source_wall_thickness_m=.55),indent=2),encoding='utf8')
print('RECEPTION_FINISH_AUTHORED',len(records))
