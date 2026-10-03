"""Object-relative cartridge grip, five-hole insertion and native arm transport."""
from mathutils import Matrix,Vector,Quaternion
import math

def smooth(x):
    x=max(0.,min(1.,x));return x*x*(3.-2.*x)

def mix(a,b,w):
    ap,aq,asc=a.decompose();bp,bq,bsc=b.decompose()
    return Matrix.LocRotScale(ap.lerp(bp,w),aq.slerp(bq,w),asc.lerp(bsc,w))

def skin_anchor(p,rows):
    points=[]
    for row in rows:
        points.append(sum(((p[n]@Vector(q))*w for n,w,q in row),Vector())/sum(w for n,w,q in row))
    return sum(points,Vector())/len(points)

def carry_arm(p,old,names,side,target):
    # Preserve the source finger shape, bone lengths and elbow bend plane.
    hand='hand_'+side;delta=target@old[hand].inverted();changed=set()
    for n in names:
        if n==hand or n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):
            p[n]=delta@old[n];changed.add(n)
    a,b='upperarm_'+side,'lowerarm_'+side
    shoulder=old[a].translation.copy();elbow=old[b].translation;wrist=old[hand].translation
    goal=target.translation;l1=(elbow-shoulder).length;l2=(wrist-elbow).length
    line=goal-shoulder;distance=line.length;axis=line.normalized()
    reach=(l1+l2)*.985
    if distance>reach:
        shift=axis*(distance-reach);shoulder+=shift;distance=reach
        clav='clavicle_'+side;p[clav]=old[clav].copy();p[clav].translation+=shift;changed.add(clav)
    distance=max(abs(l1-l2)+1e-5,distance)
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    pole=elbow-old[a].translation-axis*(elbow-old[a].translation).dot(axis)
    if pole.length<1e-7:pole=Vector((0,0,-1))
    knee=shoulder+axis*along+pole.normalized()*math.sqrt(max(0,l1*l1-along*along))
    qa=(elbow-old[a].translation).rotation_difference(knee-shoulder)
    qb=(wrist-elbow).rotation_difference(goal-knee)
    p[a]=Matrix.LocRotScale(shoulder,qa@old[a].to_quaternion(),old[a].to_scale())
    p[b]=Matrix.LocRotScale(knee,qb@old[b].to_quaternion(),old[b].to_scale());changed.update((a,b))
    for n in names:
        if n.endswith('_'+side) and n.startswith(('upperarm_twist','lowerarm_twist')):
            owner=a if n.startswith('upperarm') else b
            p[n]=p[owner]@old[owner].inverted()@old[n];changed.add(n)
    ik='ik_hand_'+side
    if ik in p:p[ik]=target.copy();changed.add(ik)
    return changed

class ReloadContact:
    def __init__(self,rig,names,parents,rest,newrest,alignment,fit,recipe,oldlocal,newlocal):
        self.rig=rig;self.names=names;self.parents=parents;self.recipe=recipe
        self.S=Matrix.Diagonal((1,-1,1,1));self.cm=Matrix.Diagonal((.01,.01,.01,1))
        self.to_native=rig.matrix_world.inverted()@self.S@self.cm
        self.to_ue=self.to_native.inverted()
        self.case_grip=[];self.forward=[]
        self.oldlocal=oldlocal;self.newlocal=newlocal
        # Pinch the brass body near its rear, matching the native source grip.
        # Each bore retains its own bind frame; no shared-case pivot shortcut.
        for i,chamber in enumerate(fit['chambers']):
            x,z,_=chamber['center_xz_radius'];bone='WPN_Case_'+str(i)
            bind=newrest[bone].inverted()@rest['WPN_root']@alignment
            self.case_grip.append(bind@Vector((x,fit['rear_plane_m']-.008,z)))
            self.forward.append((bind.to_3x3()@Vector((0,-1,0))).normalized())
        self.radius=min(c['center_xz_radius'][2] for c in fit['chambers'])-.00012
        self.release={}

    def begin(self):self.release={}

    def native(self,world):return {n:self.to_native@m@self.S for n,m in world.items()}

    def apply(self,kind,t,old_world,new_world,local):
        if not kind.startswith('single_'):return set()
        start,count=map(int,kind.split('_')[1:]);begin=1.5 if start==0 else .6
        old=self.native(old_world);p=self.native(new_world);side=self.recipe['support'];hand='hand_'+side
        changed=set()
        for i in range(start,min(5,start+count)):
            phase=t-begin-1.1*(i-start)
            if not (.02<=phase<.84):continue
            bone='WPN_Case_'+str(i);round_bone='WPN_Round_'+str(i)
            if phase<=.64:
                thumb=skin_anchor(old,self.recipe['anchors']['thumb'])
                index=skin_anchor(old,self.recipe['anchors']['index'])
                donor_forward=Vector(self.recipe['donor_forward'])
                donor_axis=old[bone].to_quaternion()@donor_forward
                q=old[bone].to_quaternion()@self.forward[i].rotation_difference(donor_forward)
                mid=(thumb+index)*.5;spread=index-thumb
                radial=spread-donor_axis*spread.dot(donor_axis)
                axis_center=old[bone].translation
                if radial.length>1e-7:
                    chord=min(radial.length,2*self.radius)
                    perpendicular=donor_axis.cross(radial).normalized()
                    offset=math.sqrt(max(0,self.radius*self.radius-chord*chord*.25))
                    choices=(mid+perpendicular*offset,mid-perpendicular*offset)
                    # Choose the circle through both pads nearest the native
                    # case axis. Midpoint alone places brass inside both pads.
                    axis_center=min(choices,key=lambda c:((c-old[bone].translation)-donor_axis*(c-old[bone].translation).dot(donor_axis)).length_squared)
                scale=old[bone].to_scale()
                held=Matrix.LocRotScale(axis_center-q@self.case_grip[i],q,scale)
                # Insertion becomes coaxial with this actual hole. Preserve
                # the donor's axial push while correcting the different bore.
                old_seat=self.to_native@(old_world['WPN_Cylinder']@self.oldlocal[bone])@self.S
                gap=max(0.,(old[bone].translation-old_seat.translation).dot(-donor_axis))
                seated=self.to_native@(new_world['WPN_Cylinder']@self.newlocal[bone])@self.S
                seated.translation-=seated.to_quaternion()@self.forward[i]*gap*1.3
                w=smooth((phase-.22)/.25)
                inserted=mix(held,seated,w)
                transport=inserted@held.inverted()
                # Align the hand and cartridge together, instead of sliding
                # the cartridge away from the fingers toward the chamber.
                hand_target=mix(old[hand],transport@old[hand],smooth((phase-.05)/.05))
                changed.update(carry_arm(p,old,self.names,side,hand_target))
                relative_round=p[bone].inverted()@p[round_bone]
                p[bone]=mix(p[bone],inserted,smooth((phase-.02)/.06))
                p[round_bone]=p[bone]@relative_round
                changed.update((bone,round_bone));self.release[i]=transport
            elif i in self.release:
                w=1-smooth((phase-.64)/.20)
                target=mix(old[hand],self.release[i]@old[hand],w)
                changed.update(carry_arm(p,old,self.names,side,target))
        for n in changed:
            new_world[n]=self.to_ue@p[n]@self.S
        # Use the rebuilt parent transforms, not those sampled before contact.
        for n in changed:
            parent=self.parents[n]
            local[n]=new_world[parent].inverted()@new_world[n]
        return changed
