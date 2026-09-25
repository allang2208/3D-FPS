"""Frozen hand frame input for read_hand_authoring.py; not an action generator."""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

P=Path(__file__).parent
PROJECT=P.parents[2]
# Definition-only input; never exports the retired V8 actions.
data=json.loads((PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/M4.json').read_text())
native=json.loads((PROJECT/'SourceAssets/ModularOutfit20260925/BareArmsFamilyV6/Sources/M4.json').read_text())
anatomy=json.loads((PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json').read_text())['anatomy']
donor=json.loads((P.parent/'ArmsV2/sparrow_motion.json').read_text())
surface=json.loads((P.parent/'ArmsV2/bow_surface.json').read_text())
FPS=120
DURATIONS={'Idle':2.,'Ready':2.,'Equip':.45,'Nock':.68,'Draw':1.4,'Hold':2.,'Release':.64,'Run':.8}
R=Matrix.Rotation(math.pi/2,3,'Z')
S=Matrix.Diagonal((1,-1,1))
def unit(v): return Vector(v).normalized()
def smooth(x):
    x=max(0.,min(1.,x)); return x*x*(3-2*x)
def mat(p,r=None):
    a=(r or Matrix.Identity(3)).to_4x4();a.translation=Vector(p);return a
def limb_frame(axis,across):
    x=axis.normalized();y=across-x*across.dot(x);y.normalize()
    return Matrix((x,y,x.cross(y))).transposed()
digits={side:{d['bone']:d for d in anatomy[side]['digits']} for side in ('l','r')}
def world_to_blender(m):return mat(S@m.translation*.01,S@m.to_3x3()@S)
names_by_index={v['index']:n for n,v in native['bones'].items()}
keep={n for w in data['weights'] for n in w}
for n in list(keep):
    while native['bones'][n]['parent'] in names_by_index:
        n=names_by_index[native['bones'][n]['parent']];keep.add(n)
order=[n for n in native['bones'] if n in keep]
parent={n:names_by_index.get(native['bones'][n]['parent']) for n in order}
rest={}
for n in order:
    b=native['bones'][n];a=Matrix(b['axes']).transposed()
    for i in range(3):a.col[i]=a.col[i].normalized()
    rest[n]=mat(R@Vector(b['position']),R@a)
# A new, unit-scale root is the native basis for this weapon. No source gun root.
root='bow_root'
for n in order:
    if parent[n] not in keep:parent[n]=root
order=[root]+order;parent[root]=None;rest[root]=Matrix.Identity(4)
for n in ('bow_grip','bow_nock'):
    order.append(n);parent[n]='hand_l' if n=='bow_grip' else 'hand_r';rest[n]=Matrix.Identity(4)
local={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in order}
# Preserve the accepted M4 VRE closed hand as a complete grasp. Fit its whole
# frame to the original bow handle; no guessed per-digit Euler bends.
grasp=json.loads((P.parent/'GripV5/grasp_native.json').read_text())
grasp_pose={n:Matrix(v) for n,v in grasp['pose'].items()}
grasp_frame=Matrix(grasp['grip_in_source'])
left_in_grip=grasp_frame.inverted()@grasp_pose['hand_l']
left_fingers={n:grasp_pose[parent[n]].inverted()@grasp_pose[n] for n in order
    if n.endswith('_l') and n.split('_')[0] in ('index','middle','ring','pinky','thumb')}
# The dark bow's existing wrap is centred at Y=-0.935 cm. Its cylindrical
# grip extends approximately Z +/-9.67 cm; retain the authored geometry.
GRIP_CONTACT=Matrix.Translation((0.,-.935,.8))


# Actual donor hand separation, sampled until the draw settles at 2.333 seconds.
draw=donor['clips']['RMB_Drawback']['frames']
dist=[(Vector(f['hand_l']['p'])-Vector(f['hand_r']['p'])).length for f in draw]
curve=[max(0.,min(1.,(dist[round(i*70/16)]-dist[0])/(dist[70]-dist[0]))) for i in range(17)]
curve[0]=0.;curve[-1]=1.
def progress(t):
    x=max(0.,min(1.,t))*16;i=min(15,int(x));return curve[i]*(1-x+i)+curve[i+1]*(x-i)
def sample_reference(t):return draw[min(70,max(0,round(t*70)))]
# Camera-space framing follows the existing rifle presentation: keep the
# shoulders behind/below the eye, with only distal forearms entering the frame.
# Solve against these anchors; do not move the bow independently of its grasp.
IDLE_BOW=Vector((46.,-20.,-20.))
DRAW_BOW=Vector((68.,-15.,-8.))
RIGHT_PARK=Vector((10.,37.,-48.))
SHOULDERS={'l':Vector((-7.,-22.,-26.)), 'r':Vector((-7.,22.,-26.))}
ELBOW_POLES={'l':Vector((6.,-35.,-46.)), 'r':Vector((0.,36.,-44.))}
# Opening the shoulder girdle carries the support shoulder forward and the
# draw shoulder back. Preserve bone lengths while retaining the full draw.
DRAW_SHOULDERS={'l':Vector((12.,-22.,-29.)), 'r':Vector((-17.,20.,-26.))}
DRAW_ELBOW_POLES={'l':Vector((10.,-32.,-54.)), 'r':Vector((-16.,44.,-6.))}
DRAW_YAW_DEG=-28.
RIGHT_HAND_YAW_DEG=-20.
def bow_frame(q):
    # Lift the bow early so the right hand stays in front of the eye and clears
    # the bottom of the frame throughout the backward/rightward draw.
    lift=smooth(min(1.,q/.65))
    r=Matrix.Rotation(math.radians(DRAW_YAW_DEG*q),3,'Z')@Matrix.Rotation(math.radians(-12+7*q),3,'X')
    return mat(IDLE_BOW.lerp(DRAW_BOW,lift),r)
# The nock stays in the original bow/string plane. Screen-right travel comes
# from orienting that plane, not bending the string sideways out of the riser.
BRACE=Vector((-21.46,-.935,1.5));ANCHOR=Vector((-52.5,-.935,1.5))

def hand_basis(side,forward,dorsal):
    oldf=R@Vector(anatomy[side]['forward']);oldd=R@Vector(anatomy[side]['dorsal'])
    oldd=(oldd-oldf*oldf.dot(oldd)).normalized();olda=oldf.cross(oldd)
    f=unit(forward);d=(Vector(dorsal)-f*f.dot(Vector(dorsal))).normalized();a=f.cross(d)
    return Matrix((f,d,a)).transposed()@Matrix((oldf,oldd,olda))

# Joint increments in this V7 hand's anatomical hinge axes, not Euler values
# copied from Sparrow's different rest pose. Each row is MCP/PIP/DIP/splay.
# Keep the existing middle-finger support exactly; soften the surrounding
# silhouette and distinguish the relaxed thumb/pinky from the three hooks.
RIGHT_RELAX={
    'index':(8.,16.,8.,0.), 'middle':(11.,20.,10.,0.),
    'ring':(16.,24.,13.,-.5), 'pinky':(22.,30.,16.,-1.),
    'thumb':(2.,10.,6.,0.)}
RIGHT_CARRY={
    'index':(10.,30.,16.,-.5), 'middle':(8.,26.,12.,0.),
    'ring':(16.,30.,16.,-.2), 'pinky':(24.,34.,18.,-.8),
    'thumb':(8.,18.,14.,0.)}
RIGHT_HOOK={
    'index':(8.,54.,28.,1.5), 'middle':(4.,60.,30.,0.),
    'ring':(12.,57.,30.,-1.), 'pinky':(28.,40.,20.,-2.),
    'thumb':(2.,14.,10.,0.)}
RIGHT_RELEASE={
    'index':(3.,12.,6.,-.5), 'middle':(5.,15.,8.,0.),
    'ring':(10.,20.,10.,.3), 'pinky':(22.,30.,16.,0.),
    'thumb':(2.,10.,6.,0.)}
NOCK_CLOSE={'index':(.55,.79),'middle':(.54,.80),'ring':(.57,.81),
            'pinky':(.52,.78),'thumb':(.50,.75)}
def blend_finger(a,b,u):return tuple(x+(y-x)*u for x,y in zip(a,b))
def right_finger_pose(role,t):
    phase=t/DURATIONS[role]
    if role=='Nock':
        result={}
        for digit in RIGHT_RELAX:
            carry=blend_finger(RIGHT_RELAX[digit],RIGHT_CARRY[digit],smooth((phase-.20)/.14))
            a,b=NOCK_CLOSE[digit]
            result[digit]=blend_finger(carry,RIGHT_HOOK[digit],smooth((phase-a)/(b-a)))
        return result
    if role in ('Draw','Hold'):return RIGHT_HOOK
    if role=='Release':
        result={}
        for digit in RIGHT_RELAX:
            # The three loaded fingers let go together; stagger only the
            # non-load-bearing thumb/pinky. Recover a soft curve, not a flat fan.
            seconds=.050 if digit in ('index','middle','ring') else .070 if digit=='pinky' else .090
            opened=blend_finger(RIGHT_HOOK[digit],RIGHT_RELEASE[digit],smooth(t/seconds))
            result[digit]=blend_finger(opened,RIGHT_RELAX[digit],smooth((t-.10)/.18))
        return result
    return RIGHT_RELAX

def pose(role,t):
    phase=t/DURATIONS[role]
    q=progress(phase) if role=='Draw' else 1. if role=='Hold' else 0.
    support=q
    bow=bow_frame(q)
    nock=bow@BRACE.lerp(ANCHOR,q)
    right=nock.copy();release=0.
    right_digits=right_finger_pose(role,t)
    if role in ('Idle','Ready','Equip','Run'):
        # Both unloaded idle and an arrow left on the rest are held one-handed.
        # The right arm is physically parked outside the lower-right frustum.
        right=RIGHT_PARK.copy()
    if role=='Nock':
        keys=[(0.,RIGHT_PARK),(.34,Vector((8,33,-46))),
              (.58,Vector((22,13,-30))),(.82,bow@BRACE+Vector((1,3,-3))),(1.,bow@BRACE)]
        for (a,p),(b,v) in zip(keys,keys[1:]):
            if a<=phase<=b:right=p.lerp(v,smooth((phase-a)/(b-a)));break
    if role=='Release':
        release=smooth(t/.075)
        settle=smooth((t-.16)/(.64-.16))
        support=1-settle
        bow=bow_frame(support)
        right=(bow_frame(1.)@ANCHOR+Vector((-2.5*release,4*release,release))).lerp(
            RIGHT_PARK,settle)
        nock=bow@ANCHOR.lerp(BRACE,release)
    if role=='Equip':
        lift=1-smooth(phase)
        offset=Vector((-10,6,-30))*lift
        bow.translation+=offset;nock+=offset
    if role=='Run':
        off=Vector((-8,6,-16));off+=Vector((math.sin(t*2*math.pi/.8)*.9,0,math.cos(t*4*math.pi/.8)*.8))
        bow.translation+=off;nock+=off
        right+=Vector((0,0,math.cos(t*4*math.pi/.8)*.8))
    if role in ('Idle','Ready'):
        # Low amplitude reference idle breathing, with identical contact transport.
        frames=donor['clips']['idle']['frames'];f=frames[round(t*30)%len(frames)];f0=frames[0]
        change=Vector(f['hand_l']['p'])-Vector(f0['hand_l']['p'])
        off=Vector((change.y,-change.x,change.z))*.20*math.sin(math.pi*phase)**2
        bow.translation+=off;right+=off;nock+=off
    left_target=bow@GRIP_CONTACT@left_in_grip
    left_delta=left_target.to_3x3()@rest['hand_l'].to_3x3().transposed()
    # Turn the complete hook and its wrist-to-string offset together. Keeping
    # a fixed camera-forward palm while the draw elbow opens twists the wrist.
    right_frame=Matrix.Rotation(math.radians(RIGHT_HAND_YAW_DEG*support),3,'Z')
    right_delta=hand_basis('r',right_frame@Vector((1,0,.06)),right_frame@Vector((0,1,0)))
    # Palm/phalange contact offsets, not the wrist origin, touch riser and string.
    targets={'l':left_target.translation,
             'r':right-right_frame@Vector((7.,-1.0,.4))}
    hands={'l':left_delta,'r':right_delta}
    world={}
    ref=sample_reference(support)
    shoulder_open=smooth(min(1.,support/.65))
    for n in order:
        world[n]=(world[parent[n]]@local[n]) if parent[n] else local[n].copy()
    for side in ('l','r'):
        clav='clavicle_'+side;up='upperarm_'+side;low='lowerarm_'+side;hand='hand_'+side
        shoulder_target=SHOULDERS[side].lerp(DRAW_SHOULDERS[side],shoulder_open)
        world[clav].translation+=shoulder_target-(world[clav]@local[up]).translation
        shoulder=(world[clav]@local[up]).translation
        wrist=targets[side]
        l1=(rest[low].translation-rest[up].translation).length
        l2=(rest[hand].translation-rest[low].translation).length
        axis=(wrist-shoulder).normalized();distance=min((wrist-shoulder).length,l1+l2-.12)
        # Sparrow's elbow travel supplies the changing pole; hand contacts and
        # V7 bone lengths remain authoritative for the first-person adaptation.
        elbow=Vector(ref['lowerarm_'+side]['p'])-Vector(ref['head']['p'])
        ref0=sample_reference(0.)
        elbow0=Vector(ref0['lowerarm_'+side]['p'])-Vector(ref0['head']['p'])
        travel=elbow-elbow0
        pole=ELBOW_POLES[side].lerp(DRAW_ELBOW_POLES[side],smooth(support))+Vector((travel.y,-travel.x,travel.z))*.15
        bend=(pole-shoulder)-axis*(pole-shoulder).dot(axis)
        bend.normalize()
        a=(l1*l1-l2*l2+distance*distance)/(2*distance)
        h=math.sqrt(max(0.,l1*l1-a*a));elbow=shoulder+axis*a+bend*h
        wrist=shoulder+axis*distance
        ru=rest[low].translation-rest[up].translation
        rl=rest[hand].translation-rest[low].translation
        ud=(elbow-shoulder).normalized();ld=(wrist-elbow).normalized()
        ref_across=R@Vector(anatomy[side]['across'])
        # Palm hinge determines roll independently of wrist extension.
        dl=limb_frame(ld,hands[side]@ref_across)@limb_frame(rl,ref_across).transposed()
        du=limb_frame(ud,ud.cross(ld))@limb_frame(ru,ru.cross(rl)).transposed()
        world[up]=mat(shoulder,du@rest[up].to_3x3())
        world[low]=mat(elbow,dl@rest[low].to_3x3())
        world[hand]=mat(wrist,hands[side]@rest[hand].to_3x3())
        descendants=set((up,low,hand))
        for n in order:
            if parent[n] in descendants and n not in (low,hand):
                descendants.add(n);world[n]=world[parent[n]]@local[n]
                # Twist/support bones keep their complete rest-local pose.
                # Their weighted skin follows the same solved rigid segment.
                digit=n.split('_')[0]
                if side=='l' and n in left_fingers:
                    world[n]=world[parent[n]]@left_fingers[n]
                elif side=='r' and n in digits['r']:
                    seg=int(n.split('_')[1])-1
                    curl=right_digits[digit][seg]
                    parent_delta=world[parent[n]].to_3x3()@rest[parent[n]].to_3x3().transposed()
                    direction=parent_delta@(R@Vector(digits[side][n]['across']))
                    # Across x forward = -dorsal, the palm-side curl direction.
                    turn=Matrix.Rotation(math.radians(curl),3,direction)
                    if seg==0:
                        normal=parent_delta@(R@Vector(digits[side][n]['dorsal']))
                        turn=Matrix.Rotation(math.radians(right_digits[digit][3]),3,normal)@turn
                    world[n]=mat(world[n].translation,turn@world[n].to_3x3())
    world['bow_grip']=bow
    world['bow_nock']=mat(right if role=='Nock' else nock)
    return world
