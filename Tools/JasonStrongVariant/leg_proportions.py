"""Leg-only height increase, preserving foot size and upper-body dimensions."""
from muscle_shape import smooth

class LegProportions:
    def __init__(self,bones):
        positions={b['name']:b['position'] for b in bones}
        self.knee=sum(positions['calf_'+s][2] for s in ('l','r'))*.5
        self.hip=sum(positions['thigh_'+s][2] for s in ('l','r'))*.5
        self.foot_keep=max(positions['foot_'+s][2] for s in ('l','r'))+5.
        self.calf_gain=2.1
        self.thigh_gain=2.4
        self.total_gain=self.calf_gain+self.thigh_gain

    def offset(self,z):
        if z<=self.foot_keep:return 0.
        if z<self.knee:return self.calf_gain*smooth(self.foot_keep,self.knee,z)
        if z<self.hip:return self.calf_gain+self.thigh_gain*smooth(self.knee,self.hip,z)
        return self.total_gain

    def point(self,p):
        return [p[0],p[1],p[2]+self.offset(p[2])]

    def deform(self,p,muscular):
        return [muscular[0],muscular[1],muscular[2]+self.offset(p[2])]
