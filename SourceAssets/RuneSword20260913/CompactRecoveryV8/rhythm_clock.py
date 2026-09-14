"""One monotone time map for the accepted V6 skeleton and its camera feedback."""
WINDUP_END=.65
CONTACT_START=.85
CONTACT_END=.965
FOLLOW_END=1.115
UNLOAD_END=1.14
RETURN_CORNER=1.44
ATTACK_END=1.775
WINDUP_KEYS=((0.,0.),(.08,.020),(.22,.105),(.38,.235),(.54,.355),(.65,.40))

def slopes(keys):
    h=[b[0]-a[0] for a,b in zip(keys,keys[1:])]
    d=[(b[1]-a[1])/span for a,b,span in zip(keys,keys[1:],h)]
    m=[0.]*len(keys)
    for i in range(1,len(keys)-1):
        w1=2*h[i]+h[i-1];w2=h[i]+2*h[i-1]
        m[i]=(w1+w2)/(w1/d[i-1]+w2/d[i])
    return m

WINDUP_SLOPES=slopes(WINDUP_KEYS)

def hermite(u,start_slope,end_slope):
    u=max(0.,min(1.,u))
    return (u*u*u-2*u*u+u)*start_slope+(-2*u*u*u+3*u*u)+(u*u*u-u*u)*end_slope

def source_time(t):
    if t<=0:return 0.
    if t<WINDUP_END:
        i=next(j for j in range(len(WINDUP_KEYS)-1) if t<=WINDUP_KEYS[j+1][0])
        (a,x),(b,y)=WINDUP_KEYS[i:i+2];span=b-a;distance=y-x;u=(t-a)/span
        return x+distance*hermite(u,WINDUP_SLOPES[i]*span/distance,WINDUP_SLOPES[i+1]*span/distance)
    if t<=CONTACT_START:return .40+.50*(t-WINDUP_END)/(CONTACT_START-WINDUP_END)
    if t<=CONTACT_END:return .90+(t-CONTACT_START)
    if t<=FOLLOW_END:return 1.015+.10*hermite((t-CONTACT_END)/(FOLLOW_END-CONTACT_END),1.5,0.)
    if t<=UNLOAD_END:return 1.115
    if t<=RETURN_CORNER:return 1.115+.225*hermite((t-UNLOAD_END)/(RETURN_CORNER-UNLOAD_END),.55,1.1)
    if t<ATTACK_END:return 1.34+.31*hermite((t-RETURN_CORNER)/(ATTACK_END-RETURN_CORNER),1.35,0.)
    return 1.65

def timing_description():
    return {'revision':'CompactRecoveryV8','windup_end':WINDUP_END,'load_hold':.2,'contact_start':CONTACT_START,'contact_end':CONTACT_END,'follow_end':FOLLOW_END,'unload_end':UNLOAD_END,'return_corner':RETURN_CORNER,'attack_end':ATTACK_END,'windup_time_pairs':WINDUP_KEYS,'windup_slopes':WINDUP_SLOPES,'source_revision':'DiagonalHeavyV6','method':'Preserve V7 windup time map and V6 complete pose path; shorter hold and more connected recovery. No IK or pose refit.'}
