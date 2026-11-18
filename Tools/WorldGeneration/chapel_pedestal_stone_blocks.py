"""Closed, bevelled fieldstone courses matching the chapel's low-wall caps."""
import math
import random

def build():
    data={k:[] for k in ('vertices','normals','uv0','uv1','colors','triangles')}
    def triangle(a,b,c,color,offset):
        ab=[b[i]-a[i] for i in range(3)];ac=[c[i]-a[i] for i in range(3)]
        n=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
        length=math.sqrt(sum(v*v for v in n))
        if length<1e-8:raise ValueError('Degenerate stone face')
        n=[v/length for v in n]
        axes=sorted(range(3),key=lambda i:abs(n[i]))[:2]
        start=len(data['vertices'])
        for p in (a,b,c):
            data['vertices'].append(p);data['normals'].append(n);data['colors'].append(color)
            data['uv0'].append([p[axes[0]]/50.+offset[0],p[axes[1]]/50.+offset[1]])
            data['uv1'].append([p[2]/34.,0.])
        data['triangles'].append([start,start+2,start+1])
    def solid(rings,color,offset):
        count=len(rings[0])
        for lower,upper in zip(rings,rings[1:]):
            for i in range(count):
                j=(i+1)%count
                triangle(lower[i],lower[j],upper[j],color,offset)
                triangle(lower[i],upper[j],upper[i],color,offset)
        for points,reverse in ((rings[0],True),(rings[-1],False)):
            center=[sum(p[k] for p in points)/count for k in range(3)]
            for i in range(count):
                a,b=points[i],points[(i+1)%count]
                triangle(center,b,a,color,offset) if reverse else triangle(center,a,b,color,offset)
    def cylinder(radius,low,high,color):
        rings=[[(radius*math.cos(math.tau*i/96),radius*math.sin(math.tau*i/96),z) for i in range(96)] for z in (low,high)]
        solid(rings,(color,color,color,1.),(0.,0.))
    # Continuous recessed beds preserve solid collision through every shallow joint.
    cylinder(213.,0.,14.5,.25)
    cylinder(181.,14.5,32.5,.25)
    cylinder(99.4,15.,34.,.96)
    rng=random.Random(171116)
    for count,phase,inner,profile in (
        (28,.016,166.,[(214.,0.),(220.,3.),(218.,13.7),(211.,16.)]),
        (20,.071,100.2,[(184.,15.4),(190.,18.),(188.5,31.),(182.5,34.)])):
        cuts=[phase+math.tau*i/count+(.012*math.sin(i*2.37) if i not in (0,count) else 0.) for i in range(count+1)]
        for i in range(count):
            lo,hi=cuts[i]+.0027,cuts[i+1]-.0027
            angles=[lo+(hi-lo)*j/4. for j in range(5)]
            rings=[]
            for row,(outer,z) in enumerate(profile):
                ir=inner+(1.2 if row in (0,len(profile)-1) else 0.)
                ring=[]
                for angle in angles:
                    r=outer+.45*math.sin(angle*31.+i*.37)+.25*math.cos(angle*57.)
                    ring.append((r*math.cos(angle),r*math.sin(angle),z))
                ring.extend((ir*math.cos(angle),ir*math.sin(angle),z) for angle in reversed(angles))
                rings.append(ring)
            tone=rng.uniform(.89,1.08)
            solid(rings,(tone,tone*rng.uniform(.99,1.015),tone*rng.uniform(.985,1.01),1.),(rng.random(),rng.random()))
    data['rows']={'lower_stones':28,'upper_stones':20,'texture_world_cm_per_uv':50.,'joint_depth_cm':1.5}
    return data
