# Integral octagonal forging, with recessed rectangular relief panels on four faces.
levels=sorted(set([z for z,r in profile if z<=-.0262]+[-.065,-.040]))
verts=[];faces=[]
def quad(points):
 idx=len(verts);verts.extend(points);faces.append(tuple(range(idx,idx+4)))
for i in range(8):
 for za,zb in zip(levels[:-1],levels[1:]):
  if i%2==0 and za>=-.065 and zb<=-.040:
   for lo,hi in [(-1,-.84),(.84,1)]:
    quad([facepoint(i,lo,za),facepoint(i,hi,za),facepoint(i,hi,zb),facepoint(i,lo,zb)])
  else:quad([facepoint(i,-1,za),facepoint(i,1,za),facepoint(i,1,zb),facepoint(i,-1,zb)])
shell=make('Integral three-step octagonal forging',verts,faces,steel,.00016)
def relief(name,i,outline,depth,thickness,mat,bevel=.00009):
 front=[facepoint(i,s,z,depth) for s,z in outline];back=[facepoint(i,s,z,depth+thickness) for s,z in outline];n=len(outline)
 return make(name,front+back,[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)],mat,bevel)
for i in range(0,8,2):
 normal=Vector((math.cos(i*math.pi/4),math.sin(i*math.pi/4),0))
 border=[facepoint(i,s,z) for s,z in [(-.84,-.065),(.84,-.065),(.84,-.040),(-.84,-.040)]]
 inner=[p-normal*.00080 for p in border]
 make('Recessed relief panel and bevelled reveal',border+inner,[(j,(j+1)%4,(j+1)%4+4,j+4) for j in range(4)]+[(4,5,6,7)],steel,.00014)
 ribbon('Flush silver panel bezel',[p+normal*.00012 for p in border],normal,.00055,.00022,silver,True)
 for row,z in enumerate([-.0412,-.0484,-.0556]):
  # Thick-tipped double sloped silver inlay, with a genuine recessed electric cut below it.
  shape=[(-.72,z),(0,z-.0040),(.72,z),(.48,z-.0030),(0,z-.0055),(-.48,z-.0030)]
  relief('Triple folded thunder silver inlay',i,shape,.00030,.00060,silver)
  path=[facepoint(i,s,zz,.00056) for s,zz in [(-.62,z-.0018),(0,z-.0059),(.62,z-.0018)]]
  ribbon('Blue white energy cut below chevron',path,normal,.00031,.00016,coremat)
  # Tiny recessed peening at the crease gives the inset a forged joint.
  p=facepoint(i,0,z-.00465,.00015)
  tube('Silver centre crease',[p+Vector((0,0,-.00022)),p+Vector((0,0,.00022))],.00016,bronze)
 # Fine inscribed brackets fill the panel corners without bars or loose fittings.
 for side in [-1,1]:
  for z in [-.044,-.051,-.058]:
   pts=[facepoint(i,side*s,zz,-.00006) for s,zz in [(.91,z+.001),(.94,z),(.91,z-.001)]]
   tube('Forged panel edge marks',pts,.00011,bronze)
# Interwoven flat silver straps fit the four intervening facets, rooted into both rims.
for i in range(1,8,2):
 normal=(math.cos(i*math.pi/4),math.sin(i*math.pi/4),0)
 for strand in range(2):
  coords=[]
  for t in np.linspace(0,1,65):
   z=-.0650+t*.0250;phase=t*math.pi*5+strand*math.pi
   coords.append(facepoint(i,.34*math.sin(phase),z,-.00046-.00018*math.cos(phase*2+strand*math.pi)))
  ribbon('Interlaced flat Nordic silver strap',coords,normal,.00105,.00020,silver)
 for side in [-1,1]:
  coords=[facepoint(i,side*.59,z,-.00013) for z in [-.065,-.040]]
  ribbon('Narrow inset braid border',coords,normal,.00038,.00020,bronze)
 # Engraved lower bevel flourishes continue the braid into the terminal rim.
 for side in [-1,1]:
  coords=[facepoint(i,side*(.34-.2*t),-.066-t*.004,-.00022) for t in np.linspace(0,1,9)]
  ribbon('Lower shoulder knot continuation',coords,normal,.00064,.00020,silver)
# Three forged shoulder lips are integral geometry, with thin silver arrises.
for z in [-.0298,-.0342,-.0396,-.0657,-.0718,-.0743]:
 points=[facepoint(i,-1,z,-.00004) for i in range(8)]
 tube('Fine silver forged arris',points,.00022,silver,True,8)
for i in range(8):
 coords=[facepoint(i,0,z,-.00014) for z in sorted(set([-.039,-.0275]+[z for z,r in profile if -.039<z<-.0275]))]
 ribbon('Inset stepped shoulder conductor',coords,(math.cos(i*math.pi/4),math.sin(i*math.pi/4),0),.00054,.00018,bronze)
# Broad solid terminal cap, with circular flat braided inlay and a triple zigzag seal.
bottom=[(CX+radius(-.075)*math.cos((i-.5)*math.pi/4),CY+radius(-.075)*math.sin((i-.5)*math.pi/4),-.075) for i in range(8)]
make('Solid broad terminal cap',bottom,[tuple(reversed(range(8)))],steel,.00020)
def terminal_ribbon(name,points,width,mat):
 pts=[Vector(p) for p in points];vs=[];fs=[];normal=Vector((0,0,-1))
 for j,p in enumerate(pts):
  tangent=(pts[min(j+1,len(pts)-1)]-pts[max(0,j-1)]).normalized();side=normal.cross(tangent)*width*.5
  vs.extend([p-side+normal*.00010,p+side+normal*.00010,p+side-normal*.00010,p-side-normal*.00010])
 for j in range(len(pts)-1):
  for k in range(4):fs.append((j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k))
 fs.extend([(3,2,1,0),tuple((len(pts)-1)*4+k for k in range(4))]);return make(name,vs,fs,mat,.00004)
for r in [.0127,.0177]:ring(-.07510,r,silver,.00025)
for strand in range(2):
 pts=[]
 for a in np.linspace(0,2*math.pi,193):
  r=.0152+.00125*math.sin(a*12+strand*math.pi);z=-.07527-.00012*math.cos(a*24+strand*math.pi)
  pts.append((CX+r*math.cos(a),CY+r*math.sin(a),z))
 terminal_ribbon('Braided silver terminal seal border',pts,.00078,silver)
for j in range(3):
 y=.0064-j*.0061
 xy=[(-.0047,y+.002),(.0046,y+.0042),(-.0036,y-.0015),(.0040,y+.0003)]
 terminal_ribbon('Triple terminal lightning seal',[(CX+x,CY+y,-.07524) for x,y in xy],.00058,silver)
 terminal_ribbon('Terminal seal electric engraving',[(CX+x,CY+y-.00057,-.07508) for x,y in xy],.00025,coremat)
# Recessed neck conductors meet the intact factory collar.
for i in range(0,8,2):tube('Throat energy trace',[facepoint(i,0,z,-.00005) for z in np.linspace(-.0273,-.0245,15)],.00014,coremat)
