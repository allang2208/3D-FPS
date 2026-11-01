"""Read the two saved animation data models at their own sample rate."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
native=json.loads((P/'native-mesh.json').read_text());bones=native['bones'];names=list(bones)
def tr(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
poses={};meta={}
for kind in ['Charge','Release']:
 path='/Game/Weapons/ThunderGodHammer20261028/JiLeiSeatV1/A_ThunderHammer_Call'+kind
 seq=u.load_asset(path);model=seq.get_editor_property('data_model_interface');rate=model.get_frame_rate();fps=rate.numerator/rate.denominator
 frames=[]
 for i in range(model.get_number_of_keys()):
  local=dict(zip(names,u.AnimationLibrary.get_bone_poses_for_time(seq,names,i/fps,False,mesh)));comp={}
  for n in names:comp[n]=local[n].multiply(comp[bones[n]['parent']]) if bones[n]['parent'] else local[n]
  frames.append([tr(comp[n]) for n in names])
 poses[kind]={'names':names,'fps':fps,'frames':frames}
 meta[kind]={'asset':path,'fps':fps,'keys':len(frames),'same_skeleton':seq.get_editor_property('skeleton')==mesh.get_editor_property('skeleton')}
(P/'native-poses.json').write_text(json.dumps(poses,separators=(',',':')))
(P/'readback-receipt.json').write_text(json.dumps({'complete':True,'sequences':meta,'runtime_tested':False},indent=2))
print('JILEI_V4_SAVED_POSES_READ',flush=True)
