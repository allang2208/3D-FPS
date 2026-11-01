from pathlib import Path
OUT=Path(__file__).resolve().parent
code=(OUT.parent/'M24GripFinish20261028/library.py').read_text()
exec(compile(code,'current_m24_library','exec'))
bpy.ops.wm.open_mainfile(filepath=str(OUT.parent/'M24Thumb20261028/M24_Thumb_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms']
thumb_names=['thumb_01_r','thumb_02_r','thumb_03_r']
def set_pose(row):
 r.animation_data_clear()
 for n,m in row.items():
  loc=row[parents[n]].inverted()@m if parents[n] else m
  r.pose.bones[n].matrix_basis=local_rest[n].inverted()@loc
 bpy.context.view_layer.update()
def thumb(row,bases):
 out={n:m.copy() for n,m in row.items()}
 for n,b in zip(thumb_names,bases):
  loc=row[parents[n]].inverted()@row[n]
  out[n]=out[parents[n]]@Matrix.LocRotScale(loc.translation,local_rest[n].to_quaternion()@b,loc.to_scale())
 return out
def Q(x=0,y=0,z=0):
 return Quaternion((0,0,1),math.radians(z))@Quaternion((0,1,0),math.radians(y))@Quaternion((1,0,0),math.radians(x))
