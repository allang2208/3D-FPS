def box(name, center, size, material, bevel=.00055, group=None):
    c=Vector(center);h=Vector(size)*.5
    verts=[c+Vector((x*h.x,y*h.y,z*h.z)) for z in (-1,1) for y in (-1,1) for x in (-1,1)]
    return solid(name,verts,[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)],material,bevel,4,group)


def crown(name,cx,levels,material):
    verts=[]
    for z,rx,ry in levels:
        verts += [(cx+ox*rx,-.0007+oy*ry,z) for ox,oy in OCT]
    faces=[tuple(reversed(range(8)))]
    for k in range(len(levels)-1):
        faces += [(k*8+i,k*8+(i+1)%8,(k+1)*8+(i+1)%8,(k+1)*8+i) for i in range(8)]
    faces.append(tuple((len(levels)-1)*8+i for i in range(8)))
    return solid(name,verts,faces,material,.00065,5)


def arch(name,x0,x1,y,z0,z1,material,radius):
    mid=(x0+x1)*.5;span=(x1-x0)*.5
    points=[(x0,y,z0),(x0,y,z1-.017)]
    for i in range(1,13):
        u=i/12
        points.append((x0+span*u,y,z1-.017+.017*math.sin(u*PI/2)))
    for i in range(1,13):
        u=i/12
        points.append((mid+span*u,y,z1-.017+.017*math.cos(u*PI/2)))
    points += [(x1,y,z0)]
    return stroke(name,points,radius,material,10)


def build_head(side):
    label='L' if side<0 else 'R';cut=CUTS[side];cx=cut+side*.067
    original_collar(side)
    oct_loft(label+'_Solid_Load_Bearing_Neck',side,[(.007,.027,.034),(.015,.030,.035),(.025,.033,.040)],STEEL,.001)
    oct_loft(label+'_Neck_Silver_Weld_Seat',side,[(.009,.029,.035),(.012,.031,.037),(.015,.030,.036)],SILVER,.0006)
    # Every opening is an intentional structural aperture; no alpha or cards.
    crown(label+'_Flared_Bell_Base',cx,[(.831,.050,.042),(.837,.053,.045),(.845,.051,.043),(.854,.045,.037)],STEEL)
    crown(label+'_Base_Bronze_Binding',cx,[(.839,.053,.044),(.842,.053,.044)],BRASS)
    crown(label+'_Bell_Roof',cx,[(.970,.045,.037),(.978,.049,.041),(.983,.046,.039)],STEEL)
    crown(label+'_Crown_Binding',cx,[(.979,.049,.041),(.982,.049,.041)],SILVER)
    crown(label+'_Tapered_Resonance_Chimney',cx,[(.983,.037,.033),(.994,.027,.025),(1.005,.022,.021)],STEEL)
    crown(label+'_Chimney_Cap',cx,[(1.004,.027,.026),(1.010,.028,.026),(1.014,.023,.022)],SILVER)
    # Central rigid web and four corner posts distribute blows to both collars.
    box(label+'_Central_Load_Web',(cx,-.0007,.907),(.088,.008,.116),BLACK,.001)
    for side_y in (-1,1):
        y=-.0007+side_y*.036
        for i in range(4):
            x=cx+(-.042+i*.028)
            box(label+'_Rib_%s_%d'%(side_y,i),(x,y,.908),(.0055,.0075,.123),BRASS,.00055)
            box(label+'_Silver_Rib_Backing_%s_%d'%(side_y,i),(x,y-side_y*.002,.908),(.008,.006,.124),STEEL,.0007)
            for z in (.851,.973):
                f=frame((x,y+side_y*.004,z),(0,side_y,0),(1,0,0))
                strip(label+'_Rivet_Plate',f,[(-.004,-.004),(.004,-.004),(.004,.004),(-.004,.004)],-.0003,.0012,BRASS)
                bolt(label+'_Window_Rivet',f,.00135)
        for i in range(3):
            x=cx+(-.028+i*.028)
            arch(label+'_Vault_Arch_%d_%s'%(i,side_y),x-.0118,x+.0118,y,.851,.970,BRASS,.00165)
            arch(label+'_Inner_Vault_Lining',x-.0098,x+.0098,y-side_y*.0008,.855,.966,SILVER,.00045)
            # Six real columns per chamber: three front and three rear.
            yy=-.0007+side_y*.018
            f=frame((x,yy,.859),(0,0,1),(1,0,0))
            disk(label+'_Resonator_Pivot',f,.003,-.007,.109,SILVER,24)
            disk(label+'_Dark_Bronze_Tone_Column',f,.0075,.007,.093,BRASS,48)
            for offset,rr,height in ((.002,.0088,.005),(.012,.0086,.002),(.085,.0086,.003),(.093,.0095,.005)):
                disk(label+'_Column_Turned_Collar',f,rr,offset,offset+height,SILVER if offset in (.012,.085) else BRASS,48)
            # Thin luminous axial seal, held within a recessed bronze channel.
            front_y=yy+side_y*.0073
            stroke(label+'_Axial_Recess',[(x,front_y,.878),(x,front_y,.937)],.00065,BLACK,8)
            stroke(label+'_Axial_Resonance',[(x,front_y+side_y*.0003,.880),(x,front_y+side_y*.0003,.935)],.00023,FLUX,8,ENERGY)
            for j in range(9):
                z=.884+j*.0055
                for k,path in enumerate(GLYPHS[(i*3+j*5)%len(GLYPHS)]):
                    pts=[(x+a*.0038,front_y+side_y*.0004,z+b*.0034) for a,b in path]
                    stroke(label+'_Column_Inlaid_Glyph_%d_%d_%d'%(i,j,k),pts,.00012,FINE_BRASS,6,INLAYS)
    # One broad, solid, chamfered impact slab at each outside end.
    f=frame((cut+side*.118,-.0007,.916),(side,0,0),(0,1,0))
    outline=[(-.029,-.074),(.029,-.074),(.041,-.060),(.041,.059),(.027,.075),(-.027,.075),(-.041,.059),(-.041,-.060)]
    strip(label+'_Solid_Impact_Anvil',f,outline,-.010,.007,STEEL,.0017)
    for scale,depth,radius,material in ((.96,.0078,.00115,SILVER),(.86,.0081,.00043,BRASS)):
        loop=[pt(f,a*scale,b*scale,depth) for a,b in outline]
        stroke(label+'_Impact_Perimeter_Rim',loop+[loop[0]],radius,material,10)
    # A long narrow vertical sigil, rather than a circular crystal core.
    path=[(0,-.059),(-.0015,-.013),(-.007,0),(-.0015,.013),(0,.060),(.0015,.013),(.007,0),(.0015,-.013),(0,-.059)]
    stroke(label+'_Impact_Seal_Recess',[pt(f,a,b,.0080) for a,b in path],.0008,BLACK,8)
    stroke(label+'_Impact_Seal_Fine_Inlay',[pt(f,a,b,.00835) for a,b in path],.00024,FINE_BRASS,8,INLAYS)
    stroke(label+'_Impact_Seal_Energy',[pt(f,0,b,.0084) for b in (-.045,.045)],.00018,FLUX,8,ENERGY)
    for y in (-.027,.027):
        for z in (-.060,.060):
            bolt(label+'_Anvil_Fastener',frame(pt(f,y,z,.0085),f[3],f[1]),.0018)
    # Minute inlays and captive bolts give the roof and foot readable depth.
    for side_y in (-1,1):
        y=-.0007+side_y*.043
        for i in range(20):
            x=cx-.043+i*.0045
            for z in (.844,.979):
                ff=frame((x,y,z),(0,side_y,0),(1,0,0))
                for path in GLYPHS[(i*7)%len(GLYPHS)]:
                    stroke(label+'_Binding_Inlay',[pt(ff,a*.0028,b*.0032,.0002) for a,b in path],.00011,FINE_BRASS,6,INLAYS)
    announce(label+' open bell chamber complete')
