import bpy,json,gzip
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
code=(O/'author_reload_contact.py').read_text().split('UC=O.parent')[0]
exec(compile(code,str(O/'author_reload_contact.py'),'exec'))
# Exploratory S90 donor inspection only. Production uses the UC right hand.
from mathutils import Quaternion
D=json.loads((BASE/'Donor/animation_inputs.json').read_text())
A=json.loads((O.parent/'Super90QuickMelee20261008/LeftArmR5/author_space.json').read_text())
Ci=Matrix(A['conversion']['C']).inverted();E=Matrix(A['conversion']['E']);Ki={n:Matrix(m).inverted() for n,m in A['conversion']['K'].items()}
def matrix(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:]))
def decode(row):
 w={}
 for n in D['names']:w[n]=w.get(D['parents'][n],I)@matrix(row[n])
 return {n:E@Ci@w[n]@Ki[n] for n in rest}
for ob in list(s.objects):
 if ob.type=='MESH' and ob.name!='M870_ReloadShell':bpy.data.objects.remove(ob,do_unlink=True)
shell=bpy.data.objects['M870_ReloadShell'];shell.hide_render=False;shell.color=(.8,.03,.02,1)
d=json.loads(gzip.decompress((O.parent/'M870SurfaceFit20261016/native_arms.json.gz').read_bytes()))
mesh=bpy.data.meshes.new('NativeArms');mesh.from_pydata([(v[0]/100,-v[1]/100,v[2]/100) for v in d['vertices']],[],d['faces']);mesh.update()
ob=bpy.data.objects.new('NativeArms',mesh);s.collection.objects.link(ob);ob.color=(.65,.35,.20,1)
for p in mesh.polygons:p.use_smooth=True
for n in {n for w in d['weights'] for n in w}:ob.vertex_groups.new(name=n)
for i,w in enumerate(d['weights']):
 for n,v in w.items():ob.vertex_groups[n].add([i],v,'REPLACE')
ob.parent=r;ob.matrix_parent_inverse=I;ob.matrix_basis=I;ob.modifiers.new('Native','ARMATURE').object=r
r.animation_data.action=None
camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(camera);s.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=.30
s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='OBJECT';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.render.resolution_x=960;s.render.resolution_y=720;s.render.resolution_percentage=100
out=[]
raw=decode(D['clips']['reload_continuous']['rows'][30]);mir=Matrix.Diagonal(Vector((-1,1,1,1)));mapped={};errors=[]
for n in rest:
 if not under(n,'hand_r'):continue
 dn=n[:-2]+'_l';mp=mir@raw[dn]@mir;mb=mir@rest[dn]@mir
 q=mp.to_quaternion()@mb.to_quaternion().inverted()@rest[n].to_quaternion()
 p=mp.translation if n=='hand_r' else (mapped[parents[n]]@local_rest[n]).translation
 mapped[n]=Matrix.LocRotScale(p,q,Vector((1,1,1)))
 errors.append([n,(p-mp.translation).length,((raw[parents[dn]].inverted()@raw[dn]).translation-local_rest[dn].translation).length if dn!='hand_l' else 0])
print('MIRROR_JOINT_ERRORS',errors,flush=True)
print('NATIVE_BIND_HANDS',[(n,list(rest[n].translation)) for n in ('hand_l','hand_r')],flush=True)
for frame in (18,24,30,36,40,44,48,54):
 raw=decode(D['clips']['reload_continuous']['rows'][frame])
 for n in rest:
  local=raw[parents[n]].inverted()@raw[n] if parents[n] else raw[n]
  r.pose.bones[n].matrix_basis=local_rest[n].inverted()@local
 bpy.context.view_layer.update()
 centre=raw['WPN_Shell']@Vector((0,.02948,0))
 out.append({'frame':frame,'shell_in_left':list(raw['hand_l'].inverted()@centre),'shell_in_right':list(raw['hand_r'].inverted()@centre)})
 if frame in (30,40,44):
  camera.location=centre+Vector((.28,-.35,.30));camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler()
  s.render.filepath=str(O/f'donor_{frame}.png');bpy.ops.render.render(write_still=True)
(O/'donor_contact.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
