"""Side-by-side table of diagnose.py summaries: python compare.py labelA labelB ..."""
import sys, json
from pathlib import Path
OUT = Path(__file__).parent
runs = [json.loads((OUT / (l + '.json')).read_text()) for l in sys.argv[1:]]
rows = [
    ('left arm min eye distance cm (idle)', lambda d: '%.1f (%.1f) @%.2fs' % (d['eye_min_cm']['l'], d['eye_idle_cm']['l'], d['eye_min_t']['l'])),
    ('right arm min eye distance cm', lambda d: '%.1f' % d['eye_min_cm']['r']),
    ('arm->gun penetration max cm (idle)', lambda d: '%.2f (%.2f) @%.2fs %s/%s' % (d['pen_depth_max_cm'], d['pen_depth_idle'], d['pen_depth_t'], d['pen_region'], d['pen_part'])),
    ('frames with penetration >0.5 / >1.0 cm', lambda d: '%d / %d of %d' % (d['frames_pen_over_05'], d['frames_pen_over_10'], d['sampled'])),
    ('elbow seam det min (idle)', lambda d: '%.3f (%.3f) @%.2fs' % (d['det_elbow_min_l'], d['det_elbow_idle_l'], d['det_elbow_min_l_t'])),
    ('elbow seam det median-min', lambda d: '%.3f' % d['det_elbow_med_min_l']),
    ('wrist seam det min (idle)', lambda d: '%.3f (%.3f)' % (d['det_wrist_min_l'], d['det_wrist_idle_l'])),
    ('right elbow / wrist det min', lambda d: '%.3f / %.3f' % (d['det_elbow_min_r'], d['det_wrist_min_r'])),
    ('elbow cap roll range deg (idle)', lambda d: '%.0f..%.0f (%.0f)' % (*d['elbow_roll_l_range'], d['elbow_roll_l_idle'])),
    ('left skin edge stretch max (idle)', lambda d: '%.2f (%.2f) @%.2fs' % (d['stretch_max_l'], d['stretch_idle_l'], d['stretch_max_l_t'])),
    ('left skin edge stretch p99.9', lambda d: '%.2f' % d['stretch_p999_l']),
    ('clavicle shift vs idle cm (l/r)', lambda d: '%.1f / %.1f' % (d['clav_shift_change_cm']['l'], d['clav_shift_change_cm']['r'])),
    ('bone length error cm', lambda d: '%.4f' % d['bone_length_err_cm']),
    ('hand jump per 1/60 s cm', lambda d: '%.1f @%.2fs' % (d['jump_hand_max_cm'], d['jump_hand_t'])),
    ('elbow jump per 1/60 s cm', lambda d: '%.1f @%.2fs' % (d['jump_elbow_max_cm'], d['jump_elbow_t'])),
    ('elbow angle range deg', lambda d: '%.0f..%.0f' % tuple(d['elbow_l_range'])),
]
w = 40
print('metric'.ljust(w) + ''.join(r['label'][:34].ljust(36) for r in runs))
for name, f in rows:
    print(name.ljust(w) + ''.join(f(r).ljust(36) for r in runs))
for g in runs[0].get('garments', {}):
    for m in ('gun_depth', 'gun_count', 'sink_max', 'sink_count', 'poke_max', 'poke_count'):
        vals = []
        for r in runs:
            G = r.get('garments', {}).get(g)
            vals.append('%.2f (idle %.2f)' % (G[m], G[m + '_idle']) if G else '-')
        print(('%s %s' % (g, m)).ljust(w) + ''.join(v.ljust(36) for v in vals))
