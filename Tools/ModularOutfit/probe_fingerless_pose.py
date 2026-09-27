from pathlib import Path
import json
P=Path('D:/FPS3D/FPSGAME');ns={}
exec((P/'Tools/ModularOutfit/check_fingerless_clearance.py').read_text().split('report=dict(')[0],ns)
R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';O=R/'ClearanceReview'
skin=json.loads((R/'SkinCoverage/PKM_review.json').read_text());glove=json.loads((R/'Authored/PKM.json').read_text())
s=ns['prepare'](skin,True);g=ns['prepare'](glove)
pose=json.loads((O/'PKM__angled_A_PKM_angled_idle_poses.json').read_text())['poses'][0]['bones']
sp=ns['deform'](s,pose);gp=ns['deform'](g,pose);result=ns['measure'](s,g,sp,gp);print('PROBE',result['max_plane_cross_mm'])
a,b=result['worst_pair']
for name,data,prepared,tri,points in [('skin',skin,s,a,sp),('glove',glove,g,b,gp)]:
    for v in prepared['t'][tri]:
        vi=prepared['original_ids'][v];print(name,'vertex',int(vi),'world',points[v].tolist(),'weights',data['weights'][vi])
print('GLOVE_UV',glove['uv1'][b])
