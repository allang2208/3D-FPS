"""Switch only the saved meteor impact and add its Cook directory."""
import json
from pathlib import Path
import install_meteor_combustion_v6 as common

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/MeteorImpactReferenceV7_20261114'
DEST='/Game/Skills/FireMagic20260921/MeteorImpactReferenceV7'
common.OUT=OUT


def main():
    receipt=json.loads((OUT/'asset-receipt.json').read_text(encoding='utf8'))
    if not receipt.get('complete'):
        raise RuntimeError('Save the complete impact revision before switching references')
    common.edit('Source/FPSGAME/Skills/MeteorAssets.h',[
        ('/Game/Skills/FireMagic20260921/MeteorCombustionV6/NS_MeteorCollisionV6.NS_MeteorCollisionV6',
         DEST+'/NS_MeteorPressureV7.NS_MeteorPressureV7')])
    previous='+DirectoriesToAlwaysCook=(Path="/Game/Skills/FireMagic20260921/MeteorCombustionV6")'
    common.edit('Config/DefaultGame.ini',[(previous,previous+'\n+DirectoriesToAlwaysCook=(Path="'+DEST+'")')])
    (OUT/'integration-receipt.json').write_text(json.dumps(dict(integrated=True,
        changed=['MeteorAssets.h Impact path','DefaultGame.ini Cook directory'],
        preserved=['V6 flight','V4 ground fire','rock and fragments','gameplay','smoke budget 16','sound','camera'],
        native_build_required=True,runtime_tested=False),indent=2),encoding='utf8')
    print('METEOR_V7_INTEGRATED',flush=True)


if __name__=='__main__':
    main()
