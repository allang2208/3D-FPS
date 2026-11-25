"""Plant the protected sides of existing boundaries and dress actual debris sources."""
import math
import random

import unreal as u


class MainStreet:
    """Arc length and signed offset on the actual cart road, in metres."""
    def __init__(self, plan):
        road = plan['roads'][0]
        self.half = road['width']*.5
        self.spans = []
        start = 0.
        for (ax,ay),(bx,by) in zip(road['points'],road['points'][1:]):
            length = math.hypot(bx-ax,by-ay)
            if length:
                self.spans.append((ax,ay,(bx-ax)/length,(by-ay)/length,length,start))
                start += length

    def project(self,x,y):
        best = math.inf
        for ax,ay,tx,ty,length,start in self.spans:
            along = min(length,max(0.,(x-ax)*tx+(y-ay)*ty))
            dx,dy = x-ax-along*tx,y-ay-along*ty
            dist = dx*dx+dy*dy
            if dist < best:
                best = dist
                station = start+along
                side = math.copysign(math.sqrt(dist),dy*tx-dx*ty)
                tangent = tx,ty
        return station,side,tangent

    def wall_runs(self,plan):
        # Collect connected stretches, irrespective of the direction or length
        # of each kit piece. A real opening splits two separate runs.
        runs = []
        for yard in plan['yard_walls']:
            if not yard.get('roadside'):
                continue
            pieces = []
            for piece in yard['pieces']:
                _,ax,ay,bx,by,top = piece
                sa = self.project(ax,ay)[0]
                sb = self.project(bx,by)[0]
                if sa > sb:
                    sa,sb,ax,ay,bx,by = sb,sa,bx,by,ax,ay
                pieces.append((sa,sb,ax,ay,bx,by,top))
            end = -math.inf
            for piece in sorted(pieces):
                if piece[0] > end+.56:
                    runs.append([])
                runs[-1].append(piece)
                end = max(end,piece[1])
        return runs

    def grow_turf(self,plan,source,scatter):
        density = (source/'VergeTurf.raw').read_bytes()
        width,height = 460,320
        if len(density)!=width*height:
            raise RuntimeError('Invalid village turf field')
        ex,ey = plan.get('surface_extent_m',plan['extent_m'])
        rng = random.Random(62931)
        def cover(x,y):
            col,row = int((x+ex)*width/(2*ex)),int((y+ey)*height/(2*ey))
            return density[row*width+col]/255. if 0<=col<width and 0<=row<height else 0.
        for ax,ay,tx,ty,length,_ in self.spans:
            for _ in range(round(length*15)):
                along = rng.uniform(0.,length)
                offset = rng.choice((-1.,1.))*(self.half+rng.uniform(-.33,4.6))
                cx,cy = ax+tx*along-ty*offset,ay+ty*along+tx*offset
                density_here = cover(cx,cy)
                if density_here<.13 or rng.random()>density_here:
                    continue
                for i in range(rng.randint(2,5)):
                    x = cx+(rng.gauss(0.,.39) if i else 0.)
                    y = cy+(rng.gauss(0.,.39) if i else 0.)
                    strength = cover(x,y)
                    if strength<.13:
                        continue
                    tall = strength>.64 and rng.random()<.24
                    role = rng.choice(('rough','seedhead','bent') if tall else ('tuft','grass','grass','bent'))
                    width_m = rng.uniform(.31,.73)*(.65+.64*strength)
                    scatter(role,x,y,width_m,rng.uniform(-180.,180.),'street_sward')

    def dress(self,plan,scatter,receipts):
        rng = random.Random(813207)
        for run in self.wall_runs(plan):
            length = max(p[1] for p in run)-run[0][0]
            if length<2.1 and rng.random()<.50:
                continue
            # Choose one shoulder and bend the growth around it. Disturbed
            # masonry sheds near one low end; the intact middle rarely sheds.
            first = run[0]
            last = max(run,key=lambda p:p[1])
            root = min((first,last),key=lambda p:p[6]+rng.uniform(-.14,.14))
            start_end = root is first
            k = rng.uniform(.18,.68)
            x = root[2]+k*(root[4]-root[2])
            y = root[3]+k*(root[5]-root[3])
            _,offset,(tx,ty) = self.project(x,y)
            sign = math.copysign(1.,offset)
            nx,ny = -ty*sign,tx*sign
            angle = math.degrees(math.atan2(ty,tx))
            run_direction = 1. if start_end else -1.
            reach = rng.uniform(1.4,min(5.6,max(2.,length)))
            spread = rng.uniform(1.1,2.25)
            planted = 0
            if root[6]<.98:
                # The apron of a low wall end: larger pieces at the break,
                # embedded splinters further into the soil. No trail along the wall.
                for _ in range(rng.randint(11,22)):
                    ualong = rng.triangular(-1.35,.62,-.24)*run_direction
                    across = -rng.triangular(.31,1.0,.43)
                    size = rng.uniform(.07,.22)*(1.-.24*min(1.,abs(ualong)))
                    planted += scatter(rng.choice(('shard','stone')),x+tx*ualong+nx*across,
                                       y+ty*ualong+ny*across,size,angle+rng.uniform(-83.,83.),'street_scree')
            for _ in range(95):
                # Interlocking lobes extend from the yard through to the road
                # face. Each has a different width; the longest tapers away.
                lobe = rng.choices((0,1,2),weights=(4,4,2))[0]
                theta = rng.uniform(0.,math.tau)
                rad = math.sqrt(rng.random())
                center_u = (reach*.25,-.25,reach*.78)[lobe]
                center_v = (.47,-.49,.02)[lobe]
                ualong = (center_u+math.cos(theta)*rad*(reach*.65,.98,reach*.42)[lobe])*run_direction
                across = center_v+math.sin(theta)*rad*(spread,.78,.62)[lobe]
                px,py = x+tx*ualong+nx*across,y+ty*ualong+ny*across
                edge = abs(self.project(px,py)[1])-self.half
                if edge<-.38 or edge>3.8:
                    continue
                worn = edge<.33
                rough = edge>.78 and rng.random()<(.46 if across<0 else .68)
                if worn:
                    role,size = rng.choice(('grass','grass','bent')),rng.uniform(.15,.38)
                elif rough:
                    role,size = rng.choice(('rough','seedhead','herb','bent')),rng.uniform(.44,.91)
                else:
                    role,size = rng.choice(('grass','tuft','bent')),rng.uniform(.29,.63)
                planted += scatter(role,px,py,size,angle+rng.uniform(-88.,88.),'street_grass')
            if planted:
                receipts.append(('street_wall_end',round(x,1),round(y,1),planted))

        # On the open side of a street a field can run down to the shoulder.
        # Extend the existing ground cover only where the field actually meets it.
        for x,y,rx,ry in plan['meadows']:
            _,offset,(tx,ty) = self.project(x,y)
            sign = math.copysign(1.,offset)
            nx,ny = -ty*sign,tx*sign
            depth = 1./math.hypot(nx/rx,ny/ry)
            to_field = abs(offset)-depth-self.half
            if to_field>2.55 or abs(offset)<self.half:
                continue
            toe = self.half+.12
            span = min(5.2,1./math.hypot(tx/rx,ty/ry))
            placed = 0
            for _ in range(92):
                t = rng.uniform(-1.,1.)
                back = 2.8*(1.-t*t)
                outward = toe+rng.uniform(0.,back)+.71*t
                if outward < self.half-.26:
                    continue
                px = x+tx*t*span+nx*(outward-abs(offset))
                py = y+ty*t*span+ny*(outward-abs(offset))
                if outward-self.half < .45:
                    role,size = rng.choice(('grass','bent')),rng.uniform(.18,.41)
                else:
                    role,size = rng.choice(('bent','grass','tuft','rough','seedhead')),rng.uniform(.42,.87)
                placed += scatter(role,px,py,size,rng.uniform(-180.,180.),'street_grass')
            if placed:
                receipts.append(('street_meadow_toe',round(x,1),round(y,1),placed))


def _street_side(x, y, roads):
    nearest = None
    for road in roads:
        for (ax, ay), (bx, by) in zip(road['points'], road['points'][1:]):
            dx, dy = bx-ax, by-ay
            t = max(0., min(1., ((x-ax)*dx+(y-ay)*dy)/max(dx*dx+dy*dy, .0001)))
            vx, vy = x-ax-t*dx, y-ay-t*dy
            distance = math.hypot(vx, vy)
            if nearest is None or distance-road['width']*.5 < nearest[0]:
                nearest = distance-road['width']*.5, vx/max(distance,.001), vy/max(distance,.001)
    return nearest[1:]


def _tree_and_rubble(world):
    sources = []
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
        if not actor.get_actor_label().startswith('Village_'):
            continue
        for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh = comp.static_mesh
            if not mesh:
                continue
            name = mesh.get_name()
            if not name.startswith(('SM_H_RubblePile_', 'SM_DeadTree_')):
                continue
            box = mesh.get_bounding_box()
            for i in range(comp.get_instance_count()):
                tr = comp.get_instance_transform(i, True)
                if name.startswith('SM_DeadTree_'):
                    # The pivot is at the trunk. Canopy bounds would put fallen twigs metres away.
                    sources.append(('tree', tr.translation.x*.01, tr.translation.y*.01, ()))
                else:
                    mid = u.MathLibrary.transform_location(tr, (box.min+box.max)*.5)
                    corners = [u.MathLibrary.transform_location(tr, u.Vector(x,y,box.min.z))
                               for x in (box.min.x, box.max.x) for y in (box.min.y, box.max.y)]
                    sources.append(('rubble', mid.x*.01, mid.y*.01,
                                    tuple(((p.x-mid.x)*.01, (p.y-mid.y)*.01) for p in corners)))
    return sorted(sources)


def dress_boundaries(world, plan, scatter):
    rng = random.Random(41729)
    receipts = []
    roads = plan['roads']
    for yard in plan['yard_walls']:
        # A few irregular stands behind each wall. Broken runs and gate openings
        # remain visible; grass never jumps the wall to find free space.
        last = []
        for j, piece in enumerate(yard['pieces']):
            _, ax, ay, bx, by, _ = piece
            length = math.hypot(bx-ax, by-ay)
            if length < .8 or rng.random() > .64:
                continue
            tx, ty = (bx-ax)/length, (by-ay)/length
            t = rng.uniform(.25,.75)
            x, y = ax+t*(bx-ax), ay+t*(by-ay)
            if any(math.hypot(x-p,y-q) < 2.8 for p,q in last):
                continue
            nx, ny = -ty, tx
            away_x, away_y = _street_side(x,y,roads)
            if nx*away_x+ny*away_y < 0.:
                nx, ny = -nx, -ny
            widths = yard.get('native_instances')
            wall = widths[j]['half_width_m'] if widths else .26
            angle = math.degrees(math.atan2(ty,tx))

            def plant(role, along, depth, size):
                return scatter(role, x+tx*along+nx*(wall+depth), y+ty*along+ny*(wall+depth),
                               size, angle+rng.uniform(-35,35), 'wall_foot')

            if not plant('rough' if not yard.get('roadside') else 'tuft', 0., .70, rng.uniform(.55,.79)):
                continue
            last.append((x,y))
            planted = 1
            for _ in range(14):
                along = rng.uniform(-min(1.3,t*length),min(1.3,(1.-t)*length))
                depth = rng.uniform(.34,1.18)
                role = rng.choice(('herb','tuft','rough')) if depth<.68 else rng.choice(('grass','tuft'))
                planted += plant(role, along, depth, rng.uniform(.32,.61))
            receipts.append(('wall_foot',round(x,1),round(y,1),planted))

    for kind, x, y, corners in _tree_and_rubble(world):
        nx, ny = _street_side(x,y,roads)
        heading = math.degrees(math.atan2(ny,nx))
        # Sample an irregular arc on the sheltered side. The support radius is
        # measured per direction, since most rubble meshes are elongated.
        placed = 0
        for i in range(36):
            angle = math.radians(heading+rng.uniform(-72.,72.))
            vx, vy = math.cos(angle), math.sin(angle)
            if kind == 'tree':
                distance = rng.uniform(.88,1.72)
                role = rng.choice(('leaf','rough','herb','tuft')) if distance<1.32 else rng.choice(('twig','grass'))
                width = rng.uniform(.34,.66)
            else:
                extension = rng.uniform(.08,.95)
                # Intersect this ray with the two slab pairs of the oriented box.
                radii = []
                for opposite in (1,2):
                    dx = (corners[opposite][0]-corners[0][0])*.5
                    dy = (corners[opposite][1]-corners[0][1])*.5
                    dot = abs(dx*vx+dy*vy)
                    if dot > .0001:
                        radii.append((dx*dx+dy*dy)/dot)
                distance = min(radii,default=1.)+extension
                if extension < .42:
                    role, width = rng.choice(('shard','stone','tuft')), rng.uniform(.24,.43)
                else:
                    role, width = rng.choice(('shard','grass','herb')), rng.uniform(.14,.29)
            placed += scatter(role, x+vx*distance, y+vy*distance, width,
                              math.degrees(angle)+rng.uniform(-24.,24.), kind+'_edge')
        if placed:
            receipts.append((kind,round(x,1),round(y,1),placed))
    # The uncut headland connects the original two meadow ends behind the
    # dwellings. Its taller seed heads follow the back, away from the yard lane.
    left,right = (plan['meadows'][i] for i in plan['common_meadow_edges'])
    dx,dy = right[0]-left[0],right[1]-left[1]
    length = math.hypot(dx,dy)
    tx,ty = dx/length,dy/length
    heading = math.degrees(math.atan2(dy,dx))
    placed = 0
    for _ in range(500):
        t = rng.uniform(.10,.94)
        w = .8+2.1*math.sin(t*math.pi)**.8
        side = rng.uniform(-1.,1.)
        # Shallow bows produce one continuous but variable meadow edge.
        offset = -.85-1.15*math.sin(2.3*math.pi*t)+w*side
        x,y = left[0]+t*dx-ty*offset,left[1]+t*dy+tx*offset
        if abs(side)>.74 and rng.random()>.48:
            continue
        if side<-.42:
            role,size = rng.choice(('grass','tuft','bent')),rng.uniform(.42,.79)
        elif side>.02:
            role,size = rng.choice(('rough','seedhead','bent','tuft')),rng.uniform(.74,1.22)
        else:
            role,size = rng.choice(('seedhead','bent','herb','grass')),rng.uniform(.53,.97)
        placed += scatter(role,x,y,size,heading+rng.uniform(-58.,58.),'common_meadow')
    if placed:
        receipts.append(('common_meadow',round((left[0]+right[0])*.5,1),round((left[1]+right[1])*.5,1),placed))
    return receipts
