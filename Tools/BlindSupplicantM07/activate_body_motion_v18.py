"""Activate native defaults only after the real V18 package-save receipt."""
import json
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
OUT = PROJECT / 'SourceAssets/BlindSupplicantM07Meshy20261001/BodyMotionV18'
REPORT = OUT / 'ue_body_motion_delivery_v18.json'


def main():
    report = json.loads(REPORT.read_text(encoding='utf-8-sig'))
    if not report.get('saved') or report.get('mesh') != '/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18.SK_M07_BodyMotionV18':
        raise RuntimeError('Retain native V17 defaults until the V18 packages actually save.')
    source = PROJECT / 'Source/FPSGAME/Monsters/BlindSupplicantMonster.cpp'
    text = source.read_text(encoding='utf-8-sig')
    text = text.replace('/SK_M07_LegJointsV17.SK_M07_LegJointsV17', '/SK_M07_BodyMotionV18.SK_M07_BodyMotionV18')
    text = text.replace('/AnimationsLegJointsV17/', '/AnimationsBodyMotionV18/')
    text = text.replace('/AnimationsArmSweepV16/', '/AnimationsBodyMotionV18/')
    source.write_text(text, encoding='utf-8')
    report.update(native_defaults_updated=True, native_editor_and_game_built=False,
                  stage='Original mesh, contact proxy/cloth, four clips and AI/F6 saved; final native build pending')
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('M07 V18 saved assets activated in native defaults; final builds pending.', flush=True)


if __name__ == '__main__':
    main()
