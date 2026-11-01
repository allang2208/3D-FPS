from pathlib import Path
O=Path(__file__).resolve().parent
code=(O/'library.py').read_text().replace("OUT/'ue_before.json'", "OUT/'ue_after.json'")
exec(compile(code,'saved_layer_readback','exec'))
expected=json.loads((OUT/'final_poses.json').read_text());result={}
for role,rows in clips.items():
 maximum=0.;root_max=0.;rotation_max=0.;frames=list(ue['clips'][role]['poses'])
 for row,f in zip(rows,frames):
  for n,m in row.items():
   error=(m.translation-Matrix(expected[role][int(f)][n]).translation).length*1000
   if under(n,'clavicle_r'):
    maximum=max(maximum,error);a=m.to_quaternion().rotation_difference(Matrix(expected[role][int(f)][n]).to_quaternion()).angle
    rotation_max=max(rotation_max,math.degrees(min(a,2*math.pi-a)))
   elif n.startswith('WPN_'):root_max=max(root_max,error)
 result[role]={'right_bone_position_error_mm':maximum,'right_bone_rotation_error_deg':rotation_max,'weapon_bone_position_error_mm':root_max,'sampled_frames':len(frames)}
(OUT/'saved_layer_readback.json').write_text(json.dumps(result,indent=2));print('SAVED_READBACK',len(result),max(v['right_bone_position_error_mm'] for v in result.values()),flush=True)
