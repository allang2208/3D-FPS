import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O.parent/'VerticalForegrip20260911/Integration/VerticalForegrip_Refined.blend'));s=bpy.context.scene;ob=bpy.data.objects['SM_VerticalForegrip'];ob.name='SM_CantedForegrip_Concept';R=Matrix.Rotation(math.radians(45),4,'X');pivot=Vector((0,0,-.014))
for v in ob.data.vertices:
 p=v.co*.75
 if p.z<-.014:p=pivot+R@(p-pivot)
 v.co=p
# Consistent current M4 material preview.
for slot in ob.material_slots:slot.material=bpy.data.materials['Body.001']
for x in list(s.objects):
 if x!=ob:bpy.data.objects.remove(x,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'CantedForegrip_Concept.blend'))
d=bpy.data.cameras.new('Camera');c=bpy.data.objects.new('Camera',d);s.collection.objects.link(c);s.camera=c;d.type='ORTHO';d.ortho_scale=.145;d.clip_start=.001;focus=Vector((0,.025,-.043))
world=bpy.data.worlds.new('Studio') if not s.world else s.world;s.world=world;world.use_nodes=True;next(n for n in world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.8,.8,.8,1);next(n for n in world.node_tree.nodes if n.type=='BACKGROUND').inputs[1].default_value=.6
for pos in [(.2,-.3,.35),(-.2,.2,.1)]:
 light=bpy.data.lights.new('Studio','AREA');light.energy=12;light.size=.3;l=bpy.data.objects.new('Studio',light);s.collection.objects.link(l);l.location=pos;l.rotation_euler=(focus-l.location).to_track_quat('-Z','Y').to_euler()
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=900;s.render.resolution_y=900;s.render.resolution_percentage=100;s.render.film_transparent=True
for label,pos,up in [('side',(0,-1,0),'Y'),('front',(-1,0,0),'Y'),('top',(0,0,1),'Y'),('hero',(-.8,1,.5),'Y')]:
 c.location=focus+Vector(pos);c.rotation_euler=(focus-c.location).to_track_quat('-Z',up).to_euler();s.render.filepath=str(O/f'concept_{label}.png');bpy.ops.render.render(write_still=True)
# Orthographic presentation sheet uses the same model, separate orientation per panel.
base=ob.data;ob.hide_render=True
for i,(label,pos) in enumerate([('SIDE',(0,-1,0)),('FROM STOCK - LEFT CANT 45 DEG',(-1,0,0)),('TOP',(0,0,1))]):
 rot=(-Vector(pos)).to_track_quat('-Z','Y').to_matrix().transposed().to_4x4();copy=bpy.data.objects.new(label,base.copy());s.collection.objects.link(copy)
 for v in copy.data.vertices:v.co=rot@(v.co-focus)
 copy.location=(.17*(i-1),0,0)
 font=bpy.data.curves.new(label,'FONT');font.body=label;font.size=.005;font.align_x='CENTER';text=bpy.data.objects.new(label,font);s.collection.objects.link(text);text.location=(.17*(i-1),-.078,0)
c.location=(0,0,1);c.rotation_euler=(0,0,0);d.ortho_scale=.51;s.render.resolution_x=1800;s.render.resolution_y=650;s.render.film_transparent=False;s.render.filepath=str(O/'concept_three_views.png');bpy.ops.render.render(write_still=True)
(O/'concept.json').write_text(json.dumps({'type':'left canted visual game accessory','cant_degrees':45,'source':'Current project vertical grip geometry as editable concept base; new generated candidate not yet complete','three_views':'concept_three_views.png'},indent=2))



