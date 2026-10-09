"""Source-clock diagnostic for the compiled Super90 presentation profile.

This is an offline preview, not a game capture. Angles/position reproduce the
Super90Loader branch and the configured camera gains for timing inspection.
"""
import math,json
from pathlib import Path
O=Path(__file__).parent
def smooth(a,b,t):
    x=max(0.,min(1.,(t-a)/(b-a)));return x*x*(3-2*x)
def impact(t,at,duration):
    age=(t-at)/duration
    if age<=0 or age>=1:return 0.
    times=(0.,.23,.37,.72,1.);values=(0.,1.,.82,-.24,0.)
    for i in range(1,5):
        if age<=times[i]:return values[i-1]+(values[i]-values[i-1])*smooth(times[i-1],times[i],age)
def sample(f,count,empty=False,cycle=False):
    t=f/60;last=(90+max(0,count-1)*4)/60
    end=1.1 if cycle else last+(68 if empty else 32)/60
    bolt=1.1*28/52 if cycle else last+44/60;dock=87/60
    follow=[0.]*3;pos=[0.]*3;angles=[0.]*3;delta=[0.]*3
    if not cycle:
        back=last+(49 if empty else 2)/60
        lift=smooth(5/60,30/60,t)*(1-smooth(back,end,t))
        pressure=smooth(dock,114/60,t)*(1-smooth(last,last+7/60,t))
        follow=[a*lift+b*pressure for a,b in zip((-.025,-.015,.085),(.025,0,-.02))]
        pos=[a*lift for a in (-.018,-.012,-.008)]
        for at,dur,a,p in [(dock,.14,(-.025,.006,-.035),(-.009,.003,.006)),(last,.16,(.045,-.008,.025),(-.012,0,.009))]:
            wave=impact(t,at,dur);angles=[x+y*wave for x,y in zip(angles,a)];delta=[x+y*wave for x,y in zip(delta,p)]
    if empty:
        wave=impact(t,bolt,min(.18,end-bolt));angles=[x+y*wave for x,y in zip(angles,(-.07,.008,.035))];delta=[x+y*wave for x,y in zip(delta,(.014,.003,-.008))]
    # Strength=2.8, FollowStrength=2, runtime ImpactStrength clamp=2,
    # AFPSGAMECharacter.CameraMotionScale=.45, no ADS during reload.
    return ([2.8*.45*(2*a+2*b) for a,b in zip(follow,angles)], [2.8*.45*(2*a+2*b) for a,b in zip(pos,delta)])
if __name__=='__main__':
    all_rows=[]
    for empty in (False,True):
      for count in range(1,8):
        end=90+4*(count-1)+(68 if empty else 32);rows=[]
        for k in range(end*4+1):
            f=k/4;a,p=sample(f,count,empty);rows.append({'frame':f,'runtime_s':f/60/.85,'degrees':a,'cm':p})
        all_rows.append({'count':count,'empty':empty,'rows':rows,'end_zero':rows[-1]['degrees']==[0.]*3 and rows[-1]['cm']==[0.]*3})
    result={'mode':'offline_source_clock_model','play_rate':.85,'clips':all_rows,
        'max_angle_deg':max(abs(v) for c in all_rows for r in c['rows'] for v in r['degrees']),
        'max_travel_cm':max(abs(v) for c in all_rows for r in c['rows'] for v in r['cm'])}
    (O/'Diagnostics/camera_motion.json').write_text(json.dumps(result,separators=(',',':')))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(10,5),sharex=True,layout='constrained')
    for ax,empty in zip(axes,(False,True)):
        rows=next(c['rows'] for c in all_rows if c['count']==7 and c['empty']==empty)
        for j,name in enumerate(('Pitch','Yaw','Roll')):ax.plot([r['runtime_s'] for r in rows],[r['degrees'][j] for r in rows],label=name)
        for f,name in [(87,'Dock'),(114,'Push stop')]+([(158,'Bolt release')] if empty else []):
            x=f/60/.85;ax.axvline(x,color='grey',ls=':',lw=.8);ax.text(x+.025,.18,name,rotation=90,va='top',fontsize=8)
        ax.set_ylabel('Camera offset (deg)');ax.set_title('Empty 7-shell reload' if empty else 'Normal 7-shell reload');ax.grid(alpha=.2);ax.legend(loc='upper left',ncol=3)
    axes[-1].set_xlabel('Runtime seconds at 0.85x');fig.savefig(O/'Diagnostics/camera_timing.png',dpi=120)
    print('CAMERA_OFFLINE',result['max_angle_deg'],result['max_travel_cm'],all(c['end_zero'] for c in all_rows))
