"""Use shared part IDs and actual current rifle stats with an M24-fitted skin."""
import copy
IDS=('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip')
DESCRIPTIONS={
    'phantom_reargrip':'贴合枪托颈部的薄型包覆，表面带有分段横向防滑肋纹。',
    'stable_antislip_reargrip':'沿原枪托曲面贴合的橡胶握持覆层，表面带细密防滑颗粒。',
    'balanced_reargrip':'贴合原握持轮廓的聚合物覆层，带细横纹与收薄边缘。'}
def apply_catalog(data):
    row=next(w for w in data['weapons'] if w['id']=='ue_m24')
    donor=next(w for w in data['weapons'] if w['id']=='ue_m4a1')['options']['reargrip']
    options=[dict(id='false',name='M24 原装后握',description='枪托与握持颈部连成一体，保留原装聚合物表面。',stats={},effects=[])]
    for key in IDS:
        entry=copy.deepcopy(next(x for x in donor if x['id']==key));entry['description']=DESCRIPTIONS[key];options.append(entry)
    if 'reargrip' not in row['allowed']:row['allowed'].append('reargrip')
    row['default_parts']['reargrip']='false';row['options']['reargrip']=options
