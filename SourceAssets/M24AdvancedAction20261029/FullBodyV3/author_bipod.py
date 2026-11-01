"""Replace only the M24 bipod mounting yoke. Keep both leg meshes and pivots."""
from pathlib import Path
O=Path(__file__).resolve().parent
helpers=(O.parent/'DetailV2/author.py').read_text(encoding='utf-8').split('# Keep the current lower perimeter')[0]
exec(compile(helpers,'M24 fitted bipod modelling helpers','exec'))
pin=cylinder('Existing transverse hinge',(0,.45,.022),.0032,.052,'X',steel,64,.0002)
for sign in (-1,1):
    yz=[(.441,.021),(.441,.048),(.428,.058),(.428,.063),(.472,.063),(.472,.058),(.459,.048),(.459,.021)]
    fork=prism_x('Bipod rising yoke',yz,sign*.0185,sign*.023,coat,.0007)
    slot(fork,(sign*.021,.45,.045),(.012,.008,.019),.0030)
    fastener(fork,sign,.45,.022,.023,.0030)
    # Captive clamp screws are sunk into the actual mounting face.
    for y in (.433,.467):fastener(fork,sign,y,.059,.023,.0017)
plate=box('Foreend contact saddle',(0,.45,.0631),(.046,.052,.0048),coat,.0006)
# Tapered saddle pad follows the retained underside contact width. It meets
# both the new 65.8 mm belly and original 65.995 mm foreend without an air gap.
pad=prism_y('Conforming contact pad',[(-.013,.0652),(.013,.0652),(.013,.0675),
                                   (.0065,.06695),(0,.0669),(-.0065,.06695),(-.013,.0675)],.429,.471,interior,.00018)
for y in (.431,.469):
    head=cylinder('Vertical mounting screw',(0,y,.0647),.0024,.0018,'Z',steel,40,.0002)
    cut(head,cylinder('Vertical hex recess',(0,y,.0656),.0013,.0015,'Z',steel,6,.00006))

# UV0 is the same four-centimetre tangential microfinish contract as the body.
tail='#'+(O.parent/'DetailV2/author.py').read_text(encoding='utf-8').split('# Apply only authored features.')[1]
tail=tail.replace('DetailV2','BipodSeatV3').replace('M24_AdvancedAction_DetailBody','M24_Bipod_SeatV3')
tail=tail.replace('SM_M24_m24_advanced_action.fbx','SM_M24_Bipod_Base.fbx')
tail=tail.replace("'authoring.json'","'bipod_authoring.json'")
exec(compile(tail,'M24 fitted bipod export','exec'))
