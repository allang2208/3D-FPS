"""Persist the M14 extended-bite reach and matching AI engagement distances."""
from pathlib import Path
import json, traceback
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004')
OUT=ROOT/'ProductionV04'
(OUT/'Records').mkdir(parents=True,exist_ok=True)
REPORT=OUT/'Records/ue_revision.json'
report={'complete':False,'saved':[],'tested':False,'rendered':False,'native_code_changed':False}

def record():REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main():
    bp=u.load_asset('/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14')
    cdo=u.get_default_object(bp.generated_class())
    before={name:float(cdo.get_editor_property(name)) for name in
        ('bite_trigger_range','mouth_reach','bite_contact_seconds','bite_cooldown','walk_speed')}
    bite=cdo.get_editor_property('bite_clip')
    report.update(before=before,bite_animation=bite.get_path_name(),
        death_animation=cdo.get_editor_property('death_clip').get_path_name())
    if bite.get_path_name()!='/Game/Monsters/SpiralPillarM14/Animations/A_M14_Bite_v03.A_M14_Bite_v03':
        raise RuntimeError('Expected the V03 extended bite before applying its range settings')
    # Trigger range is measured from the actor; hit reach is measured from the animated mouth.
    # 185 + 15 (new mouth excursion) + 35 (70 -> 105 reach) = 235 cm.
    # The existing combat adapter derives stop range as trigger - 15 cm.
    cdo.set_editor_property('mouth_reach',105.)
    cdo.set_editor_property('bite_trigger_range',235.)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    if not u.EditorAssetLibrary.save_loaded_asset(bp,False):raise RuntimeError('Could not save M14 range settings')
    report.update(complete=True,saved=[bp.get_path_name()],mouth_reach_cm=105.,
        bite_trigger_range_cm=235.,derived_stop_range_cm=220.,mouth_reach_multiplier=1.5,
        source_trigger_range_cm=185.,source_mouth_reach_cm=70.,
        animated_mouth_extension_increment_cm=15.,trigger_delta_cm=50.,
        ice_wall_reach_cm=235.,facing_activation_distance_cm=270.,
        hit_anchor='mouth_socket',user_testing_pending=True)
    record();print('M14_V04_BITE_RANGE_SAVED')

try:main()
except Exception:
    report['error']=traceback.format_exc();record();raise
