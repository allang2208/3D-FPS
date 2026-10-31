"""The towel rolls over the circular rim before hanging outside the basket wall."""
vs=[];fs=[];nx=70;ny=40
for side in (1,-1):
    for j in range(ny+1):
        y=-.135+.27*j/ny;edge=math.sqrt(.245**2-y*y)
        for i in range(nx+1):
            t=i/nx
            if t<.56:
                s=t/.56;x=-.08+(edge-.015+.08)*s;z=.330+.192*s**.40+.002*math.sin(s*13+y*22)*math.sin(s*math.pi)
            elif t<.80:
                a=(t-.56)/.24*math.pi/2;x=edge-.015+.040*math.sin(a);z=.522-.040*(1-math.cos(a))
            else:
                s=(t-.80)/.20;x=edge+.025+.012*s;z=.482-.14*s
            # Thickness follows the outer face; it never cuts through the rim.
            vs.append((x+side*.002,y,z+side*.002))
n=(nx+1)*(ny+1)
for layer in (0,1):
    for j in range(ny):
        for i in range(nx):
            a=layer*n+j*(nx+1)+i;f=(a,a+1,a+nx+2,a+nx+1);fs.append(f if layer==0 else tuple(reversed(f)))
edge=list(range(nx+1))+[j*(nx+1)+nx for j in range(1,ny+1)]+[ny*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(ny-1,0,-1)]
for a,b in zip(edge,edge[1:]+edge[:1]):fs.append((a,a+n,b+n,b))
uvs=[]
for face in fs:
    coords=[]
    for vi in face:
        base=vi%n;j=base//(nx+1);i=base%(nx+1)
        length=sum((Vector(vs[j*(nx+1)+q])-Vector(vs[j*(nx+1)+q-1])).length for q in range(1,i+1))
        coords.append((length,.27*j/ny))
    uvs.append(coords)
g.poly('LaundryBasket',vs,fs,'FogLinen',uv=uvs,smooth=True)
pipe('LaundryBasket',[vs[i] for i in edge]+[vs[edge[0]]],.0014,'CharcoalWeave',8)
