"""Small source-clock load/impact responses shared by weapon and camera authoring.

Frames remain R16/R20 frames. Values are camera-space degrees/centimetres;
they never affect ammunition, input timing, playback rate or audio events.
"""
import math
def smooth(x):
    x=max(0.,min(1.,x));return x*x*x*(x*(x*6-15)+10)
def phase(f,a,b):return smooth((f-a)/(b-a))
def response(f,start,span):
    u=(f-start)/span
    if not 0<u<1:return 0.
    keys=((0,0),(.12,1),(.28,.62),(.54,-.26),(.77,.065),(1,0))
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if u<=b:return x+(y-x)*smooth((u-a)/(b-a))
    return 0.

def motion(branch,f):
    end={'normal':144,'empty':180,'cycle':66}[branch]
    angles=[0.,0.,0.];position=[0.,0.,0.];elbow=0.
    def add(w,a,p,e=0):
        nonlocal elbow
        for i in range(3):angles[i]+=w*a[i];position[i]+=w*p[i]
        elbow+=w*e
    if branch!='cycle':
        # Irregular, quiet effort while holding the weight; no looping shake.
        add(response(f,8,24),(-.13,.07,.19),(-.015,.018,-.025),.2)
        add(response(f,57,17),(.14,-.08,-.16),(.02,-.025,.015),-.25)
        add(response(f,87.012105,11),(-.34,.11,.38),(-.045,.014,-.03),.8)
        effort=phase(f,87,107)*(1-phase(f,110,116))
        add(effort,(-.18,.07,.24),(-.025,.009,-.008),.35)
        # Small, non-uniform resistance along the accepted full pusher travel.
        for at,gain in ((93.397242,.72),(99.468221,1),(106,.83)):
            add(response(f,at,4.6)*gain,(-.07,.025,.08),(-.012,0,-.004),.12)
        add(response(f,110,13),(.66,-.17,-.54),(.085,-.025,.035),-1.1)
        add(response(f,123.464567,10),(-.15,-.06,.22),(-.015,.025,-.015),.25)
    if branch!='normal':
        pull,release=(32.218914,38.382387) if branch=='cycle' else (153.384599,158.240668)
        add(response(f,pull,8),(-.33,.1,-.21),(-.055,.01,-.015),.55)
        add(response(f,release,12),(.48,-.09,.27),(.065,-.02,.025),-.65)
    add(response(f,end-10,8),(-.1,.035,.12),(-.012,.009,-.006),.12)
    edge=phase(f,0,4)*(1-phase(f,end-4,end))
    return ([x*edge for x in angles],[x*edge for x in position],elbow*edge)

def camera_response(branch,f):
    # The head follows the hand's load later and less strongly. This is an
    # authored response, not a second audio callback or a random tick impulse.
    a,_,_=motion(branch,f-1.4)
    b,_,_=motion(branch,f-3.0)
    end={'normal':144,'empty':180,'cycle':66}[branch]
    fade=1-phase(f,end-5,end)
    return [(.72*a[i]+.28*b[i])*gain*fade for i,gain in enumerate((.26,.20,.14))]
