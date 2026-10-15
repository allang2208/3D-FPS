"""Freeze a design-sheet construction revision without replacing the first author source."""
from pathlib import Path
P=Path(__file__).resolve().parent;BASE=P.parent
source=(BASE/'author_heads.py').read_text(encoding='utf-8')
source=source.replace('ROOT=P.parents[1];sys.path.insert(0,str(P))','ROOT=P.parents[2];sys.path.insert(0,str(P.parent))')
a=source.index('PROFILES={');b=source.index('\nreceipts=[]',a)
source=source[:a]+'''# Successive solid cross-sections define shoulders, bevels, rims and recessed faces.
# None is the unchanged tangent continuation at the real factory neck boundary.
PROFILES={
 'heavy_forged':[
  (.078,None,0),(.088,(.037,.046),0),(.096,(.048,.057),0),
  (.104,(.055,.064),0),(.108,(.057,.066),0),(.112,(.057,.066),0),
  (.170,(.057,.066),0),(.174,(.056,.065),0),(.179,(.053,.062),0),
  (.182,(.050,.059),0),(.1825,(.047,.056),0),(.1815,(.0465,.0555),0),(.181,(.044,.053),0)],
 'flanged_breaker':[
  (.078,None,0),(.088,(.034,.038),0),(.096,(.042,.047),.25),
  (.104,(.055,.061),.80),(.110,(.059,.065),1),(.153,(.059,.065),1),
  (.158,(.058,.064),1),(.165,(.054,.060),1),(.170,(.050,.056),1),
  (.1706,(.046,.052),1),(.168,(.034,.038),0),(.1715,(.029,.029),0),(.172,(.0275,.0275),0)],
 'light_drum':[
  (.078,None,0),(.089,(.029,.029),0),(.094,(.035,.035),0),
  (.097,(.039,.039),0),(.100,(.0405,.0405),0),(.103,(.0405,.0405),0),
  (.106,(.0395,.0395),0),(.110,(.0345,.0345),0),(.116,(.030,.030),0),
  (.132,(.030,.030),0),(.138,(.0335,.0335),0),(.143,(.0385,.0385),0),
  (.147,(.0405,.0405),0),(.151,(.0405,.0405),0),(.154,(.0395,.0395),0),
  (.157,(.0375,.0375),0),(.158,(.0355,.0355),0),(.157,(.0335,.0335),0),
  (.151,(.0325,.0325),0),(.150,(.0315,.0315),0),(.150,(.027,.027),0)]
}
def radius_shape(kind,theta,ry,rz,flange):
    c=math.cos(theta);s=math.sin(theta)
    if kind=='heavy_forged':
        # A broad rectangular striking face with rounded corners.
        r=(abs(c)**8+abs(s)**8)**(-.125)
    elif kind=='flanged_breaker':
        # Eight broad, bevel-edged longitudinal ribs, with a circular central disk.
        phase=abs((theta+math.pi/8)%(math.pi/4)-math.pi/8)/(math.pi/8)
        if phase<.20:weight=1.
        elif phase<.28:weight=1.-(phase-.20)/.08*.25
        elif phase<.72:weight=.75*(1.-(phase-.28)/.44)
        else:weight=0.
        r=1.-flange*(.28*(1.-weight))
    else:r=1.
    return Vector((0,ry*c*r,rz*s*r))
''' + source[b:]
source=source.replace('for stage,(x,dims) in enumerate(PROFILES[kind]):','for stage,(x,dims,flange) in enumerate(PROFILES[kind]):')
source=source.replace('radius_shape(kind,angles[j],*dims)','radius_shape(kind,angles[j],*dims,flange)')
source=source.replace('n=len(ring);previous_ring=ring','n=len(ring);previous_ring=ring\n        unwrapped=np.unwrap(np.array(angles));direction=1. if unwrapped[-1]>unwrapped[0] else -1.')
old="blend=min(1.,max(0.,(abs(loop.vert.co.x)-cut)/.025));new_uv=Vector(((abs(loop.vert.co.x)-cut)/.12,(j+1 if index==k else j)/n))"
new="""blend=min(1.,max(0.,(abs(loop.vert.co.x)-cut)/.025))
                    angle=unwrapped[index]+(direction*math.tau if index==0 and j==n-1 else 0.)
                    new_uv=Vector(((abs(loop.vert.co.x)-cut)/.12,(angle-unwrapped[0])*.05/.12))"""
source=source.replace(old,new)
source=source.replace("name='SM_CommonHammerHeads_'+kind","name='SM_CommonHammerHeads_'+kind+'_DesignV2'")
source=source.replace('CommonHammerHeads_Editable.blend','CommonHammerHeads_DesignV2_Editable.blend')
source=source.replace("'tested':False","'design_reference':'../DesignSheetV1/common-hammer-heads-design-v1.png','revision':'DesignV2','tested':False")
# Keep the same shared steel resources. No texture or material look changes are deployed.
(P/'author_design.py').write_text(source,encoding='utf-8')
icons=(BASE/'author_icons.py').read_text(encoding='utf-8')
icons=icons.replace('ROOT=P.parents[1]','ROOT=P.parents[2]').replace('CommonHammerHeads_Editable.blend','CommonHammerHeads_DesignV2_Editable.blend')
icons=icons.replace('CommonHammerHeads_Icons_Editable.blend','CommonHammerHeads_DesignV2_Icons.blend')
# Save only to this revision during authoring; deployment runs after UE assets are saved.
icons=icons.replace("shutil.copy2(O/(row['id']+'.png'),dest/(key+'.png'))","pass  # deployment is owned by import_design.py")
(P/'author_icons.py').write_text(icons,encoding='utf-8')
print('Prepared DesignV2 modeling and icon authoring sources')
