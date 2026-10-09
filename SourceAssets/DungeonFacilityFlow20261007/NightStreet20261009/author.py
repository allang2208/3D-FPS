"""Closed reception entrance: repaired printed faces and bounded street scenery.
Production modelling/export only. No render, game launch or acceptance test.
"""
from pathlib import Path
import bpy,bmesh,json,sys,hashlib,copy
ROOT=Path(__file__).resolve().parent;FLOW=ROOT.parent;PROJECT=FLOW.parents[1]
HALL=PROJECT/'SourceAssets/DungeonReceptionHall20261006'
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE='/Game/Dungeons/FacilityFlow20261007/NightStreet20261009'
sys.path.insert(0,str(HALL/'Scripts'));import geometry as g
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
records=[]

def export(obj,kind,materials,collision=False,hulls=(),shadow=True):
    obj.name='SM_ReceptionNight_'+kind
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    # Do not recalculate disconnected printed-face islands: there is no coherent
    # enclosed volume from which Blender could infer their intended front side.
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    colliders=[]
    for i,(vs,fs) in enumerate(hulls):
        mesh=bpy.data.meshes.new('UCX_'+obj.name+'_%03d'%i);mesh.from_pydata(vs,[],fs);mesh.update()
        co=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(co);co.select_set(True);colliders.append(co)
    file=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
    for co in colliders:co.hide_set(True);co.hide_render=True
    records.append(dict(name=obj.name,kind=kind,mesh=BASE+'/Meshes/'+obj.name,fbx=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),materials=materials,collision=collision,nanite=False,cast_shadow=shadow,triangles=len(obj.data.polygons)))

source=FLOW/'FrontEntry20261008'
with bpy.data.libraries.load(str(source/'Authored/FrontEntry.blend'),link=False) as (src,dst):dst.objects=['SM_FrontEntry_Signs']
obj=dst.objects[0];bpy.context.collection.objects.link(obj)
bm=bmesh.new();bm.from_mesh(obj.data);changed=0
for face in bm.faces:
    p=face.calc_center_median()
    if -22.92<p.x<-22.90 and abs(abs(p.y)-4.8)<.4 and .9<p.z<1.9 and obj.data.materials[face.material_index].name.startswith('RH_Labels'):
        if face.normal.x<0:face.normal_flip();changed+=1
bm.to_mesh(obj.data);bm.free();obj.data.update()
sign_materials=next(m['materials'] for m in json.loads((source/'geometry.json').read_text('utf8'))['meshes'] if m['kind']=='Signs')
export(obj,'Signs',sign_materials,shadow=False)

g.ROOM='NightStreet'
MATS={
    'Asphalt':BASE+'/Materials/M_NightStreet_Asphalt',
    'Concrete':'/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete',
    'Steel':'/Game/Dungeons/SeamMetal20260923/Materials/MI_BareSteel',
    'DarkSteel':'/Game/Dungeons/ReceptionHall20261006/Materials/M_Reception_Teal',
    'Background':BASE+'/Materials/M_NightStreet_Background',
}
# A 2.1 m approach stays inside the old 3 m vestibule. The gate remains the
# gameplay barrier, so these inaccessible set-dressing pieces need no collision.
g.box('Forecourt',(-25.59,0,.018),(2.12,3.94,.036),'Asphalt')
for side in (-1,1):
    # Raised kerb with real expansion joints; restrained geometry behind grille.
    for i in range(4):
        g.box('Forecourt',(-24.80-i*.49,side*1.79,.066),(.482,.24,.132),'Concrete')
    g.box('Drain',(-25.59,side*1.62,.025),(2.09,.09,.018),'DarkSteel')
    for i in range(42):
        g.box('Drain',(-24.575-i*.0495,side*1.62,.041),(.018,.085,.012),'Steel')
# The narrow transverse drainage channel bridges the threshold to wet asphalt.
g.box('Drain',(-24.575,0,.043),(.10,3.22,.014),'DarkSteel')
for i in range(66):g.box('Drain',(-24.575,-1.59+i*.0482,.055),(.087,.012,.011),'Steel')
# Four inward faces share a view-projected image, so lateral views see the same
# distant street instead of revealing the original shallow white room.
# Retain the existing roof and lamp as a short entrance canopy. The side image
# surfaces sit in front of the old side trims, with positive depth separation.
x0,x1=-24.525,-26.985;y0,y1=-1.94,1.94;z0,z1=.012,3.395
g.poly('Background',[(x1,y0,z0),(x1,y1,z0),(x1,y1,z1),(x1,y0,z1)],[(0,1,2,3)],'Background')
g.poly('Background',[(x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)],[(0,1,2,3)],'Background')
g.poly('Background',[(x1,y1,z0),(x0,y1,z0),(x0,y1,z1),(x1,y1,z1)],[(0,1,2,3)],'Background')
g.poly('Background',[(x1,y0,z0),(x0,y0,z0),(x0,y1,z0),(x1,y1,z0)],[(0,1,2,3)],'Background')

for (room,kind),data in g.G.items():
    mesh=bpy.data.meshes.new(kind);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
    obj=bpy.data.objects.new(kind,mesh);bpy.context.collection.objects.link(obj)
    slots=list(dict.fromkeys(data['m']));materials={}
    for name in slots:
        mat=bpy.data.materials.new('NS_'+name);mesh.materials.append(mat);materials[mat.name]=MATS[name]
    uv=mesh.uv_layers.new(name='UVMap')
    for face,material in zip(mesh.polygons,data['m']):
        face.material_index=slots.index(material)
        axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(face.normal[a]))]
        for li in face.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]],p[axes[1]])
    if kind=='Forecourt':
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        bevel=obj.modifiers.new('Cast kerb edge bevels','BEVEL');bevel.width=.006;bevel.segments=2
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    export(obj,kind,materials,shadow=kind!='Background')

bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ReceptionNightStreet.blend'))
(ROOT/'geometry.json').write_text(json.dumps(dict(meshes=records,corrected_printed_triangles=changed,street_inside_existing_bounds=True),indent=2),encoding='utf8')
print('RECEPTION_NIGHT_AUTHORED',len(records),'meshes; repaired printed faces:',changed)
