"""Two painted faces on three real oak boards, suspended from the fascia of the centre pier."""
from forms import bar,ring,sweep,curve

def clip(poly,lo,keep_greater):
    out=[]
    for i,(qa,za) in enumerate(poly):
        qb,zb=poly[(i+1)%len(poly)]
        a=(qa>=lo)==keep_greater;b=(qb>=lo)==keep_greater
        if a:out.append((qa,za))
        if a!=b:out.append((lo,za+(zb-za)*(lo-qa)/(qb-qa)))
    return out

def boards(m,weathered=False):
    # q increases away from the post; Z is relative to the bracket arm.
    outline=[(20,-17),(20,-77),(26,-84),(31,-88),(41,-92.3),(49,-94.5),
             (55,-95.4),(61,-94.7),(70,-92.9),(79,-89.5),(85,-84.5),(90,-78),(90,-17)]
    if weathered:
        # Chips interrupt the exposed arrises but leave the painted crest intact.
        outline=[(20,-17.25),(20,-36),(20.38,-37.9),(20,-40.1),(20,-70.8),
                 (20.8,-72.6),(20.5,-77),(25.4,-83.2),(27.6,-83.9),(30.8,-87.6),
                 (39.3,-91.6),(40.4,-91.0),(42.6,-92.15),(49,-94.25),
                 (54.5,-95.3),(55.7,-94.7),(60.6,-94.6),(69.7,-92.6),
                 (78.7,-89.2),(82,-86.9),(83.1,-85.1),(85.1,-84.2),
                 (89.7,-78),(90,-62),(89.4,-59.3),(90,-57.3),(90,-17.3)]
    for num,(left,right) in enumerate([(20,42.7),(42.91,67.15),(67.4,90)]):
        poly=clip(clip(outline,left-.00001,True),right+.00001,False)
        cq=sum(q for q,z in poly)/len(poly);cz=sum(z for q,z in poly)/len(poly)
        layers=[];n=len(poly)
        for depth,bevel in ((-2.25,True),(-1.99,False),(1.99,False),(2.25,True)):
            face=[(cq+(q-cq)*(.985 if bevel else 1),cz+(z-cz)*(.995 if bevel else 1)) for q,z in poly]
            points=[(depth+((num-1)*.12+.12*((z+55)/40)**2) if weathered else depth,-q,z) for q,z in face]
            start=m.vertices(points);layers.append((start,face))
        for index in (0,3):
            start,face=layers[index];order=list(range(n)) if index==0 else list(reversed(range(n)))
            uv=[(((90-face[j][0])/70 if index==0 else (face[j][0]-20)/70),
                 (face[j][1]+95.4)/78.4) for j in order]
            if weathered:uv=[((u+(1 if index==3 else 0))*.5,v) for u,v in uv]
            m.face([start+j for j in order],uv,'Paint')
        for i in range(3):
            base,_=layers[i];outer,_=layers[i+1]
            for j,(q,z) in enumerate(poly):
                k=(j+1)%n; q2,z2=poly[k]
                length=((q2-q)**2+(z2-z)**2)**.5
                m.face([base+k,base+j,outer+j,outer+k],
                       [(i*.036,length/63+num*.19),(i*.036,num*.19),((i+1)*.036,num*.19),((i+1)*.036,length/63+num*.19)],
                       'Endgrain' if abs(q-q2)>2*abs(z-z2) else 'Oak')

def fixed(m):
    # All iron pieces meet the same post face; the arch takes the load back down into the plate.
    bar(m,(0,-.32,-37.5),(0,-.32,5.5),(3.9,.85),'Iron',flat=True)
    bar(m,(0,.35,0),(0,-94,0),(1.83,1.65),'Iron',flat=True)
    count=(10,7,5)[m.level]
    brace=curve((0,-1,-32),[((0,-5,-15),(0,-23,-3.6),(0,-42,-.6))],count)
    sweep(m,brace,(1.27,1.58),'Iron',(1,0,0),box=True)
    scroll=curve((0,-93,0),[((0,-98,-1.3),(0,-104,.6),(0,-104,5.1)),
                            ((0,-104,8.6),(0,-100.2,9.2),(0,-99.7,6.1))],count)
    sweep(m,scroll,[(1.81-1.42*i/(len(scroll)-1),1.65-1.27*i/(len(scroll)-1)) for i in range(len(scroll))],'Iron',box=True)
    for z in (3.6,-34.5,-15):
        bar(m,(0,-.6,z),(0,-2.05,z),(1.18,1.18),'Rubbed')
    for q in (32,77.6):
        ring(m,(0,-q,-.8),(3.15,0,0),(0,0,4.15),.69)

def chain(m):
    for q in (32,77.6):
        ring(m,(0,-q,-7.),(0,2.12,0),(0,0,4.18),.74,'Rubbed')

def board_straps(m):
    for q in (32,77.6):
        ring(m,(0,-q,-13.3),(2.6,0,0),(0,0,4.0),.73)
        # Bent saddle goes over the board top; each end is riveted to a painted face.
        saddle=curve((-2.64,-q,-22.9),[((-2.67,-q,-19),(-3.1,-q,-16.4),(-2.1,-q,-15.6)),
                    ((-.6,-q,-14.6),(1.3,-q,-14.8),(2.23,-q,-15.7)),
                    ((3.12,-q,-16.7),(2.64,-q,-19),(2.64,-q,-22.9))],(5,4,3)[m.level])
        sweep(m,saddle,(1.63,.32),'Iron',(0,1,0),box=True)
        for side in (-1,1):
            bar(m,(side*2.68,-q,-21.0),(side*3.48,-q,-21.0),(.89,.89),'Rubbed',(0,1,0))


def signboard(m):
    boards(m)
    fixed(m)
    chain(m)
    board_straps(m)
