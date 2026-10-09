"""Repair reception facade seams, signs and moved lounge assemblies in place.
Only derived meshes are exported. The accepted iron grille is reused unchanged.
"""
from pathlib import Path
import bpy,bmesh,json,sys,hashlib,math,copy
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;FLOW=ROOT.parent;PROJECT=FLOW.parents[1]
HALL=PROJECT/'SourceAssets/DungeonReceptionHall20261006';REFINE=HALL/'Refine20261007'
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE='/Game/Dungeons/FacilityFlow20261007/FrontEntry20261008'
sys.path.insert(0,str(HALL/'Scripts'));import geometry as g
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
records=[]

def export(obj,kind,materials,collision=False,nanite=True,hulls=()):
    obj.name='SM_FrontEntry_'+kind
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    colliders=[]
    for i,(vs,fs) in enumerate(hulls):
        mesh=bpy.data.meshes.new('UCX_'+obj.name+'_%03d'%i);mesh.from_pydata(vs,[],fs);mesh.update()
        co=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(co);co.select_set(True);colliders.append(co)
    file=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
    for co in colliders:co.hide_set(True);co.hide_render=True
    records.append(dict(name=obj.name,kind=kind,mesh=BASE+'/Meshes/'+obj.name,fbx=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),materials=materials,collision=collision,nanite=nanite,cast_shadow=kind!='Signs',triangles=len(obj.data.polygons)))
    print('FRONT_ENTRY_EXPORTED',kind,flush=True)

source_manifest=json.loads((REFINE/'geometry.json').read_text('utf8'))['meshes']
for source,kind in [('SM_RH2_Signs','Signs'),('SM_RH2_Hardware','Mounts'),('SM_RH2_LoungeDetails','LoungeDetails')]:
    with bpy.data.libraries.load(str(REFINE/'Authored/ReceptionRefine.blend'),link=False) as (src,dst):dst.objects=[source]
    obj=dst.objects[0];bpy.context.collection.objects.link(obj)
    for vertex in obj.data.vertices:
        x,y,z=vertex.co
        if kind in ('Signs','Mounts'):
            # Retain the previously approved waiting-card relocation at the breach.
            if -19.6<x<-15.8 and y<-16.4 and 1.95<z<3.25:vertex.co.x+=8.7
            # Rotate the two west directory faces and their fasteners as rigid
            # assemblies around the stand centre; UVs and text ratio are untouched.
            elif -23.3<x<-22.7 and .7<z<2.0 and abs(abs(y)-4.8)<.6:
                cy=4.8 if y>0 else -4.8
                vertex.co.x=-46-x;vertex.co.y=2*cy-y
            # The return sign previously entered the mezzanine underside at 4.12 m.
            # Uniform scaling fits the entire printed card between lintel and slab.
            elif -24.0<x<-23.5 and abs(y)<1.7 and 3.35<z<4.5:
                vertex.co=Vector((-23.73,0,3.80))+(vertex.co-Vector((-23.79,0,3.92)))*(1.9/3.2)
        else:
            # Move the matching tray, papers and cup with each relocated coffee table.
            for oldx,newy in [(-20.7,-10.5),(-16.9,10.5)]:
                if abs(x-oldx)<.9 and abs(y+13.55)<.5 and 0<z<.7:
                    vertex.co.x=-21.15+(y+13.55);vertex.co.y=newy-(x-oldx);break
    obj.data.update()
    record=next(m for m in source_manifest if m['name']==source)
    export(obj,kind,copy.deepcopy(record['materials']),nanite=kind!='Signs')

# New manufactured reveals for both openings. Header soffits are 35 mm below
# the concrete/vestibule ceiling plane, with end-to-end rather than overlapping
# joints at the jambs. Replaces the old complete PortalFrames group.
g.ROOM='FrontEntry'
for x,width,height in [(-24,4,3.4),(24,3,3)]:
    bottom=height-.035
    for side in (-1,1):
        g.box('PortalFrames',(x,side*(width/2-.025),bottom/2),(.49,.08,bottom),'Teal',collision=True)
    g.box('PortalFrames',(x,0,(bottom+height+.08)/2),(.49,width+.16,height+.08-bottom),'Teal',collision=True)
data=g.G[(g.ROOM,'PortalFrames')]
mesh=bpy.data.meshes.new('PortalFrames');mesh.from_pydata(data['v'],[],data['f']);mesh.update()
obj=bpy.data.objects.new('PortalFrames',mesh);bpy.context.collection.objects.link(obj)
mat=bpy.data.materials.new('FE_Teal');mat.diffuse_color=(.032,.077,.07,1);mesh.materials.append(mat)
uv=mesh.uv_layers.new(name='UVMap');color=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
for face in mesh.polygons:
    axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(face.normal[a]))]
    for li in face.loop_indices:
        p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]],p[axes[1]]);color.data[li].color=(.06,0,0,1)
export(obj,'PortalFrames',{'FE_Teal':'/Game/Dungeons/ReceptionHall20261006/Materials/M_Reception_Teal'},True,True,g.C[(g.ROOM,'PortalFrames')])
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FrontEntry.blend'))
(ROOT/'geometry.json').write_text(json.dumps(dict(meshes=records),indent=2),encoding='utf8')
