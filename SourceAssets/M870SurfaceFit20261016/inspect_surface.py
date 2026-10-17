import bpy,json,math,sys,gzip
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;P=O.parents[1]
src=P/'SourceAssets/M870GripADS20261016'
bpy.ops.wm.open_mainfile(filepath=str(src/'M870_GripADS_Editable.blend'),use_scripts=False)
if '--candidate' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(O/'M870_ContactCandidate.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene
auth=json.loads((src/'authoring.json').read_text())
if '--candidate' not in sys.argv:
 a=bpy.data.actions[auth['clips']['idle']['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
suffix='before'
if '--candidate' in sys.argv:suffix='candidate'
if '--native' in sys.argv:
 suffix='native'
 d=json.loads(gzip.decompress((P/'SourceAssets/Super90JointSurface20261012/arms_published.json.gz').read_bytes()))
 errors={n:(r.matrix_world@r.data.bones[n].matrix_local.translation-Vector((b['position'][0]/100,-b['position'][1]/100,b['position'][2]/100))).length for n,b in d['bones'].items() if n in r.data.bones}
 print('NATIVE_BIND_POSITION_MAX',max(errors.values()),sorted(errors.items(),key=lambda p:-p[1])[:5],flush=True)
 old=bpy.data.objects['M870_V7'];bpy.data.objects.remove(old,do_unlink=True)
 mesh=bpy.data.meshes.new('NativeBare');mesh.from_pydata([(v[0]/100,-v[1]/100,v[2]/100) for v in d['positions']],[],d['triangles']);mesh.update()
 ob=bpy.data.objects.new('M870_V7',mesh);s.collection.objects.link(ob)
 for p in mesh.polygons:p.use_smooth=True
 for n in {n for w in d['weights'] for n in w}:ob.vertex_groups.new(name=n)
 for i,w in enumerate(d['weights']):
  for n,weight in w.items():ob.vertex_groups[n].add([i],weight,'REPLACE')
 ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4);ob.modifiers.new('Native skin','ARMATURE').object=r
canon=r.data.bones['WPN_root'].matrix_local@r.pose.bones['WPN_root'].matrix.inverted()
# Put all evaluated geometry in the gun's author coordinates for contact views.
dep=bpy.context.evaluated_depsgraph_get();out=[];info={}
for ob in list(s.objects):
 if ob.type!='MESH':continue
 ev=ob.evaluated_get(dep);mesh=bpy.data.meshes.new_from_object(ev);new=bpy.data.objects.new('View_'+ob.name,mesh);s.collection.objects.link(new)
 new.matrix_world=canon@r.matrix_world.inverted()@ev.matrix_world
 mat=bpy.data.materials.new('Review_'+ob.name);mat.diffuse_color=(.61,.30,.18,1) if 'V7' in ob.name else (.055,.065,.075,1)
 mesh.materials.clear();mesh.materials.append(mat)
 for p in mesh.polygons:p.material_index=0
 out.append(new);ob.hide_render=True
 if ob.name=='M870_V7':
  for v in ob.data.vertices:
   groups=[(g.weight,ob.vertex_groups[g.group].name) for g in v.groups]
   if groups:info.setdefault(max(groups)[1],[]).append(v.index)
info={'groups':info,'bones':{b.name:{'p':list((canon@b.matrix).translation),'m':[list(row) for row in canon@b.matrix]} for b in r.pose.bones if b.name.endswith('_l')}}
(O/'surface_inputs.json').write_text(json.dumps(info))
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True
s.render.resolution_x=960;s.render.resolution_y=720;s.render.resolution_percentage=100
if not s.world:s.world=bpy.data.worlds.new('ReviewWorld')
s.world.color=(.26,.26,.26);s.view_settings.view_transform='Standard'
for loc,energy,size in [((-.5,-.2,.1),180,1.5),((.5,.2,-.3),100,1),((0,.8,-.3),100,1)]:
 d=bpy.data.lights.new('ReviewLight','AREA');d.energy=energy;d.shape='DISK';d.size=size;o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,.2,-.77))-o.location).to_track_quat('-Z','Y').to_euler()
ca=bpy.data.cameras.new('ReviewCamera');co=bpy.data.objects.new('ReviewCamera',ca);s.collection.objects.link(co);s.camera=co
for name,eye,target,lens in [('side',(-.48,.10,-.68),(0,.21,-.78),55),('front',(.4,.37,-.65),(0,.2,-.78),55),('under',(-.18,.15,-1.18),(0,.22,-.77),55),('ads',(0,-.262,-.7014),(0,.449,-.70335),32)]:
 co.location=eye;co.rotation_euler=(Vector(target)-co.location).to_track_quat('-Z','Y').to_euler();ca.lens=lens;ca.clip_start=.005
 s.render.filepath=str(O/(name+'_'+suffix+'.png'));bpy.ops.render.render(write_still=True)
print('SURFACE_REVIEW_DONE',flush=True)
