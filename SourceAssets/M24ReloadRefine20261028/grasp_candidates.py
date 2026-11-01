from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'reload_library','exec'))
setup_render();folder=O/'Candidates';folder.mkdir(exist_ok=True)
def Q(x=0,y=0,z=0):return Quaternion((0,0,1),math.radians(z))@Quaternion((0,1,0),math.radians(y))@Quaternion((1,0,0),math.radians(x))
base=clips['reload'][24];mag=base['WPN_Magazine']@rest['WPN_Magazine'].inverted()
for degrees in (0,45,75,90):
 row=clone(base);pivot=Vector((.01,.190,.005));D=mag@Matrix.Translation(pivot)@Matrix.Rotation(math.radians(degrees),4,'Z')@Matrix.Translation(-pivot)@mag.inverted()
 for n in names:
  if under(n,'hand_l'):row[n]=D@base[n]
 for finger in ('index','middle','ring','pinky','thumb'):
  n=finger+'_03_l';loc=base[parents[n]].inverted()@base[n]
  row[n]=row[parents[n]]@Matrix.LocRotScale(loc.translation,local_rest[n].to_quaternion()@Q(z=12 if finger=='thumb' else 28),loc.to_scale())
 for view in ('left','right','bottom'):show(row,folder/f'distal_{degrees}_{view}.png',view)
print('M24_GRASP_CANDIDATES_SAVED',flush=True)
