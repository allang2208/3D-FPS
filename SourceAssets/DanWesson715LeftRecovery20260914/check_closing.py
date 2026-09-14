"""User-requested inspection, limited to the altered close/regrip intervals."""
import bpy, json, math
from pathlib import Path
_check_dir=Path(__file__).resolve().parent
__file__=str(_check_dir/'author_actions.py')
_saved_name=__name__;__name__='closing_inspection'
exec(compile(Path(__file__).read_text(encoding='utf-8'),__file__,'exec'),globals())
__name__=_saved_name

def angle(a,b):
    return math.degrees(a.to_quaternion().rotation_difference(b.to_quaternion()).angle)%360

report={'scope':'27 closing intervals at 120Hz; source pose only, not PIE or audio testing','clips':{}}
for start in range(6):
    for count in range(1,7-start):
        kind=f'single_{start}_{count}';begin=EMPTY_BEGIN if start==0 else BEGIN;close=begin+count*STEP
        report['clips'][kind]={'start':close-.20,'close':close,'end':close+TAIL,'start_live':start,'count':count}
    report['clips'][f'speed_{start}']={'start':2.53*(3.85/3.6 if start==0 else 1), 'close':2.68*(3.85/3.6 if start==0 else 1),
                                    'end':3.85 if start==0 else 3.6,'start_live':start}
for kind,row in report['clips'].items():
    speed=kind.startswith('speed');start=row['start_live'];count=row.get('count',1)
    old=lambda t: _natural_speed(start,t) if speed else _natural_single(start,count,t)
    new=lambda t: pose_speed(start,t) if speed else pose_single(start,count,t)
    duration=row['end']-row['start'];n=math.ceil(duration*120)
    max_preserved=0.;old_swing=[];new_swing=[];old_angles=[];new_angles=[];last_old=None;last_new=None
    for i in range(n+1):
        t=row['start']+duration*i/n;a=old(t);b=new(t)
        for name in names:
            if (name.startswith('WPN_') and name!='WPN_Loader') or name.endswith('_r'):
                max_preserved=max(max_preserved,max(abs(a[name][r][c]-b[name][r][c]) for r in range(4) for c in range(4)))
        if row['close']<=t<=row['close']+.55:
            old_swing.append(a['hand_l'].translation.z);new_swing.append(b['hand_l'].translation.z)
            if last_old is not None:
                old_angles.append(min(angle(last_old,a['hand_l']),360-angle(last_old,a['hand_l']))/(duration/n))
                new_angles.append(min(angle(last_new,b['hand_l']),360-angle(last_new,b['hand_l']))/(duration/n))
        last_old=a['hand_l'];last_new=b['hand_l']
    end_old=old(row['end']);end_new=new(row['end']);entry_old=old(row['start']);entry_new=new(row['start'])
    row.update({'right_and_mechanics_matrix_max_delta':max_preserved,
                'entry_hand_gap_mm':(entry_old['hand_l'].translation-entry_new['hand_l'].translation).length*1000,
                'end_hand_gap_mm':(end_old['hand_l'].translation-end_new['hand_l'].translation).length*1000,
                'old_close_left_z_range_mm':(max(old_swing)-min(old_swing))*1000,
                'new_close_left_z_range_mm':(max(new_swing)-min(new_swing))*1000,
                'old_close_left_peak_deg_s':max(old_angles),'new_close_left_peak_deg_s':max(new_angles)})
(_check_dir/'closing-inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DW715_CLOSE_INSPECTION_COMPLETE',len(report['clips']),flush=True)
