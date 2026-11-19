from pathlib import Path
import sys,runpy,json,numpy as np
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here))
from r4_pose import BASE,OUT,pose_values
review=OUT/'Review'
forms=json.loads((review/'forms.json').read_text())
r3=BASE/'R3_ArmsRefined'
before=json.loads((r3/'AnatomyReview/derived_saved_mesh.json').read_text())
after=dict(before,positions=forms['base'])
for data in (before,after):data['head_z_cm']=4.5
def apply(data,bind,posed):
    p=np.asarray(data['positions']).copy()
    if data is before:return p,{}
    values=pose_values(data,bind,posed)
    for n,w in values.items():
        a=np.array(forms['targets'][n]);p[a[:,0].astype(int)]+=a[:,1:]*w
    return p,values
# Head also follows spine, neck, facial and shoulder weights through the sampled transformations.
samples=json.loads((review/'pose_samples.json').read_text())
runpy.run_path(str(here/'render_anatomy_review.py'),run_name='__main__',init_globals={
    'review_output':r3,'review_folder':review,'review_datasets':[before,after],
    'review_method':'Offline skinning of the saved R3 reference mesh and R4 authored vertex positions using the same joints and weights. R4 applies the four local-angle corrections before skinning.',
    'review_apply_forms':apply,'review_sample_poses':{k:v['cs'] for k,v in samples.items()},
    'review_width':1900,'review_height':650,'review_spacing':.80,
    'review_shots':[('01_high','shoulders_high',0,3.20,1.51),
        ('02_flex','elbows',-74,2.37,1.28),
        ('03_cast','Staff.FullBody.CastRelease',0,3.20,1.40),
        ('04_aim','Rifle.Idle',-24,2.96,1.47)]})
