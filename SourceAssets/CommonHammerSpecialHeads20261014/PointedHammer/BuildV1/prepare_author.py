"""Reuse the established head-interface loft with the approved pointed profile."""
from pathlib import Path
P = Path(__file__).resolve().parent
ROOT = P.parents[3]
source = (ROOT/'SourceAssets/CommonHammerHeads20261014/DesignBuildV2/author_design.py').read_text(encoding='utf-8-sig')
source = source.replace('ROOT=P.parents[2];sys.path.insert(0,str(P.parent))', 'ROOT=P.parents[3];sys.path.insert(0,str(P))')
start = source.index('# Shared, physically scaled steel maps')
end = source.index('\ndef clip', start)
source = source[:start]+'''# Reuse the actual shared hammer steel and its packed PBR maps.
with bpy.data.libraries.load(str(ROOT/'SourceAssets/CommonHammerHeads20261014/DesignBuildV2/CommonHammerHeads_DesignV2_Editable.blend'),link=False) as (src,dst):
    dst.materials=['M_CommonHammerHeadSteel']
mat=dst.materials[0]
'''+source[end:]
start = source.index('PROFILES={')
end = source.index('\nreceipts=[]', start)
source = source[:start]+'''PROFILES={
 'pointed_hammer':[
  (.078,None,0),(.084,(.0295,.0305),0),
  (.086,(.032,.033),0),(.091,(.032,.033),0),(.094,(.0295,.0305),0),
  (.099,(.034,.035),.25),(.106,(.045,.047),.8),(.111,(.048,.050),1),
  (.117,(.046,.048),1),(.143,(.034,.0355),1),(.171,(.021,.022),1),
  (.190,(.012,.0125),.9),(.196,(.009,.0095),.45),(.199,(.008,.0085),0),
  (.213,(.0007,.0007),0)]
}

# Eight broad crests with recessed longitudinal channels. Ray/polygon intersection
# preserves planar facets rather than making a wavy circular cone.
PROFILE_SECTOR=[(0,1.0),(3,1.0),(7,.95),(16,.79),(22.5,.77),(29,.79),(38,.95),(42,1.0),(45,1.0)]
def radius_shape(kind,theta,ry,rz,flange):
    a=theta%(math.pi/4)
    rays=[(math.radians(deg),Vector((r*math.cos(math.radians(deg)),r*math.sin(math.radians(deg))))) for deg,r in PROFILE_SECTOR]
    direction=Vector((math.cos(a),math.sin(a)))
    radius=1.
    for (aa,p),(bb,q) in zip(rays,rays[1:]):
        if aa-1e-8<=a<=bb+1e-8:
            edge=q-p
            cross=direction.x*edge.y-direction.y*edge.x
            radius=(p.x*edge.y-p.y*edge.x)/cross
            break
    # End cap is an eight-sided clean taper; flutes gently close before it.
    oct_radius=math.cos(math.pi/8)/math.cos(a-math.pi/8)
    r=oct_radius*(1-flange)+radius*flange
    return Vector((0,ry*math.cos(theta)*r,rz*math.sin(theta)*r))
'''+source[end:]
source = source.replace("name='SM_CommonHammerHeads_'+kind+'_DesignV2'", "name='SM_CommonHammerHeads_pointed_hammer_V1'")
source = source.replace("sign*PROFILES[kind][-1][0],center.y,center.z", "sign*(PROFILES[kind][-1][0]+.0007),center.y,center.z")
# Preserve smooth source/transition normals; use per-face normals along the new
# planar flutes and bevel strips so the V4 ridges remain crisp.
source = source.replace('face.normal if face in caps else loop.vert.normal', 'face.normal if face in caps or abs(loop.vert.co.x)>.104 else loop.vert.normal')
source = source.replace("CommonHammerHeads_DesignV2_Editable.blend'))", "PointedHammer_Editable.blend'))")
source = source.replace("'design_reference':'../DesignSheetV1/common-hammer-heads-design-v1.png','revision':'DesignV2'", "'design_reference':'../ConceptV4/faceted-double-spike-design.png','revision':'PointedHammerV1'")
source = source.replace("'location_cm':[0,0,92.5000011920929]", "'location_cm':[0,0,92.5000011920929],'materials':[m.name for m in data.materials]")
source = source.replace("print('COMMON_HAMMER_HEADS_AUTHORED'", "print('POINTED_HAMMER_AUTHORED'")
(P/'author_pointed_hammer.py').write_text(source,encoding='utf-8')
print('POINTED_HAMMER_AUTHOR_SAVED')
