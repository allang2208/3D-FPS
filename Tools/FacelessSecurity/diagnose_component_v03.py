import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V03/Diagnosis')
report={}
for name in ['FacelessSecurity','NurseZombie']:
    bp=u.load_asset('/Game/Monsters/'+name+'/BP_'+name);cdo=u.get_default_object(bp.generated_class());mc=cdo.get_editor_property('mesh');mesh=cdo.get_editor_property('visual_mesh')
    row={'component':mc.get_path_name(),'materials':[mc.get_material(i).get_path_name() if mc.get_material(i) else None for i in range(mc.get_num_materials())]}
    for p in ['override_materials','relative_location','relative_rotation','relative_scale3d','forced_lod_model','visibility_based_anim_tick_option','component_use_fixed_skel_bounds']:
        try:row[p]=str(mc.get_editor_property(p))
        except Exception as e:row[p]=str(e)
    report[name]=row
(ROOT/'component_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
