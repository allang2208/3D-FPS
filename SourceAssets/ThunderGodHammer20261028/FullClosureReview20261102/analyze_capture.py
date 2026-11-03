"""Summarize measured frames and recorded mixer audio; does not certify aesthetics."""
from pathlib import Path
import argparse,csv,json,math
import numpy as np
from PIL import Image
import soundfile as sf
from scipy.signal import correlate,find_peaks,resample_poly

p=argparse.ArgumentParser();p.add_argument('capture');a=p.parse_args();D=Path(a.capture);R=Path(__file__).parent
result={'scope':'measured frame samples and waveform matching, not subjective animation or sound acceptance'}
frames=D/'frames.csv'
if frames.exists():
    rows=list(csv.DictReader(frames.open(encoding='utf-8-sig')));groups={}
    for row in rows:
        phase=int(row['phase']);age=float(row['age'])
        # Fixed idle samples after loading; screenshots occur after the window.
        if phase==-1 and 5<=age<9.5 or phase in (0,1,2,3,4,5,11) and 15<=age<19.5:
            groups.setdefault(phase,[]).append(row)
    result['idle_performance']={}
    for phase,values in groups.items():
        d={'frames':len(values)}
        for metric in ('delta_ms','game_ms','render_ms','gpu_ms'):
            x=np.array([float(v[metric]) for v in values]);x=x[x>0]
            d[metric]={'p50':float(np.quantile(x,.5)),'p95':float(np.quantile(x,.95)),'max':float(x.max())} if len(x) else None
        result['idle_performance'][str(phase)]=d
result['images']=[{'file':x.name,'size':Image.open(x).size} for x in sorted(D.glob('*.png'))]
wavs=list(D.glob('*.wav'))
if wavs:
    signal,rate=sf.read(wavs[0],always_2d=True);mono=signal.mean(axis=1)
    result['audio']={'file':wavs[0].name,'sample_rate':rate,'channels':signal.shape[1],'seconds':len(signal)/rate,
        'peak':float(np.max(np.abs(signal))),'clipped_samples':int(np.sum(np.abs(signal)>=.9999))}
    target=12000;audio=resample_poly(mono,target,rate);matches=[]
    for clip in sorted((R.parent/'JiLeiRecordedCurrentV2/Waves').glob('*.wav')):
        data,sr=sf.read(clip,always_2d=True);template=resample_poly(data.mean(axis=1),target,sr)
        # Native pitch and random cuts can be confirmed without guessing from a spectrum.
        n=len(template)
        if n>len(audio):continue
        dots=correlate(audio,template,mode='valid',method='fft')
        energy=np.sqrt(np.maximum(1e-15,correlate(audio*audio,np.ones(n),mode='valid',method='fft')*np.sum(template*template)))
        scores=dots/energy
        peaks,_=find_peaks(scores,height=.65,distance=target//2)
        for i in peaks:matches.append({'clip':clip.name,'start_seconds':float(i/target),'correlation':float(scores[i]),'clip_seconds':n/target})
    # Cuts share material from the same recording; a weaker overlapping match
    # is not a second simultaneous playback. Keep the strongest distinct spans.
    distinct=[]
    for candidate in sorted(matches,key=lambda x:x['correlation'],reverse=True):
        start=candidate['start_seconds'];end=start+candidate['clip_seconds']
        if any(min(end,m['start_seconds']+m['clip_seconds'])-max(start,m['start_seconds'])>.05 for m in distinct):continue
        distinct.append(candidate)
    result['audio']['matched_source_cuts']=sorted(distinct,key=lambda x:x['start_seconds'])
    result['audio']['overlapping_match_candidates_removed']=len(matches)-len(distinct)
    result['audio']['note']='Waveform matches demonstrate recorded cuts in the mixer output; human listening is still required for preference.'
(D/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
