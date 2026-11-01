def solid_relief(name,i,outline,depth,thickness,mat):
 front=[facepoint(i,s,z,depth) for s,z in outline];back=[facepoint(i,s,z,depth+thickness) for s,z in outline];n=len(outline)
 return make(name,front+back,[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)],mat,.00007)
if KIND=='LeiXi':
 for i in range(0,8,2):
  zs=sorted(set([-.0618,-.0465,-.032]+[z for z,r in profile if -.0618<z<-.032]))
  normal=Vector((math.cos(i*math.pi/4),math.sin(i*math.pi/4),0))
  border=[facepoint(i,section(z)[4][0],z,-.00016) for z in zs]+[facepoint(i,-section(z)[4][0],z,-.00016) for z in list(reversed(zs))[1:-1]]
  ribbon('Flush thick silver diamond surround',border,normal,.00105,.00040,silver,True)
  inner=[p-normal*.00035 for p in border]
  ribbon('Dark bronze inset window lip',inner,normal,.00043,.00022,bronze,True)
else:
 for i in range(0,8,2):
  normal=Vector((math.cos(i*math.pi/4),math.sin(i*math.pi/4),0))
  border=[facepoint(i,s,z,-.00013) for s,z in [(-.84,-.065),(.84,-.065),(.84,-.040),(-.84,-.040)]]
  ribbon('Recess frame silver arris',border,normal,.00056,.00026,silver,True)
  for z in [-.0412,-.0484,-.0556]:
   shape=[(-.72,z),(0,z-.0040),(.72,z),(.48,z-.0030),(0,z-.0055),(-.48,z-.0030)]
   solid_relief('Triple bevelled folded thunder inlay',i,shape,.00026,.00066,silver)
   pts=[facepoint(i,s,zz,.00056) for s,zz in [(-.62,z-.0018),(0,z-.0059),(.62,z-.0018)]]
   ribbon('Contained blue white thunder cut',pts,normal,.00030,.00015,coremat)
  for side in [-1,1]:
   for z in [-.045,-.052,-.059]:
    pts=[facepoint(i,side*s,zz,-.00008) for s,zz in [(.92,z+.001),(.96,z),(.92,z-.001)]]
    ribbon('Small forged corner incisions',pts,normal,.00022,.00014,bronze)
for i in range(1,8,2):
 normal=(math.cos(i*math.pi/4),math.sin(i*math.pi/4),0)
 z0,z1=(-.0634,-.0298) if KIND=='LeiXi' else (-.065,-.040)
 for strand in range(2):
  pts=[]
  for t in sorted(set(list(np.linspace(0,1,81))+[(z-z0)/(z1-z0) for z,r in profile if z0<z<z1])):
   phase=t*math.pi*6+strand*math.pi;z=z0+t*(z1-z0)
   offset=.00036+.00014*math.cos(phase*2+strand*math.pi)
   pts.append(facepoint(i,.32*math.sin(phase),z,-offset))
  ribbon('Flat interwoven Nordic silver inlay',pts,normal,.00120,.00024,silver)
 # Border is a narrow inlay, and its root ends are embedded in the metal shoulder.
 for side in [-1,1]:
  pts=[facepoint(i,side*.58,z,-.00009) for z in sorted(set([z0,z1]+[z for z,r in profile if z0<z<z1]))]
  ribbon('Inset braid panel border',pts,normal,.00037,.00021,bronze)
 if KIND=='ZhenTing':
  for side in [-1,1]:
   pts=[facepoint(i,side*(.34-.2*t),-.066-t*.004,-.00017) for t in np.linspace(0,1,9)]
   ribbon('Lower bevel interlace return',pts,normal,.00058,.00022,silver)
seams=[-.0287,-.0641,-.0686,-.0734] if KIND=='LeiXi' else [-.0298,-.0342,-.0396,-.0657,-.0718,-.0743]
for z in seams:
 tube('Flush silver forged edge', [facepoint(i,-1,z,-.00004) for i in range(8)],.00020,silver,True,10)
# Bottom ornaments use proper cyclic topology, not duplicate first/last vertices and overlapping caps.
def flat_band(name,points,width,mat,closed=False):
 pts=[Vector(p) for p in points];vs=[];fs=[];normal=Vector((0,0,-1));n=len(pts)
 for j,p in enumerate(pts):
  tangent=(pts[(j+1)%n]-pts[(j-1)%n]) if closed else (pts[min(j+1,n-1)]-pts[max(0,j-1)])
  side=normal.cross(tangent.normalized())*width*.5
  vs.extend([p-side+normal*.00010,p+side+normal*.00010,p+side-normal*.00010,p-side-normal*.00010])
 for j in range(n if closed else n-1):
  for k in range(4):fs.append((j*4+k,j*4+(k+1)%4,((j+1)%n)*4+(k+1)%4,((j+1)%n)*4+k))
 if not closed:fs.extend([(3,2,1,0),tuple((n-1)*4+k for k in range(4))])
 return make(name,vs,fs,mat,.000045)
if KIND=='LeiXi':
 for r in [.0086,.0057]:
  pts=[(CX+r*math.cos(i*math.pi/2),CY+r*math.sin(i*math.pi/2),-.07517) for i in range(4)]
  flat_band('Terminal silver diamond seal',pts,.00072,silver,True)
 pts=[(CX,CY,-.07542),(CX+.0035,CY,-.07510),(CX,CY+.0047,-.07510),(CX-.0035,CY,-.07510),(CX,CY-.0047,-.07510),(CX,CY,-.0747)]
 make('Solid inset terminal storm seal',pts,[(0,2,1),(0,3,2),(0,4,3),(0,1,4),(5,1,2),(5,2,3),(5,3,4),(5,4,1)],coremat,uvs=[(.5,.5),(1,.5),(.5,1),(0,.5),(.5,0),(.5,.5)])
else:
 for r in [.0127,.0177]:ring(-.07513,r,silver,.00025)
 for strand in range(2):
  pts=[]
  for a in np.linspace(0,math.pi*2,240,endpoint=False):
   r=.0152+.00125*math.sin(a*12+strand*math.pi);z=-.07528-.00012*math.cos(a*24+strand*math.pi)
   pts.append((CX+r*math.cos(a),CY+r*math.sin(a),z))
  flat_band('Interwoven terminal silver seal border',pts,.00077,silver,True)
 for j in range(3):
  y=.0064-j*.0061;xy=[(-.0047,y+.002),(.0046,y+.0042),(-.0036,y-.0015),(.0040,y+.0003)]
  flat_band('Terminal triple thunder silver seal',[(CX+x,CY+y,-.07524) for x,y in xy],.00058,silver)
  flat_band('Terminal thunder engraving',[(CX+x,CY+y-.00057,-.07508) for x,y in xy],.00025,coremat)
for i in range(0,8,2):
 tube('Inset neck energy conductor',[facepoint(i,0,z,-.00005) for z in np.linspace(-.0273,-.0248,12)],.00013,coremat)
