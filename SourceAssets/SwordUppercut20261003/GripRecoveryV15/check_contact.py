"""Only the requested hand/recovery issue, in authored and UE-read poses."""
from pathlib import Path
P=Path(__file__).resolve().parent
exec(compile((P/'author_common.py').read_text('utf-8'),str(P/'author_common.py'),'exec'))
def pose(rows):return {n:canonical(m) for n,m in globalize({n:native(k) for n,k in rows.items()}).items()}
def rigid(m):return mat(m.translation,m.to_quaternion())
report={}
for variant in ('Standard','LongGrip'):
    results={}
    for revision,path in [('V14',P/'SourceV14'/variant/'editable_keys.json'),('V15',P/variant/'editable_keys.json')]:
        d=json.loads(path.read_text('utf-8'));idle=pose(d['samples'][0]['bones'])
        grip={s:rigid(idle['WPN_root']).inverted()@rigid(idle['hand_'+s]) for s in ('l','r')}
        rows=[];last=None
        for sample in d['samples']:
            w=pose(sample['bones']);inv=rigid(w['WPN_root']).inverted();row={'t':sample['seconds'],'hands':{}}
            for s in ('l','r'):
                h,l,a=[w[n+'_'+s] for n in ('hand','lowerarm','upperarm')]
                p=(inv@h).translation;p0=grip[s].translation
                delta=h.to_quaternion()@idle['hand_'+s].to_quaternion().inverted()
                wrist=delta@(idle['hand_'+s].translation-idle['lowerarm_'+s].translation).normalized()
                lower=(h.translation-l.translation).normalized()
                row['hands'][s]={'radial_drift_cm':abs(math.hypot(p.x,p.y)-math.hypot(p0.x,p0.y))*100,
                    'station_drift_cm':abs(p.z-p0.z)*100,'wrist_bend_deg':math.degrees(lower.angle(wrist)),
                    'upper_length_cm':(l.translation-a.translation).length*100,'lower_length_cm':(h.translation-l.translation).length*100,
                    'frame_move_cm':(h.translation-last['hand_'+s].translation).length*100 if last else 0.}
            rows.append(row);last=w
        results[revision]={'peaks':{},'selected':[min(rows,key=lambda r:abs(r['t']-t)) for t in (0.,.5,1.,1.125,1.267,1.6,1.8,1.833,2.05)]}
        for s in ('l','r'):
            results[revision]['peaks'][s]={}
            for k in ('radial_drift_cm','station_drift_cm','wrist_bend_deg','upper_length_cm','lower_length_cm'):
                r=max(rows,key=lambda x:x['hands'][s][k]);results[revision]['peaks'][s][k]={'t':r['t'],'value':r['hands'][s][k]}
            r=max((r for r in rows if r['t']>=152/120),key=lambda x:x['hands'][s]['frame_move_cm'])
            results[revision]['peaks'][s]['recover_frame_move_cm']={'t':r['t'],'value':r['hands'][s]['frame_move_cm']}
    report[variant]=results
before=json.loads((P/'current_pose_before.json').read_text('utf-8'))
for v,d in before.items():
    author=json.loads((P/'SourceV14'/v/'editable_keys.json').read_text('utf-8'))
    errs=[]
    for source,comp in zip(d['samples']['SOURCE'],d['samples']['COMPRESSED']):
        w=pose(sample_keys(author['samples'],source['t']))
        for n,r in source['world'].items():
            errs.append({'t':source['t'],'bone':n,'author_source_cm':(w[n].translation-canonical(native(r)).translation).length*100,
                'source_compressed_cm':(Vector(r['p'])-Vector(comp['world'][n]['p'])).length})
    report[v]['imported_v14']={k:max(errs,key=lambda e:e[k]) for k in ('author_source_cm','source_compressed_cm')}
(P/'contact_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({v:{k:d[k]['peaks'] for k in ('V14','V15')} for v,d in report.items()}))
print('IMPORTED '+json.dumps({v:d['imported_v14'] for v,d in report.items()}))
