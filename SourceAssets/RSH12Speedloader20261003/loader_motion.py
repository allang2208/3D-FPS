"""Transport native 715 loader, all five rounds and its holding hand together."""
from mathutils import Matrix,Vector,Quaternion
from contact_motion import carry_arm,mix,smooth

class LoaderContact:
    def __init__(self,ctx):
        self.ctx=ctx;self.names=ctx['names'];self.parent=ctx['parent']
        self.S=ctx['S'];self.to_native=ctx['r'].matrix_world.inverted()@self.S@Matrix.Diagonal((.01,.01,.01,1));self.to_ue=self.to_native.inverted()
        speed=ctx['D']['clips']['speed_0'];self.duration=speed['duration']
        seat=min(speed['samples'],key=lambda row:abs(row['time']/self.duration*3.6-2.42))
        world={n:ctx['matrix'](v) for n,v in seat['world'].items()}
        self.old_seat=world['WPN_Cylinder'].inverted()@world['WPN_Loader']
        self.new_seat=ctx['desired']['WPN_Cylinder'].inverted()@ctx['desired']['WPN_Loader']
        self.frozen=None

    def begin(self):self.frozen=None

    def apply(self,kind,t,old,world,local):
        if kind!='speed_0':
            # A loader is only carried by the speed action; keep it collapsed
            # during presentation, single loading, firing and all other channels.
            m=local['WPN_Loader'];local['WPN_Loader']=Matrix.LocRotScale(m.translation,m.to_quaternion(),Vector((.0001,)*3));return {'WPN_Loader'}
        u=t/self.duration*3.6;changed=set()
        if u<1.27:return changed
        old_seat=old['WPN_Cylinder']@self.old_seat
        new_seat=world['WPN_Cylinder']@self.new_seat
        transport=new_seat@old_seat.inverted()
        if u<=2.53:self.frozen=transport.copy()
        elif self.frozen is not None:transport=self.frozen
        weight=smooth((u-1.27)/.13)*(1-smooth((u-2.91)/.38))
        hand_map=mix(Matrix.Identity(4),transport,weight)
        target=hand_map@old['WPN_Loader'];world['WPN_Loader']=target;changed.add('WPN_Loader')
        if self.ctx['SIDE']=='single':
            native_old={n:self.to_native@m@self.S for n,m in old.items()}
            native_new={n:self.to_native@m@self.S for n,m in world.items()}
            target_hand=self.to_native@hand_map@old['hand_l']@self.S
            arm=carry_arm(native_new,native_old,self.names,'l',target_hand)
            for n in arm:world[n]=self.to_ue@native_new[n]@self.S
            changed.update(arm)
        if 1.44<=u:
            # The five seated transforms use their own bore frames. Before
            # release they form one rigid pack with the held loader; afterwards
            # the rounds stay seated while the original 715 hand withdraws.
            pack=target@new_seat.inverted() if u<2.42 else Matrix.Identity(4)
            for i in range(5):
                case='WPN_Case_'+str(i);tip='WPN_Round_'+str(i)
                world[case]=pack@world['WPN_Cylinder']@self.ctx['newlocal'][case]
                world[tip]=world[case]@self.ctx['newlocal'][tip]
                changed.update((case,tip))
        for n in changed:local[n]=world[self.parent[n]].inverted()@world[n]
        return changed
