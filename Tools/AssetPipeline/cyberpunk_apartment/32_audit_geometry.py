"""Requested source audit: complete mesh matrix and conservative 2D capsule
clearance/connectivity. This is geometry evidence, not a UE physics/PIE test.
"""
import importlib.util
import json
import numpy as np
from scipy import ndimage
from playable_config import ROOT, SCALE, COMPLEX, ROOMS, SPAWN_XY

spec = importlib.util.spec_from_file_location('geo', __file__.replace('32_audit_geometry.py','00_gltf_geometry.py'))
geo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geo)
geo.EXPORT = str(ROOT/'export')
geo.GLTF = str(ROOT/'export/CyberpunkApartmentPlayable.gltf')
geo.OUT = str(ROOT/'geometry.json')
geo.main()
data = json.loads((ROOT/'geometry.json').read_text())['meshes']
step = 5.0
x0, y0 = -100., -1800.
nx, ny = 440, 470
occupied = np.zeros((ny,nx), dtype=bool)
owners = np.zeros((ny,nx), dtype=np.int16)
matrix=[]
for num, (name, entry) in enumerate(data.items(),1):
    collision = name in COMPLEX
    matrix.append(dict(name=name, triangles=entry['tris'], collision='complex' if collision else
        ('door_component' if name.startswith('DoorAsset_') else 'none'),
        nanite_candidate=entry['tris']>=10000 and not name.startswith('DoorAsset_'),
        bounds_cm=[entry['min'],entry['max']]))
    if not collision:
        continue
    p = np.asarray(entry['positions'])*SCALE
    t = p[np.asarray(entry['indices']).reshape(-1,3)]
    # Ignore the low walkable threshold, surfaces below the sole and ceilings.
    t = t[(t[:,:,2].max(1)>45) & (t[:,:,2].min(1)<192)]
    # Project only the portion intersecting the body's standing height.
    for tri in t:
        poly = list(tri)
        for z, sign in ((45,1),(192,-1)):
            clip=[]
            for a,b in zip(poly, poly[1:]+poly[:1]):
                ia,ib = (a[2]-z)*sign>=0, (b[2]-z)*sign>=0
                if ia:clip.append(a)
                if ia != ib:clip.append(a+(b-a)*((z-a[2])/(b[2]-a[2])))
            poly=clip
            if not poly:break
        if not poly:continue
        v=np.asarray(poly)[:,:2]
        v=(v-np.array([x0,y0]))/step
        ix0,iy0=np.floor(v.min(0)).astype(int)
        ix1,iy1=np.ceil(v.max(0)).astype(int)
        ix0,iy0=max(ix0,0),max(iy0,0)
        ix1,iy1=min(ix1,nx-1),min(iy1,ny-1)
        if ix1<ix0 or iy1<iy0:continue
        # Rasterize polygon interior and edges, including vertical surfaces.
        yy,xx=np.mgrid[iy0:iy1+1,ix0:ix1+1]
        inside=np.ones(xx.shape,dtype=bool)
        signs=[]
        for a,b in zip(v,np.roll(v,-1,axis=0)):
            cross=(b[0]-a[0])*(yy-a[1])-(b[1]-a[1])*(xx-a[0])
            signs.append(cross)
        signs=np.asarray(signs)
        inside=(signs>=-.01).all(0)|(signs<=.01).all(0)
        # Edges conservatively rounded to nearest cell.
        occupied[iy0:iy1+1,ix0:ix1+1] |= inside
        owners[iy0:iy1+1,ix0:ix1+1][inside]=num
        for a,b in zip(v,np.roll(v,-1,axis=0)):
            points=np.rint(np.linspace(a,b,max(2,int(np.linalg.norm(b-a)*2)+1))).astype(int)
            ok=(points[:,0]>=0)&(points[:,0]<nx)&(points[:,1]>=0)&(points[:,1]<ny)
            points=points[ok]
            occupied[points[:,1],points[:,0]]=True
            owners[points[:,1],points[:,0]]=num

distance=ndimage.distance_transform_edt(~occupied)*step
free=distance>=45
# Supported area excludes open sky around the slab.
floor=np.zeros_like(free)
for bounds in list(ROOMS.values())+[(0,1600,-1100,0)]:
    a,b,c,d=np.array(bounds)*SCALE
    floor[max(0,int((c-y0)/step)):min(ny,int((d-y0)/step)+1),
          max(0,int((a-x0)/step)):min(nx,int((b-x0)/step)+1)]=True
free &= floor
labels,count=ndimage.label(free)
sx,sy=SPAWN_XY[0]*SCALE,-SPAWN_XY[1]*SCALE
ix,iy=round((sx-x0)/step),round((sy-y0)/step)
origin=int(labels[iy,ix])
spawn_clearance=float(distance[iy,ix])
room_report={}
for name,bounds in ROOMS.items():
    a,b,c,d=np.array(bounds)*SCALE
    region=labels[int((c-y0)/step):int((d-y0)/step)+1,int((a-x0)/step):int((b-x0)/step)+1]
    ys,xs=np.where(region==origin) if origin else ([],[])
    room_report[name]={'reachable_free_cells':len(xs),'reachable':bool(len(xs))}

# Useful door cross-sections for diagnosing remaining modelling obstructions.
doors=json.loads((ROOT/'authoring.json').read_text())['doors']
door_report=[]
for d in doors:
    x,y=d['x']*SCALE,d['y']*SCALE
    ix,iy=round((x-x0)/step),round((y-y0)/step)
    door_report.append(dict(name=d['name'],width_cm=d['width_cm'],height_cm=d['height_cm'],
                            centre_clearance_cm=round(float(distance[iy,ix]),1)))
report=dict(method='5 cm raster, 45 cm radius incl. margin; body band 45..192 cm; open doors',
            scale=SCALE,capsule_cm=[42,96],spawn_free=bool(origin),
            spawn_clearance_cm=spawn_clearance,rooms=room_report,doors=door_report,meshes=matrix)
(ROOT/'geometry_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
np.savez_compressed(ROOT/'clearance_grid.npz',distance=distance,labels=labels,owners=owners,
                    names=np.array(list(data)),origin=origin,x0=x0,y0=y0,step=step)
print(json.dumps({'spawn_free':bool(origin),'rooms':room_report,'doors':door_report},indent=2))
