"""R3: directional upper-arm muscle volume with a gentler deltoid silhouette."""
import math
from muscle_shape import MuscleShape, smooth, bell

class ArmRefinedShape(MuscleShape):
    def limb(self,p,group):
        part,side=group.rsplit('_',1)
        if part not in ('upperarm','lowerarm'):
            return super().limb(p,group)
        a=self.bones[group]
        b=self.bones[('lowerarm' if part=='upperarm' else 'hand')+'_'+side]
        axis=[b[i]-a[i] for i in range(3)]
        length=math.sqrt(sum(v*v for v in axis))
        direction=[v/length for v in axis]
        t=sum((p[i]-a[i])*axis[i] for i in range(3))/(length*length)
        radial=[p[i]-a[i]-axis[i]*t for i in range(3)]
        # Forward-facing biceps and rear triceps are not a circular balloon.
        forward=[(1. if i==1 else 0.)-direction[i]*direction[1] for i in range(3)]
        fl=math.sqrt(sum(v*v for v in forward));forward=[v/fl for v in forward]
        rfront=sum(radial[i]*forward[i] for i in range(3))
        side_radial=[radial[i]-rfront*forward[i] for i in range(3)]
        if part=='upperarm':
            envelope=smooth(-.42,.10,t)*(1-smooth(.62,1.02,t))
            lateral_gain=.14*bell(t,.24,.44)*envelope
            anterior_gain=(.26*bell(t,.47,.40)+.09*bell(t,.12,.35))*envelope
            posterior_gain=(.22*bell(t,.40,.42)+.06*bell(t,.12,.35))*envelope
        else:
            envelope=smooth(-.15,.16,t)*(1-smooth(.52,.96,t))
            lateral_gain=.13*bell(t,.28,.38)*envelope
            anterior_gain=.16*bell(t,.30,.40)*envelope
            posterior_gain=.14*bell(t,.28,.40)*envelope
        front_gain=anterior_gain if rfront>=0 else posterior_gain
        return [side_radial[i]*lateral_gain+forward[i]*rfront*front_gain for i in range(3)]
