"""Remove the empty-reload whole-assembly tuck, retaining every local contact."""
from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'source_motion.py').read_text().split("if __name__=='__main__':")[0],'current M24 source','exec'))
import copy
patch={};report=dict(scope='empty reload base and mag10 only',bone='VM_Root',
    source_window_frames=[55,105],fps=30,sample_rate=120,ordinary_reload_changed=False,
    rotations_changed=False,local_hand_tracks_changed=False,mechanical_timing_changed=False,runtime_tested=False)
for family,role in (('base','reload_empty'),('mag10','reload_empty_mag10')):
    data=D['clips'][role];clip=next(c for c in D['profiles'][family]['clips'] if c['base']==data['path'])
    old=next((t for t in clip['tracks'] if t['bone']=='VM_Root'),None)
    anchor=compose(role,55)['WPN_root'].translation
    times=set(old['times'] if old else [0.,clip['duration']])
    times.update(i/120 for i in range(55*4,105*4+1))
    times=sorted(times);values=[]
    for t in times:
        v=sample(old,t,10,'values') if old else [0.,0.,0.,0.,0.,0.,1.,0.,0.,0.]
        if 55/30<t<105/30:
            # VM_Root is the actual skeleton root. A component-space translation
            # here moves the gun, hands, elbows and shoulders as one rigid group.
            # All descendant local rotations/translations and joint lengths stay.
            offset=anchor-compose(role,t*30)['WPN_root'].translation
            v[:3]=list(Vector(v[:3])+offset)
        values.extend(v)
    patch[family]=dict(base=data['path'],duration=clip['duration'],
        track=dict(bone='VM_Root',times=times,values=values),previous=old)
(O/'translation_patch.json').write_text(json.dumps(patch),encoding='utf-8')
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_EMPTY_RELOAD_TUCK_REMOVED_IN_AUTHOR_DATA',flush=True)
