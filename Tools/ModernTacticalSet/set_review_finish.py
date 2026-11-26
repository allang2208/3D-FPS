"""Resolve non-rendering author points and record the bounded review outcome."""
import json,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/SetFitReview20261115'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
review=read(R/'saved-review.json')
for row in review['rows']:
    if not any(c['max_vertex_distance_cm']>.01 for c in row['source_candidates']):continue
    cap=read(R/'Captured'/(row['key']+'.json'));d=cap.get('source_model',cap['lods'][0]);p=np.array(d['positions']);tree=cKDTree(p)
    for c in row['source_candidates']:
        a=read(c['file']);all_ap=np.array(a['positions']);ap=all_ap[np.unique(np.array(a['triangles'],int))];c['unused_author_vertices_excluded']=len(all_ap)-len(ap);c['max_vertex_distance_cm']=float(max(tree.query(ap,workers=2)[0].max(),cKDTree(ap).query(p,workers=2)[0].max()))
(R/'saved-review.json').write_text(json.dumps(review,indent=2),encoding='utf-8')
changed=[]
for row in read(R/'plan.json')['rows']:
    if hashlib.sha256(Path(row['disk']).read_bytes()).hexdigest()!=row['asset_sha256']:changed.append(row['key'])
if changed:raise RuntimeError('Packages changed during read-only review: '+str(changed))
fit=read(R/'fit-source.json');pairs=read(R/'pair-review.json');materials=read(R/'materials-review.json');neck=read(R/'neck-review.json')
summary=dict(completed=True,overall_qualified=False,review_kind='User-requested static model review, saved assets and offline geometry views',equipment_assets=72,body_references=2,render_lods=review['render_lods'],source_binding_read=True,render_binding_read=False,packages_modified=False,gameplay_tested=False,animation_tested=False,shader_visual_acceptance=False,configuration_changed=False,asset_hashes_unchanged=True,
    findings=[
        dict(id='shirt_pattern',severity='major',status='unresolved',finding='躯干采用裸身体表外扩约 3.2 mm 的构造，女款胸腹轮廓过紧；肩袖材质分界沿三角面呈锯齿，尚未达到概念图的成衣裁片与缝线质量。',evidence=['Views/Kaitlin_shirt_front.png','Views/Kaitlin_shirt_back.png','Views/Jason_shirt_back.png'],fix='按男女胸背包络重新裁制躯干与插肩袖片，设置成衣余量和连续缝线；保留腕口锚点。'),
        dict(id='hem_fit',severity='major',status='unresolved',finding='上衣内下摆在裤腰内局部进入原生身体表面；最近表面法线距离为男款约 -1.99 cm、女款约 -2.85 cm。该区域被裤腰遮挡，不能据此宣称游戏可见露肤。',evidence=['fit-source.json'],fix='按真实腰臀与裤腰内侧空间重做搭接，同时保持外表不鼓包。'),
        dict(id='male_shoulder_carrier',severity='major',status='unresolved',finding='男款上衣外层与防弹衣肩部存在 121 对相交三角形，涉及 35 个上衣三角面；女款对应外层相交计数为 0。相交对数不是独立可见缺陷数。',evidence=['pair-review.json'],fix='按穿上衣后的肩部表面重新拟合肩带和承托层。'),
        dict(id='glove_degeneracy',severity='minor',status='unresolved',finding='26 个手套版本检出少量面积低于 1e-10 cm² 的退化三角面；该数值检查不直接证明肉眼可见尖刺。',evidence=['saved-review.json'],fix='清理折叠或重复映射面，并保持手型、袖口和原生权重。'),
        dict(id='lower_finish',severity='art_quality',status='unresolved',finding='离线造型检查中，裤后膝拼片和裤腿褶皱过于规整，裤靴衔接具有覆盖，但小腿和靴筒外形仍显生硬。',evidence=['Views/Kaitlin_outfit_back.png','Views/Jason_outfit_front.png'],fix='重做受力区褶皱与后膝拼接，精修靴口厚度和鞋面转折。')],
    retained_results=dict(no_missing_material_interfaces=True,no_nonfinite_captured_positions=True,no_unweighted_source_vertices=True,native_head_neckline_intersections=neck,cuff_axial_overlap_cm={x['rig']:{k:v['axial_overlap_cm'] for k,v in x['cuffs'].items()} for x in pairs['rows']},cloth_materials=6,texture_sources_matching=all(t['source_matches'] for m in materials for t in m['textures'].values()),helmet_revision='HelmetHairFitR1 packages unchanged; native hair dynamics not re-tested'),
    limitations=['Reference pose only; no gameplay, animation, multiplayer or real-time cloth test.','Offline Blender images inspect geometry and approximate PBR; they are not UE lighting or shader visual acceptance.','Signed closest-surface measurements are diagnostic, not exact penetration depth or volume.','The saved mesh capture completed all 74 outputs; its second read host crashed during shutdown. No package was saved. Separate material read host exited successfully.','Other shirt/pants combinations and backpack combinations are not included in this current full-set review.'])
(R/'review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('SET_REVIEW_FINISHED',review['assets'],review['render_lods'],'qualified=False')
print('MAX_SOURCE_DISTANCE_CM',max(min(c['max_vertex_distance_cm'] for c in x['source_candidates']) for x in review['rows'] if x['source_candidates']))
