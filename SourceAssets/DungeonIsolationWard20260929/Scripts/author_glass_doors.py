"""Fitted glazed double door skins, installed as two independent ColdSteelDoor actors.

Local X is thickness, Y is width, Z is height. Jambs are 5 cm, headers 8 cm;
leaf panel thickness is 5 cm, matching the existing hinge contract exactly.
No rendering, simulation, or interaction-system replacement.
"""
import json,math,os
from pathlib import Path
import bpy,bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
paths={
 'BareSteel':'/Game/Dungeons/SeamMetal20260923/Materials/MI_BareSteel',
 'PaintedSteel':'/Game/Dungeons/SeamMetal20260923/Materials/MI_PaintedSteel',
 'Rubber':'/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_Rubber',
 'Glass':'/Game/Dungeons/IsolationWard20260929/Materials/M_WardGlassV2'}
materials={k:bpy.data.materials.new('RS_'+k) for k in paths}
records=[]
EXPORT_KINDS={s for s in os.environ.get('WARD_DOOR_EXPORT_KINDS','').split(',') if s}
previous_records={i['kind']:i for i in json.loads((OUT/'door-manifest.json').read_text('utf8'))['objects']} if EXPORT_KINDS else {}

def block(name,c,size,mat,bevel=.002):
 bpy.ops.mesh.primitive_cube_add(size=1,location=c)
 obj=bpy.context.object;obj.name=name;obj.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 obj.data.materials.append(materials[mat])
 if bevel:
  mod=obj.modifiers.new('Soft manufactured edges','BEVEL');mod.width=bevel;mod.segments=3
  bpy.ops.object.modifier_apply(modifier=mod.name)
 return obj

def cylinder(name,a,b,r,mat):
 axis=Vector(b)-Vector(a)
 bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=r,depth=axis.length,location=(Vector(a)+Vector(b))/2)
 obj=bpy.context.object;obj.name=name;obj.rotation_euler=axis.to_track_quat('Z','Y').to_euler()
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 obj.data.materials.append(materials[mat])
 mod=obj.modifiers.new('Rim radius','BEVEL');mod.width=.001;mod.segments=2
 bpy.ops.object.modifier_apply(modifier=mod.name)
 return obj

def export(kind,parts,boxes):
 if EXPORT_KINDS and kind not in EXPORT_KINDS:
  records.append(previous_records[kind]);return
 name='SM_Ward_'+kind
 bpy.ops.object.select_all(action='DESELECT')
 for o in parts:o.select_set(True)
 bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
 obj=bpy.context.object;obj.name=name
 bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
 mesh=obj.data
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 uv=mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap')
 age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
 for face in mesh.polygons:
  key=mesh.materials[face.material_index].name
  dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
  points=[mesh.vertices[v].co for v in face.vertices]
  for li in face.loop_indices:
   p=mesh.vertices[mesh.loops[li].vertex_index].co
   uv.data[li].uv=tuple((p[k]-min(v[k] for v in points))/max(.0001,max(v[k] for v in points)-min(v[k] for v in points)) for k in dims) if key=='RS_Glass' else tuple(p[k]/.8 for k in dims)
   age.data[li].color=(.13,0,0,1)
 mod=obj.modifiers.new('Triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 colliders=[]
 for i,(c,size) in enumerate(boxes):
  o=block('UCX_'+name+'_'+str(i).zfill(2),c,size,'BareSteel',0);o.data.materials.clear();colliders.append(o)
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
 for o in colliders:o.select_set(True)
 bpy.context.view_layer.objects.active=obj
 fbx=OUT/(name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
                          bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
 for o in colliders:o.hide_set(True);o.hide_render=True;o.select_set(False)
 records.append(dict(name=name,kind=kind,fbx=str(fbx),materials={'RS_'+k:v for k,v in paths.items()},
                     triangles=len(obj.data.polygons),collision=True,collision_boxes=len(boxes),
                     nanite=kind=='GlassDoorFrame',sample_only=False,assembly_only=True))
 print('WARD_DOOR_AUTHORED',name,len(obj.data.polygons),flush=True)

# Preserve the 336 x 312 x 48 cm outer fit and recessed sill. A 326 cm
# throat leaves 3 cm beside each hinge for the 5 cm leaf's swept thickness.
# One closed ring replaces overlapping face strips and touching box end caps.
outer=[(-1.68,-1.56),(1.68,-1.56),(1.68,1.56),(-1.68,1.56)]
inner=[(-1.63,-1.485),(1.63,-1.485),(1.63,1.48),(-1.63,1.48)]
vs=[(x,y,z) for x in (-.24,.24) for ring in (outer,inner) for y,z in ring]
faces=[];roles=[]
for i in range(4):
 j=(i+1)%4
 faces.extend(((i,j,j+4,i+4),(i+8,i+12,j+12,j+8),(i,i+8,j+8,j),(i+4,j+4,j+12,i+12)))
 roles.extend([i%2]*4)
mesh=bpy.data.meshes.new('ContinuousDoorFrame');mesh.from_pydata(vs,[],faces);mesh.update()
obj=bpy.data.objects.new('ContinuousDoorFrame',mesh);bpy.context.collection.objects.link(obj)
mesh.materials.append(materials['BareSteel']);mesh.materials.append(materials['PaintedSteel'])
for polygon,role in zip(mesh.polygons,roles):polygon.material_index=role
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
mod=obj.modifiers.new('Soft manufactured edges','BEVEL');mod.width=.002;mod.segments=3
bpy.ops.object.modifier_apply(modifier=mod.name)
frame=[obj]
frame_boxes=[((0,y,-.0025),(.48,.05,2.965)) for y in (-1.655,1.655)]
# The old sill top shared z=4.2 cm with the finished floor. Embed it 5 mm.
frame_boxes += [((0,0,-1.5225),(.48,3.36,.075)),((0,0,1.52),(.48,3.36,.08))]
export('GlassDoorFrame',frame,frame_boxes)

# One symmetric leaf serves both hinges; right leaf is rotated 180 by the existing actor.
# Blender Y is mirrored by UE import: negative Y is the central handle edge in UE.
leaf=[]
for y in (-.7625,.7625):leaf.append(block('LeafStile',(0,y,0),(.05,.07,2.95),'PaintedSteel'))
for z in (-1.44,1.44):leaf.append(block('LeafRail',(0,0,z),(.05,1.455,.07),'PaintedSteel'))
leaf.append(block('KickPlate',(0,0,-1.27),(.048,1.455,.27),'BareSteel'))
leaf.append(block('SafetyCrossrail',(0,0,-.23),(.05,1.455,.055),'BareSteel'))
# Glass is surrounded by a genuine recessed EPDM gasket, with no overlapping faces.
for y in (-.719,.719):leaf.append(block('VerticalSeal',(0,y,.17),(.027,.017,2.47),'Rubber',.001))
for z in (-1.128,1.394):leaf.append(block('HorizontalSeal',(0,0,z),(.027,1.422,.017),'Rubber',.001))
leaf.append(block('LaminatedGlass',(0,0,.133),(.012,1.42,2.50),'Glass',.0008))
for side in (-1,1):
 x=side*.071
 for z in (-.39,.19):
  # Fasten both pull handles into the surviving 7 cm metal stile, not the pane.
  leaf.append(cylinder('HandleFoot',(side*.024,-.7625,z),(side*.072,-.7625,z),.014,'BareSteel'))
  leaf.append(cylinder('MountRose',(side*.024,-.7625,z),(side*.030,-.7625,z),.023,'BareSteel'))
 leaf.append(cylinder('PullHandle',(x,-.7625,-.39),(x,-.7625,.19),.012,'BareSteel'))
 # Flush bolts and narrow kickplate seams add close-range construction detail.
 for y in (-.68,.68):
  for z in (-1.34,-1.20):leaf.append(cylinder('KickplateFastener',(side*.024,y,z),(side*.026,y,z),.0045,'BareSteel'))
for z in (-1.15,0,1.15):
 leaf.append(cylinder('HingeBarrel',(0,.773,z-.046),(0,.773,z+.046),.021,'BareSteel'))
export('GlassDoorLeaf',leaf,[((0,0,0),(.05,1.595,2.95))])
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'WardGlassDoors.blend'))
(OUT/'door-manifest.json').write_text(json.dumps(dict(objects=records,actor_class='/Script/FPSGAME.ColdSteelDoor',independent_leaves=True,
 frame_member_cm=5,header_member_cm=8,finished_clear_width_cm=326,leaf_half_thickness_cm=2.5,tests_run=False,rendered=False),indent=2),encoding='utf-8')
