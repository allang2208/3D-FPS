from pathlib import Path
import unreal as u,pickle
r=Path(__file__).resolve().parent;g=pickle.load(open(r/'geometry.pkl','rb'));names=g['names'];mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7');clip=u.load_asset('/Game/Weapons/M249/Bipod/A_M249_Bipod')
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
fps=600;frames=[[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(clip,names,i/fps,False,mesh)] for i in range(round(clip.get_play_length()*fps)+1)]
pickle.dump(dict(names=names,parents=g['parents'],fps=fps,duration=clip.get_play_length(),frames=frames),open(r/'final_saved.pkl','wb'));print('SAVED_BIPOD_READBACK',len(frames),flush=True)
