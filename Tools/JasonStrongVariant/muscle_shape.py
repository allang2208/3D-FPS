"""Anatomical body morph in Jason's native centimetre bind pose.

Only positions change. Bone transforms, topology, UVs and skin weights are retained.
This module is shared by the Blender source and all UE LODs.
"""
import math

def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)

def bell(x, center, width):
    return math.exp(-((x - center) / width) ** 2)

def groups_for_bones(bones):
    by_index = {b['index']: b for b in bones}
    groups = {}
    for bone in bones:
        cursor, group = bone, 'torso'
        while cursor:
            name = cursor['name']
            if name.startswith(('neck_', 'FACIAL_')) or name == 'head':
                group = 'fixed'; break
            matched = False
            for part in ('hand', 'foot', 'ball', 'lowerarm', 'upperarm', 'calf', 'thigh'):
                if name in (part + '_l', part + '_r'):
                    group = ('fixed' if part in ('hand', 'foot', 'ball') else name)
                    matched = True; break
            if matched:
                break
            cursor = by_index.get(cursor['parent'])
        groups[bone['index']] = group
    return groups

def neck_seam(data):
    """Find the true collar boundary, ignoring duplicate UV/material seam vertices."""
    positions=data['positions']
    canonical={}
    weld=[]
    for p in positions:
        key=tuple(round(v,3) for v in p)
        if key not in canonical:canonical[key]=len(canonical)
        weld.append(canonical[key])
    edges={}
    for triangle in data['triangles']:
        for a,b in ((triangle[0],triangle[1]),(triangle[1],triangle[2]),(triangle[2],triangle[0])):
            if min(positions[a][2],positions[b][2])<120 or max(abs(positions[a][0]),abs(positions[b][0]))>28:
                continue
            key=tuple(sorted((weld[a],weld[b])))
            count,pair=edges.get(key,(0,(a,b)))
            edges[key]=(count+1,pair)
    return [[positions[a],positions[b]] for count,(a,b) in edges.values() if count==1]

def distance_to_segment(p,a,b):
    ab=[b[i]-a[i] for i in range(3)]
    length=sum(v*v for v in ab)
    t=max(0.,min(1.,sum((p[i]-a[i])*ab[i] for i in range(3))/max(length,1e-12)))
    return sum((p[i]-a[i]-t*ab[i])**2 for i in range(3))**.5

class MuscleShape:
    def __init__(self, bones, strength=1.0, seam_segments=()):
        self.bones = {b['name']: b['position'] for b in bones}
        self.groups = groups_for_bones(bones)
        self.strength = strength
        self.seam_segments = seam_segments

    def limb(self, p, group):
        part, side = group.rsplit('_', 1)
        next_part = {'upperarm': 'lowerarm', 'lowerarm': 'hand', 'thigh': 'calf', 'calf': 'foot'}[part]
        a, b = self.bones[group], self.bones[next_part + '_' + side]
        axis = [b[i] - a[i] for i in range(3)]
        t = sum((p[i] - a[i]) * axis[i] for i in range(3)) / sum(v*v for v in axis)
        radial = [p[i] - a[i] - axis[i]*t for i in range(3)]
        if part == 'upperarm':
            # Rounded deltoid and substantial biceps/triceps, tapered into elbow.
            gain = (0.34*bell(t, .04, .28) + .32*bell(t, .43, .31))
            gain *= smooth(-.28, -.06, t) * (1-smooth(.79, .99, t))
        elif part == 'lowerarm':
            gain = .25*bell(t, .32, .30) * smooth(-.05, .12, t) * (1-smooth(.68, .88, t))
        elif part == 'thigh':
            gain = (.12*bell(t, .03, .28) + .22*bell(t, .38, .35))
            gain *= smooth(-.30, -.05, t) * (1-smooth(.78, 1.0, t))
        else:
            gain = .19*bell(t, .35, .25) * smooth(.0, .16, t) * (1-smooth(.64, .85, t))
        return [v*gain for v in radial]

    def torso(self, p):
        x, y, z = p
        ax = abs(x)
        chest = bell(z, 126., 17.)
        lats = bell(z, 117., 17.)
        waist = bell(z, 97., 12.)
        dx = x*(.145*chest + .055*lats + .022*waist)
        front = smooth(-1.5, 6.0, y)
        back = 1-smooth(-6.0, 1.5, y)
        # Paired pectoral fullness, retaining a central sternum transition.
        pec = bell(ax, 8., 7.5)*bell(z, 128., 9.5)
        dy = front*(2.35*pec + .55*bell(z, 117., 18.))
        dy -= back*(1.25*bell(z, 126., 15.) + .75*bell(z, 111., 20.))
        # Small abdominal and glute increase balances the larger upper body.
        dy += .35*front*bell(z, 101., 13.)
        dy -= .80*back*bell(z, 86., 9.)
        dx += x*.035*bell(z, 86., 9.)
        # Keep the independent head and native neck seam untouched.
        neck_fade = 1-smooth(140., 147., z)
        low_fade = smooth(72., 84., z)
        return [dx*neck_fade*low_fade, dy*neck_fade*low_fade, 0.0]

    def deform(self, p, weights):
        groups = {}
        for index, weight in weights:
            group = self.groups[index]
            groups[group] = groups.get(group, 0.) + weight
        delta = [0., 0., 0.]
        for group, weight in groups.items():
            if group == 'fixed':
                continue
            d = self.torso(p) if group == 'torso' else self.limb(p, group)
            for i in range(3):
                delta[i] += weight*d[i]
        # Enforce exact neck/foot boundaries regardless of corrective influences.
        fade = (1-smooth(143., 147., p[2]))*smooth(12., 21., p[2])
        # Preserve the narrow native contact folds. Expanding opposite sides of
        # the crotch or the inner upper arm can otherwise invert small faces.
        crotch_band=smooth(60.,68.,p[2])*(1-smooth(80.,89.,p[2]))
        fade*=1-crotch_band*(1-smooth(2.,8.,abs(p[0])))
        armpit_radius=(((abs(p[0])-16.2)/4.)**2+((p[1]+4.5)/8.)**2+((p[2]-130.)/7.)**2)**.5
        fade*=smooth(.75,1.8,armpit_radius)
        if fade>0 and any(abs(v)>1e-10 for v in delta) and p[2]>114 and abs(p[0])<35 and self.seam_segments:
            distance=min(distance_to_segment(p,a,b) for a,b in self.seam_segments)
            fade*=smooth(.3,6.0,distance)
        return [p[i]+delta[i]*fade*self.strength for i in range(3)]
