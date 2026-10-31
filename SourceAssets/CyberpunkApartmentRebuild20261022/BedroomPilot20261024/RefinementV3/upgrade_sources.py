"""Apply the V3 source edits once to the retained V2 authoring baseline."""
from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'author.py';s=p.read_text('utf8')
s=s.replace('# Headwall is attached',"exec(compile((R/'precision.py').read_text('utf8'),str(R/'precision.py'),'exec'),globals())\n\n# Headwall is attached")
start=s.index('for i in range(7):',s.index("k='WallShelf'"));end=s.index('# Desk side accessories',start)
s=s[:start]+'''# Seven separately bound volumes, with varied dimensions and visible page blocks.
for i in range(7):
    x=-.57+i*.067;thickness=[.038,.046,.032,.043,.035,.048,.037][i]
    height=[.265,.242,.284,.258,.275,.247,.267][i]
    before=len(g.group(k)['v'])
    book(k,(0,0,0),.175,height,thickness,['CITY ATLAS','NIGHT SHIFT','FORM / 07','SOUND LAB','CIRCUITS','URBAN LIFE','FIELD NOTES'][i],['BookNavy','BookSage','BookOchre'][i%3])
    data=g.group(k)
    for q in range(before,len(data['v'])):
        xx,yy,zz=data['v'][q];data['v'][q]=(x+zz,-.040+xx,.5375+yy+height/2)
    # Spine identification fits within the physical width; no glowing lettering.
    text(k,f'{i+1:02}',(x+.007,-.131,.615),.012,'Paper',(90,0,0))
    for z in (.573,.710):B(k,(x+thickness/2,-.130,.5375+(z-.5375)*height/.265),(thickness-.012,.0006,.0012),'Copper')
plant(k,(.43,-.04,.018))
for x in (-.66,.66):
    for z in (0,.52):screw(k,(x,-.17,z+.018),(0,0,1),.0035)

''' + s[end:]
# Additional manufactured details stay inside existing support footprints.
s=s.replace("materials={};records=[]",'''# Accessory details use the same calibrated anchors as their parent assemblies.
for x in (-.065,.065):screw('Headphones',(x,.040,.0205),(0,0,1),.0027)
for side in (-1,1):
    for j in range(7):
        z=.128+j*.009
        roundbox('Headphones',(side*.1155,0,z),(.0015,.032,.0022),'Ink',.0006,4)
for x in (-.125,.125):
    for y in (-.100,.100):screw('BedsideTray',(x,y,.042),(0,0,1),.002)
for x in (-.65,.65):
    for y in (-.20,.20):screw('WindowBench',(x,y,.486),(0,0,1),.003)

materials={};records=[]''')
s=s.replace("# Per-group export and functional collision, no per-detail actors.",'''# Orient closed authored islands before freezing FBX normals. This catches
    # inverted shade walls instead of masking them with two-sided materials.
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
    # Per-group export and functional collision, no per-detail actors.''')
s=s.replace("'Headphones'}", "'Headphones','WallShelf','ReadingFixture','BedRefined'}")
p.write_text(s,encoding='utf8')
p=R/'bedding.py';s=p.read_text('utf8').replace("audit=R/'Audit/before'","audit=R.parent/'RefinementV2/Audit/before'")
s=s.replace("faces=[tuple(reversed(t)) for t,m in zip(native['triangles'],native['materials']) if m==slot]",'''faces=[tuple(reversed(t)) for t,m in zip(native['triangles'],native['materials']) if m==slot
           and not all(abs(verts[v][0])>.80 and verts[v][1]<1.125 and verts[v][2]>1.18 for v in t)]''')
s=s.replace('# Existing physical support',"bed_lamps('BedRefined')\n# Existing physical support")
# Rounded corner falloff removes the triangulated diagonal ridge of max(sx,sy).
s=s.replace('return .661-.21*max(sx,sy)**1.5+.004*math.sin(x*15+y*7)*(1-max(sx,sy))+.003*math.sin(y*23+x*4)*(1-max(sx,sy))', 'fall=1-(1-sx)*(1-sy)\n    return .661-.21*fall**1.5+.004*math.sin(x*15+y*7)*(1-fall)+.003*math.sin(y*23+x*4)*(1-fall)')
p.write_text(s,encoding='utf8')
p=R/'placements.py';s=p.read_text('utf8');s=s.replace("(R.parent/'installed.json')","(R.parent/'RefinementV2/installed.json')");s=s.replace("rows=[dict(r) for r in rows]","rows=[dict(r) for r in rows if r['actor']!='AP_Bed2_Bed']")
p.write_text(s,encoding='utf8')
print('V3_AUTHORING_SOURCE_READY')
