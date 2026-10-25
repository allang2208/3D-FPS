def window_surround(name,cx,side_y):
    """Closed 4.8 mm deep arched frame with an actual empty window and inner reveal."""
    outer=[(-.015,.850),(.015,.850),(.015,.951),(.012,.960),(0,.974),(-.012,.960),(-.015,.951)]
    inner=[(-.0102,.855),(.0102,.855),(.0102,.950),(.0075,.957),(0,.966),(-.0075,.957),(-.0102,.950)]
    verts=[]
    for depth,path in ((.034,outer),(.039,outer),(.039,inner),(.034,inner)):
        verts += [(cx+x,-.0007+side_y*depth,z) for x,z in path]
    faces=[];n=len(outer)
    for ring in range(4):
        for i in range(n):
            j=(i+1)%n
            faces.append((ring*n+i,ring*n+j,((ring+1)%4)*n+j,((ring+1)%4)*n+i))
    solid(name,verts,faces,STEEL,.00048,4)
    # The gold arris is sunk into the solid surround, never suspended over the aperture.
    outline=[(cx+x,-.0007+side_y*.03905,z) for x,z in inner]
    stroke(name+'_Inset_Bronze_Arris',outline+[outline[0]],.00055,BRASS,8)


def build_head(side):
    label='L' if side<0 else 'R';cut=CUTS[side];cx=cut+side*.067
    original_collar(side)
    oct_loft(label+'_Solid_Load_Bearing_Neck',side,[(.007,.027,.034),(.015,.030,.035),(.025,.033,.040)],STEEL,.001)
    oct_loft(label+'_Neck_Silver_Weld_Seat',side,[(.009,.029,.035),(.012,.031,.037),(.015,.030,.036)],SILVER,.0006)
    crown(label+'_Flared_Bell_Base',cx,[(.831,.050,.042),(.837,.053,.045),(.845,.051,.043),(.854,.045,.037)],STEEL)
    crown(label+'_Base_Bronze_Binding',cx,[(.839,.053,.044),(.842,.053,.044)],BRASS)
    crown(label+'_Bell_Roof',cx,[(.970,.045,.037),(.978,.049,.041),(.983,.046,.039)],STEEL)
    crown(label+'_Crown_Binding',cx,[(.979,.049,.041),(.982,.049,.041)],SILVER)
    crown(label+'_Tapered_Resonance_Chimney',cx,[(.983,.037,.033),(.994,.027,.025),(1.005,.022,.021)],STEEL)
    crown(label+'_Chimney_Cap',cx,[(1.004,.027,.026),(1.010,.028,.026),(1.014,.023,.022)],SILVER)
    box(label+'_Central_Load_Web',(cx,-.0007,.907),(.088,.008,.116),BLACK,.001)
    for sy in (-1,1):
        y=-.0007+sy*.036
        for i in range(4):
            x=cx-.042+i*.028
            box(label+'_Solid_Vault_Post_%s_%d'%(sy,i),(x,y,.910),(.006,.009,.120),BRASS,.0006)
            # Embedded bolts and square seats are kept inside the top/base rails.
            for z in (.855,.970):
                f=frame((x,-.0007+sy*.0392,z),(0,sy,0),(1,0,0))
                strip(label+'_Captive_Rivet_Seat',f,[(-.003,-.003),(.003,-.003),(.003,.003),(-.003,.003)],-.0007,.0006,BRASS,.00025)
                bolt(label+'_Window_Rivet',f,.00115)
        for i in range(3):
            x=cx-.028+i*.028
            window_surround(label+'_Solid_Arched_Window_%s_%d'%(sy,i),x,sy)
            yy=-.0007+sy*.018
            f=frame((x,yy,.859),(0,0,1),(1,0,0))
            disk(label+'_Resonator_Pivot',f,.003,-.007,.109,SILVER,24)
            disk(label+'_Bronze_Tone_Column',f,.0075,.007,.093,BRASS,48)
            for offset,rr,height in ((.002,.0088,.005),(.012,.0086,.002),(.085,.0086,.003),(.093,.0095,.005)):
                disk(label+'_Column_Turned_Collar',f,rr,offset,offset+height,BRASS,48)
            fy=yy+sy*.00735
            stroke(label+'_Axial_Seal_Recess',[(x,fy,.879),(x,fy,.936)],.00065,BLACK,8)
            stroke(label+'_Axial_Seal_Energy',[(x,fy+sy*.00015,.880),(x,fy+sy*.00015,.935)],.00028,FLUX,8,ENERGY)
            # Glyphs conform to the cylindrical tone column, with a partially embedded cross section.
            for j in range(7):
                z=.886+j*.0065
                for k,path in enumerate(GLYPHS[(i*3+j*5)%len(GLYPHS)]):
                    points=[]
                    for a,b in path:
                        xx=a*.0038
                        surface=math.sqrt(.0075**2-xx**2)
                        points.append((x+xx,yy+sy*(surface+.000035),z+b*.0034))
                    stroke(label+'_Fitted_Column_Inlay',points,.00016,FINE_BRASS,6,INLAYS)
        # No constant-Y lettering on the octagonal corners. Both rows fit the flat rail faces.
        for z,depth,halfwidth in ((.8405,.044,.028),(.9805,.041,.027)):
            for i in range(13):
                x=cx-halfwidth+2*halfwidth*i/12
                ff=frame((x,-.0007+sy*depth,z),(0,sy,0),(1,0,0))
                for path in GLYPHS[(i*7)%len(GLYPHS)]:
                    stroke(label+'_Embedded_Rail_Engraving',[pt(ff,a*.0023,b*.0017,.000025) for a,b in path],.00013,FINE_BRASS,6,INLAYS)
        # Solid taper-mounted trim follows the actual octagonal chimney profile.
        def roofpoint(x,z,offset=0):
            if z<=.994:ry=.033+(.025-.033)*(z-.983)/.011
            else:ry=.025+(.021-.025)*(z-.994)/.011
            return (cx+x,-.0007+sy*(ry+offset),z)
        border=[(-.019,.984),(.019,.984),(.012,.998),(.010,1.003),(-.010,1.003),(-.012,.998)]
        path=[roofpoint(x,z,.0001) for x,z in border]
        stroke(label+'_Fitted_Roof_Binding',path+[path[0]],.00065,BRASS,8)
        emblem=[(0,.986),(-.004,.992),(0,1.001),(.004,.992),(0,.986)]
        stroke(label+'_Roof_Lozenge', [roofpoint(x,z,.00012) for x,z in emblem],.00046,FINE_BRASS,8,INLAYS)
    # Broad 17 mm impact slab, with its ornament embedded in the face.
    f=frame((cut+side*.118,-.0007,.916),(side,0,0),(0,1,0))
    outline=[(-.029,-.074),(.029,-.074),(.041,-.060),(.041,.059),(.027,.075),(-.027,.075),(-.041,.059),(-.041,-.060)]
    strip(label+'_Solid_Impact_Anvil',f,outline,-.010,.007,STEEL,.0017)
    for scale,depth,radius,mat in ((.93,.0068,.0011,SILVER),(.84,.0070,.00045,BRASS)):
        points=[pt(f,a*scale,b*scale,depth) for a,b in outline]
        stroke(label+'_Embedded_Impact_Rim',points+[points[0]],radius,mat,10)
    sigil=[(0,-.055),(-.0017,-.012),(-.006,0),(-.0017,.012),(0,.055),(.0017,.012),(.006,0),(.0017,-.012),(0,-.055)]
    stroke(label+'_Impact_Seal_Recess',[pt(f,a,b,.0068) for a,b in sigil],.00075,BLACK,8)
    stroke(label+'_Impact_Seal_Inlay',[pt(f,a,b,.00710) for a,b in sigil],.00035,FINE_BRASS,8,INLAYS)
    stroke(label+'_Impact_Seal_Energy',[pt(f,0,b,.00710) for b in (-.042,.042)],.00025,FLUX,8,ENERGY)
    for y in (-.025,.025):
        for z in (-.056,.056):
            bolt(label+'_Anvil_Captive_Fastener',frame(pt(f,y,z,.0067),f[3],f[1]),.0015)
    announce(label+' V2 solid windows and surface-fitted details complete')
