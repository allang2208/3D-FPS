"""Prepare real constellation figures for the twelve pavilion roof panels.

Uses Olaf Frohn's d3-celestial GeoJSON coordinates and line sequences.
The downloaded data and BSD notice remain under References/d3-celestial.
Only a local sky projection and a uniform scale are applied to each figure.
"""
import json
import math
from pathlib import Path

ROOT=Path(__file__).parent
REF=ROOT/'References'/'d3-celestial'
DEG=math.pi/180
SELECTED=[('Gem','Gemini','双子座'),('Leo','Leo','狮子座'),
          ('And','Andromeda','仙女座'),('Per','Perseus','英仙座'),
          ('UMa','Ursa Major','大熊座'),('Aql','Aquila','天鹰座'),
          ('Lyr','Lyra','天琴座'),('Tau','Taurus','金牛座'),
          ('Sco','Scorpius','天蝎座'),('Cyg','Cygnus','天鹅座'),
          ('Ori','Orion','猎户座'),('Cas','Cassiopeia','仙后座')]


def unit(ra,dec):
    a=ra*DEG;d=dec*DEG
    return (math.cos(d)*math.cos(a),math.cos(d)*math.sin(a),math.sin(d))


def dot(a,b):return sum(x*y for x,y in zip(a,b))


def dome_point(x,y,theta):
    phi=45.-y/(4*DEG)
    return (phi,theta+x/(4*math.sin(phi*DEG)*DEG))


def prepare():
    atlas={f['id']:f for f in json.loads((REF/'constellations.lines.json').read_text())['features']}
    catalog=json.loads((REF/'stars.6.json').read_text())['features']
    catalog=[(unit(*s['geometry']['coordinates']),s['properties']['mag']) for s in catalog]
    groups=[]
    for k,(code,name,chinese) in enumerate(SELECTED):
        points=[];edges=[]
        for line in atlas[code]['geometry']['coordinates']:
            chain=[]
            for point in line:
                if point not in points:points.append(point)
                chain.append(points.index(point))
            for a,b in zip(chain,chain[1:]):
                edge=tuple(sorted((a,b)))
                if a!=b and edge not in edges:edges.append(edge)
        vectors=[unit(*p) for p in points]
        centre=[sum(v[i] for v in vectors)/len(vectors) for i in range(3)]
        norm=math.sqrt(dot(centre,centre));centre=[v/norm for v in centre]
        ra=math.atan2(centre[1],centre[0]);dec=math.asin(centre[2])
        east=(-math.sin(ra),math.cos(ra),0.)
        north=(-math.sin(dec)*math.cos(ra),-math.sin(dec)*math.sin(ra),math.cos(dec))
        xy=[(-dot(v,east)/dot(v,centre),dot(v,north)/dot(v,centre)) for v in vectors]
        xmin=min(x for x,y in xy);xmax=max(x for x,y in xy)
        ymin=min(y for x,y in xy);ymax=max(y for x,y in xy)
        scale=min(1.15/(xmax-xmin),1.9/(ymax-ymin))
        xy=[((x-(xmin+xmax)/2)*scale,(y-(ymin+ymax)/2)*scale) for x,y in xy]
        # Fit the narrowing bay without stretching the stellar configuration.
        for _ in range(20):
            if max(abs(dome_point(x,y,0.)[1]) for x,y in xy)<=11.5:break
            xy=[(x*.97,y*.97) for x,y in xy]
        mags=[];sizes=[]
        for i,v in enumerate(vectors):
            score,mag=max((dot(v,s),mag) for s,mag in catalog)
            mag=mag if score>math.cos(.03*DEG) else 4.
            mags.append(mag)
            separation=min(math.dist(xy[i],p) for j,p in enumerate(xy) if j!=i)
            radius=max(.022,min(.086-.010*mag,.29*separation))
            sizes.append(radius)
        groups.append({'id':code,'name':name,'name_zh':chinese,'centre_phi_theta':[45.,k*30+15.],
                       'ra_dec_deg':points,'local_xy_m':xy,'edges':edges,
                       'magnitudes':mags,'star_radius_m':sizes,
                       'points_phi_theta':[dome_point(x,y,k*30+15.) for x,y in xy]})
    data={'source':'https://github.com/ofrohn/d3-celestial/blob/master/data/constellations.lines.json',
          'source_license':'BSD-3-Clause; see References/d3-celestial/LICENSE',
          'projection':'local gnomonic sky chart, north up and east left; uniform scale; wrapped onto dome',
          'layout':'individual architectural panels, not an all-sky atlas',
          'centre_phi':45.,'ring_phi':[74.15,88.5],'scattered_stars':[],'groups':groups}
    (ROOT/'C4_constellations.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1200" viewBox="0 0 1600 1200">',
         '<rect width="1600" height="1200" fill="#101723"/>',
         '<text x="40" y="40" fill="#ead7ab" font-family="sans-serif" font-size="24">C4 / Real constellation figures / North up, east left</text>']
    for i,g in enumerate(groups):
        ox=200+(i%4)*400;oy=215+(i//4)*370
        xy=g['local_xy_m']
        def screen(p):return (ox+p[0]*175,oy-p[1]*175)
        for a,b in g['edges']:
            x0,y0=screen(xy[a]);x1,y1=screen(xy[b])
            svg.append(f'<path d="M{x0:.2f},{y0:.2f} L{x1:.2f},{y1:.2f}" stroke="#cfb273" stroke-width="1.8"/>')
        for j,p in enumerate(xy):
            x,y=screen(p)
            svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{max(2,g["star_radius_m"][j]*72):.2f}" fill="#f8ecd1"/>')
        svg.append(f'<text x="{ox}" y="{oy+185}" text-anchor="middle" fill="#eee2c7" font-family="sans-serif" font-size="21">{g["id"]} / {g["name"]}</text>')
    svg.append('<text x="40" y="1180" fill="#acb4be" font-family="sans-serif" font-size="15">Coordinates and line figures: d3-celestial / Olaf Frohn. BSD-3-Clause. Individual figures scaled for roof panels.</text></svg>')
    (ROOT/'previews'/'C4_constellation_reference.svg').write_text('\n'.join(svg),encoding='utf-8')
    print('C4 reference figures prepared: '+', '.join(g['id'] for g in groups))


if __name__=='__main__':prepare()
