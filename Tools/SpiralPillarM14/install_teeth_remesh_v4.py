"""Import M14's offline tooth repair into its existing live mesh and soft death."""
from pathlib import Path
import sys, importlib
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
sys.path.insert(0,str(P/'Tools/MonsterAI'))
import install_meshy_remesh_v3 as shared
importlib.reload(shared)
shared.ROOT=P/'SourceAssets/AlienGeometry20261006/RemeshV4Teeth'
shared.DEST='/Game/Monsters/RemeshV4Teeth'

def reuse_materials(species,author,report):
    result={}
    for name,entry in author['materials'].items():
        family=entry['source_material_name'].rsplit('_',1)[-1]
        if entry['new_texture']:
            path='/Game/Monsters/RemeshV3/SpiralPillarM14/Materials/M_M14_'+family+'_RemeshV3'
        else:path='/Game/Monsters/SpiralPillarM14/Materials/M_M14_'+family
        result[name]=shared.load(path)
    return result

shared.materials=reuse_materials

def run(species,stage):
    if species!='SpiralPillarM14':raise RuntimeError('This repair only applies to M14')
    shared.run(species,stage)

if __name__=='__main__':
    command=u.SystemLibrary.get_command_line()
    def arg(key):return command.split('-'+key+'=',1)[1].split()[0]
    run(arg('RemeshSpecies'),arg('RemeshStage'))
