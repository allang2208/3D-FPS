import struct, zlib, sys, os, math, collections

def parse_props(data, pos, count):
    props = []
    for _ in range(count):
        t = data[pos]; pos += 1
        c = chr(t)
        if c == 'Y': v = struct.unpack_from('<h', data, pos)[0]; pos += 2
        elif c == 'C': v = bool(data[pos]); pos += 1
        elif c == 'I': v = struct.unpack_from('<i', data, pos)[0]; pos += 4
        elif c == 'F': v = struct.unpack_from('<f', data, pos)[0]; pos += 4
        elif c == 'D': v = struct.unpack_from('<d', data, pos)[0]; pos += 8
        elif c == 'L': v = struct.unpack_from('<q', data, pos)[0]; pos += 8
        elif c == 'R': ln = struct.unpack_from('<I', data, pos)[0]; pos += 4; v = data[pos:pos+ln]; pos += ln
        elif c == 'S':
            ln = struct.unpack_from('<I', data, pos)[0]; pos += 4
            v = data[pos:pos+ln].split(b'\x00\x01')[0].decode('utf-8', 'replace'); pos += ln
        elif c in 'fdilb':
            alen, enc, clen = struct.unpack_from('<III', data, pos); pos += 12
            sz = {'f':4,'d':8,'i':4,'l':8,'b':1}[c]
            buf = zlib.decompress(data[pos:pos+clen]) if enc else data[pos:pos+alen*sz]
            pos += clen if enc else alen*sz
            fmt = {'f':'<%df','d':'<%dd','i':'<%di','l':'<%dq','b':'<%db'}[c] % alen
            v = list(struct.unpack(fmt, buf))
        else:
            raise ValueError('unknown prop type %r' % c)
        props.append(v)
    return pos, props

def parse_fbx(path):
    data = open(path,'rb').read()
    ver = struct.unpack_from('<I', data, 23)[0]
    big = ver >= 7500
    rec_min = 25 if big else 13
    def walk_nodes(pos, end):
        nodes_list = []
        while pos + rec_min <= end:
            if big:
                noff, nprops, plen = struct.unpack_from('<QQQ', data, pos)
                nlen = data[pos+24]; name = data[pos+25:pos+25+nlen].decode('utf-8','replace'); hpos = pos + 25 + nlen
            else:
                noff, nprops, plen = struct.unpack_from('<III', data, pos)
                nlen = data[pos+12]; name = data[pos+13:pos+13+nlen].decode('utf-8','replace'); hpos = pos + 13 + nlen
            if noff == 0:
                break
            p2, props = parse_props(data, hpos, nprops)
            children = []
            if p2 < noff:
                children = walk_nodes(p2, noff)
            nodes_list.append((name, props, children))
            pos = noff
        return nodes_list
    return walk_nodes(27, len(data)), ver

def analyze(path):
    tree, ver = parse_fbx(path)
    print('%s  fbx_ver=%d' % (os.path.basename(path), ver))
    # collect objects: Geometry id -> {verts, polyidx, matlayer}, Model id -> name
    geos = {}
    models = {}
    conns = []  # (type, child, parent)
    for top in tree:
        if top[0] == 'Objects':
            for obj in top[2]:
                if obj[0] == 'Geometry':
                    gid = obj[1][0] if obj[1] else -1
                    g = {'verts': None, 'poly': None, 'mat': None, 'matmap': None}
                    for ch in obj[2]:
                        if ch[0] == 'Vertices' and ch[1] and isinstance(ch[1][0], list):
                            g['verts'] = ch[1][0]
                        elif ch[0] == 'PolygonVertexIndex' and ch[1] and isinstance(ch[1][0], list):
                            g['poly'] = ch[1][0]
                        elif ch[0] == 'LayerElementMaterial':
                            for gch in ch[2]:
                                if gch[0] == 'MappingInformationType': g['matmap'] = gch[1][0]
                                elif gch[0] == 'Materials' and gch[1] and isinstance(gch[1][0], list): g['mat'] = gch[1][0]
                    geos[gid] = g
                elif obj[0] == 'Model':
                    mid = obj[1][0] if obj[1] else -1
                    name = obj[1][1] if len(obj[1]) > 1 else ''
                    models[mid] = name
        elif top[0] == 'Connections':
            for c in top[2]:
                if c[0] == 'C' and len(c[1]) >= 3:
                    conns.append((c[1][0], c[1][1], c[1][2]))
    # geometry -> model name
    geo_model = {}
    for ctype, child, parent in conns:
        if child in geos and parent in models:
            geo_model[child] = models[parent]
    for gid, g in geos.items():
        v = g['verts']
        if v is None: continue
        n = len(v)//3
        xs, ys, zs = v[0::3], v[1::3], v[2::3]
        name = geo_model.get(gid, '?')
        print('  geo %s (%s): verts=%d  min=(%.1f,%.1f,%.1f) max=(%.1f,%.1f,%.1f)' % (
            gid, name, n, min(xs),min(ys),min(zs), max(xs),max(ys),max(zs)))
        # outlier verts: far from median center
        mx = sorted(xs)[n//2]; my = sorted(ys)[n//2]; mz = sorted(zs)[n//2]
        outliers = []
        for i in range(n):
            dx,dy,dz = xs[i]-mx, ys[i]-my, zs[i]-mz
            d = math.sqrt(dx*dx+dy*dy+dz*dz)
            if d > 60:  # > 60cm (or 60 units) from median
                outliers.append((d,i,xs[i],ys[i],zs[i]))
        outliers.sort(reverse=True)
        if outliers:
            print('    OUTLIERS (dist from median>60):')
            for d,i,x,y,z in outliers[:25]:
                print('      v%-6d d=%8.1f  (%.2f, %.2f, %.2f)' % (i,d,x,y,z))
        # sliver triangles: longest edge >= 30 while shortest <= 3 (aspect >=10) or area tiny
        if g['poly']:
            polys = []
            cur = []
            for idx in g['poly']:
                if idx < 0:
                    cur.append(~idx); polys.append(cur); cur = []
                else:
                    cur.append(idx)
            # material per poly
            mats = g['mat'] if g['mat'] else None
            slivers = []
            for pi, poly in enumerate(polys):
                # triangulate fan for edge check; check all consecutive pairs + closing
                pts = [(xs[i],ys[i],zs[i]) for i in poly]
                m = mats[pi] if mats and pi < len(mats) else -1
                el = []
                k = len(pts)
                for a in range(k):
                    b = (a+1) % k
                    d = math.dist(pts[a],pts[b]); el.append(d)
                # also diagonals for quads
                if k >= 4:
                    for a in range(k):
                        for b in range(a+2,k):
                            if a==0 and b==k-1: continue
                            el.append(math.dist(pts[a],pts[b]))
                if not el: continue
                lmax, lmin = max(el), min(el)
                if lmax >= 40 and (lmin <= 3 or lmax/max(lmin,1e-6) >= 15):
                    slivers.append((lmax,lmin,pi,m,poly,pts))
            slivers.sort(key=lambda s:-s[0])
            print('    slivers(longest>=40 & thin): %d' % len(slivers))
            for lmax,lmin,pi,m,poly,pts in slivers[:30]:
                pstr = ' '.join('(%.1f,%.1f,%.1f)' % p for p in pts)
                print('      poly%-6d mat=%d n=%d L=%.1f/%.1f  verts: %s' % (pi,m,len(pts),lmax,lmin,pstr[:150]))

if __name__ == "__main__":
    for path in sys.argv[1:]:
        try:
            analyze(path)
        except Exception:
            import traceback
            traceback.print_exc()
