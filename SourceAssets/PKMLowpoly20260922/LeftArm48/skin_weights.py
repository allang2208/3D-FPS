"""PKM-local, continuous binding along the real left forearm bone stations."""
import bisect
import math

FOREARM=('lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l')

def binding_parameters(bones):
    elbow=bones['lowerarm_l']['position']
    wrist=bones['hand_l']['position']
    delta=[wrist[i]-elbow[i] for i in range(3)]
    length2=sum(x*x for x in delta)
    stations=[sum((bones[n]['position'][i]-elbow[i])*delta[i] for i in range(3))/length2 for n in FOREARM]
    return elbow,delta,length2,stations

def rebind(position,original,parameters):
    total=sum(original.get(n,0.) for n in FOREARM)
    if total <= 1.e-10 or not any(original.get(n,0.)>0 for n in FOREARM[:-1]):
        return dict(original)
    elbow,delta,length2,stations=parameters
    t=sum((position[i]-elbow[i])*delta[i] for i in range(3))/length2
    j=max(0,min(len(stations)-2,bisect.bisect_right(stations,t)-1))
    alpha=max(0.,min(1.,(t-stations[j])/(stations[j+1]-stations[j])))
    result={n:w for n,w in original.items() if n not in FOREARM}
    for n,w in ((FOREARM[j],total*(1-alpha)),(FOREARM[j+1],total*alpha)):
        if w>1.e-10: result[n]=w
    return result
