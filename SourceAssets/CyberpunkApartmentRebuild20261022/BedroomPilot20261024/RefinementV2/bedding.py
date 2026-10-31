"""Keep the existing bed frame; rebuild mutually clear mattress, pillows and covers."""
audit=R/'Audit/before'
capture=json.loads((audit/'components.json').read_text('utf8'))
bedrow=next(r for r in capture['components'] if r['actor']=='AP_Bed2_Bed')
native=json.loads((audit/(bedrow['key']+'.json')).read_text('utf8'))
roles={'AP_Oak':'Walnut','AP_Dark':'Graphite','AP_Brass':'Copper','AP_Warm':'WarmDiffuser'}
verts=[(v[0]/100,-v[1]/100,v[2]/100) for v in native['vertices']]
for slot,role in enumerate(bedrow['slots']):
    if role not in roles:continue
    faces=[tuple(reversed(t)) for t,m in zip(native['triangles'],native['materials']) if m==slot]
    used=sorted({v for f in faces for v in f});remap={v:i for i,v in enumerate(used)}
    g.poly('BedRefined',[verts[v] for v in used],[tuple(remap[v] for v in f) for f in faces],roles[role],smooth=False)
# Existing physical support remains at the original 67 cm rest plane.
roundbox('BedRefined',(0,.01,.4975),(1.5,2.05,.235),'FogLinen',.055,8)
for z in (.405,.593):pipe('BedRefined',loop(0,.01,z,1.48,2.03,.07),.0025,'FogLinen',8)
for x in (-.375,.375):
    roundbox('BedRefined',(x,1.116,1.0),(.72,.07,.74),'CharcoalWeave',.035,7)
    for z in (.70,1.30):pipe('BedRefined',[(x-.31,1.078,z),(x+.31,1.078,z)],.0016,'FogLinen',7)

def pillow_supported(cx):
    nx=52;ny=34;w=.67;d=.46;vs=[];fs=[];uv=[]
    for side in (1,-1):
        for j in range(ny+1):
            b=-1+2*j/ny
            for i in range(nx+1):
                a=-1+2*i/nx;bulge=max(0,(1-a*a)*(1-b*b))
                x=cx+a*w/2*(1-.06*abs(b)**8);y=.75+b*d/2*(1-.06*abs(a)**8)
                z=.617 if side<0 else .631+.139*bulge**.65+.0025*math.sin(a*20+b*5)*abs(b)**5*(1-a*a)
                vs.append((x,y,z))
    n=(nx+1)*(ny+1)
    for layer in range(2):
        for j in range(ny):
            for i in range(nx):
                a=layer*n+j*(nx+1)+i;face=(a,a+1,a+nx+2,a+nx+1)
                fs.append(face if layer==0 else tuple(reversed(face)))
                uv.append(None)
    edge=list(range(nx+1))+[j*(nx+1)+nx for j in range(1,ny+1)]+[ny*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(ny-1,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]):fs.append((a,a+n,b+n,b));uv.append(None)
    g.poly('BedRefined',vs,fs,'FogLinen',uv=uv,smooth=True)
    pipe('BedRefined',[(vs[i][0],vs[i][1],.628) for i in edge]+[(vs[edge[0]][0],vs[edge[0]][1],.628)],.0015,'FogLinen',8)
for x in (-.375,.375):pillow_supported(x)

def duvet_top(x,y):
    sx=max(0,min(1,(abs(x)-.72)/.16));sy=max(0,min(1,(-y-.94)/.23))
    return .661-.21*max(sx,sy)**1.5+.004*math.sin(x*15+y*7)*(1-max(sx,sy))+.003*math.sin(y*23+x*4)*(1-max(sx,sy))

def cover(k,x0,x1,y0,y1,offset,thickness,mat,nx,ny):
    vs=[];fs=[];uv=[]
    for side in (1,0):
        for j in range(ny+1):
            y=y0+(y1-y0)*j/ny
            for i in range(nx+1):
                x=x0+(x1-x0)*i/nx
                vs.append((x,y,duvet_top(x,y)+offset+(thickness if side else 0)))
    n=(nx+1)*(ny+1)
    for layer in (0,1):
        for j in range(ny):
            for i in range(nx):
                a=layer*n+j*(nx+1)+i;f=(a,a+1,a+nx+2,a+nx+1)
                face=f if layer==0 else tuple(reversed(f));fs.append(face)
                uv.append([((vs[q][0]-x0),(vs[q][1]-y0)) for q in face])
    edge=list(range(nx+1))+[j*(nx+1)+nx for j in range(1,ny+1)]+[ny*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(ny-1,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]):fs.append((a,a+n,b+n,b));uv.append(None)
    g.poly(k,vs,fs,mat,uv=uv,smooth=True)
    pipe(k,[vs[i] for i in edge]+[vs[edge[0]]],.0017,'FogLinen',8)
cover('BedRefined',-.88,.88,-1.17,.48,-.018,.018,'CharcoalWeave',96,84)
cover('FootThrow',-.865,.865,-.82,-.35,.006,.006,'OchreCloth',96,40)
for side in (-1,1):
    for j in range(25):
        y=-.80+j*.018;x=side*.865;z=duvet_top(x,y)+.011
        pipe('FootThrow',[(x,y,z),(side*.888,y+.004,duvet_top(side*.88,y)+.013),(side*.902,y-.003,.420)],.0012,'OchreCloth',6)
# Frame and mattress support volumes are scoped to the revised bed asset.
g.box(None,(0,0,.24),(1.64,2.22,.28),collision='BedRefined')
g.box(None,(0,.01,.4975),(1.50,2.05,.235),collision='BedRefined')
g.box(None,(0,1.18,.91),(2.,.10,1.42),collision='BedRefined')
