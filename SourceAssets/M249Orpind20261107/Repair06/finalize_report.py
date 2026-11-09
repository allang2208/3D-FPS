from pathlib import Path
import json
r=Path(__file__).resolve().parent
def read(path):return json.loads((r/path).read_text(encoding='utf-8-sig'))
ads=read('after_idle_ads/review.json')['views'][0]
contacts={}
for view in ('after_reload_left','after_reload_empty_left'):
    contacts[view]=read(view+'/native_contacts.json')
result={
    'saved_assets':list(read('saved.json'))+['/Game/Weapons/M249/Animations/A_M249_reload','/Game/Weapons/M249/Animations/A_M249_reload_empty'],
    'changes':['Bind materials and gameplay slot names to incoming FBX identities','Move initial left-hand reach 4.2 cm outboard with smooth entry/exit; solve elbow and wrist','Increase physical reticle radius from 0.025 to 0.055 cm to retain pixel coverage at 720p'],
    'ads_projection':{k:ads[k] for k in ('reticle_pixel_x','reticle_pixel_y','corrective_count')},
    'render_size':[1280,720],
    'native_animation_base_surface_contacts':read('after/contact_sweep.json'),
    'native_corrective_surface_sample_contacts':contacts,
    'aperture_geometry':read('aperture_geometry.json'),
    'reach_joint_steps':read('reach_joint_steps.json'),
    'reticle_visibility':read('reticle_visibility.json'),
    'reticle_import':read('reticle_saved.json'),
    'build_boundary':'Initial Editor and Game build succeeded. Current complete rebuild blocked by unrelated LightningHaste GetLeaderPoseComponent errors. Native preview used the available Editor module, including the checker-backdrop review code.',
    'render_views':['after_idle_ads','after_reload_left','after_reload_empty_left'],
    'gameplay_test':False,
    'boundary':'Saved native assets, offline full-clip base-surface sweep, native V9 corrective render samples; no PIE/input test.'
}
(r/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8')
print('M249_REPAIR06_REPORT_SAVED')
