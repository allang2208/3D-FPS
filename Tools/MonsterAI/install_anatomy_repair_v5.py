"""Save offline M08/M09/M10 geometry repair and its rebound soft corpse."""
from pathlib import Path
import sys, importlib, json
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
sys.path.insert(0,str(P/'Tools/MonsterAI'))
import install_meshy_remesh_v3 as shared
importlib.reload(shared)
shared.ROOT=P/'SourceAssets/AlienGeometry20261006/AnatomyRepairV5'
shared.DEST='/Game/Monsters/AnatomyRepairV5'

def reuse_materials(species,author,report):
    result={}
    for name,entry in author['materials'].items():
        if species=='HangingBellM09':
            path='/Game/Monsters/HangingBellM09/V04/Materials/M_M09_Body'
        elif entry['new_texture']:
            family='M_M10_MeshySurface' if species=='M10Mawcrawler' else 'M_M08_Skin'
            path='/Game/Monsters/RemeshV3/'+species+'/Materials/'+family+'_RemeshV3'
        else:
            result[name]=shared.original_material(species,entry['source_material_name'])
            continue
        result[name]=shared.load(path)
    if species=='HangingBellM09':
        # In-place FBX reimport may retain the old named slots. The restored
        # geometry uses the original atlas, including those retained slots.
        prior=json.loads((P/'SourceAssets/AlienGeometry20261006/RemeshV3'/species/'authoring.json').read_text(encoding='utf8'))
        original=shared.load('/Game/Monsters/HangingBellM09/V04/Materials/M_M09_Body')
        for name in prior['materials']:result[name]=original
    return result

shared.materials=reuse_materials

def run(species,stage):
    if species not in ('HangingBellM09','M10Mawcrawler','LurkerM08'):
        raise RuntimeError('This repair only applies to M08, M09 and M10')
    shared.run(species,stage)

if __name__=='__main__':
    command=u.SystemLibrary.get_command_line()
    def arg(key):return command.split('-'+key+'=',1)[1].split()[0]
    run(arg('RemeshSpecies'),arg('RemeshStage'))
