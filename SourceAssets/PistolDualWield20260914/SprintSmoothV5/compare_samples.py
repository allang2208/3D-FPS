"""Compare the two actual UE pose captures; no game/profile writes."""
import json, math
from pathlib import Path

O=Path(__file__).parent
old=json.loads((O/'pose-samples-SprintReferenceV4.json').read_text(encoding='utf-8'))['clips']
new=json.loads((O/'pose-samples-SprintSmoothV5.json').read_text(encoding='utf-8'))['clips']
assert set(old)==set(new) and len(new)==6, 'Both captures must contain all six sprint variants'
report={'comparison':'UE compressed animation poses, 240 Hz sampling in separate processes','clips':{},'failures':[]}

def centre(samples,bone):
    return [sum(s[bone]['p'][j] for s in samples[:-1])/(len(samples)-1) for j in range(3)]
def excursion(samples,bone):
    mean=centre(samples,bone)
    return math.sqrt(sum(math.dist(s[bone]['p'],mean)**2 for s in samples[:-1])/(len(samples)-1))

for name,b in new.items():
    a=old[name];bone='WPN_SOCKET_Muzzle'
    before,after=a['motion'][bone],b['motion'][bone]
    peak=after['max_acceleration_cm_per_source_second2']/before['max_acceleration_cm_per_source_second2']
    rms=after['rms_acceleration_cm_per_source_second2']/before['rms_acceleration_cm_per_source_second2']
    sway=excursion(b['samples'],bone)/excursion(a['samples'],bone)
    shift=math.dist(centre(a['samples'],bone),centre(b['samples'],bone))
    checks={
        'same_duration_and_120_hz_keys':abs(a['duration']-b['duration'])<1.e-6 and b['sampled_keys']==121,
        'continuous_interpolation':b['interpolation']==a['interpolation'] and 'LINEAR' in b['interpolation'],
        'compression_below_0_1_mm':b['compression_error_cm']<.01 and b['compression_error_degrees']<.01,
        'loop_below_0_02_mm':max(m['loop_gap_cm'] for m in b['motion'].values())<.002,
        'no_frozen_muzzle_samples':after['identical_adjacent_samples']==0,
        'original_arm_lengths':max(b['arm_length_range_cm'])<.01,
        'hand_stays_on_grip':b['hand_to_gun_drift_local_cm']<.001,
        'peak_acceleration_reduced_at_least_50_percent':peak<.5,
        'rms_acceleration_reduced_at_least_40_percent':rms<.6,
        'main_sway_retained':.70<sway<1.25,
        'carry_centre_preserved_within_1_cm':shift<1.,
    }
    report['clips'][name]={'checks':checks,'peak_acceleration_reduction_percent':100*(1-peak),
        'rms_acceleration_reduction_percent':100*(1-rms),'sway_rms_ratio':sway,'carry_centre_shift_cm':shift,
        'loop_gap_cm':max(m['loop_gap_cm'] for m in b['motion'].values()),
        'compression_error_cm':b['compression_error_cm']}
    report['failures'].extend(name+': '+check for check,passed in checks.items() if not passed)
report['passed']=not report['failures']
(O/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
if report['failures']:raise SystemExit(1)
