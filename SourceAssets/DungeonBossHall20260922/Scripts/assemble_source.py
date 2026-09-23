"""Save an editable source assembly using the existing confluence and corridor models."""
import json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/Dungeon_BossPumpHall.blend'))
contract=json.loads((ROOT/'Config/terminal-assembly.json').read_text(encoding='utf-8'))
existing=ROOT.parent/'DungeonRoutes20260922/Authored/Dungeon_DistinctRoomShells.blend'
with bpy.data.libraries.load(str(existing),link=False) as (src,dst):
    dst.objects=[name for name in src.objects if name.startswith(('SM_RS_Junction_','SM_RS_Transit_'))]
origins={a['source']:a['origin_m'] for a in contract['assembly'] if 'source' in a}
for obj in dst.objects:
    if obj is None:continue
    source='Junction' if obj.name.startswith('SM_RS_Junction_') else 'Transit'
    bpy.context.scene.collection.objects.link(obj)
    obj.location=origins[source];obj['reused_source']=str(existing);obj['terminal_module']='BossConfluence' if source=='Junction' else 'BossApproach'
    obj.name='TerminalReuse_'+obj.name
sys.path.insert(0,str(ROOT/'Scripts'))
from lookdev import bind
bind()
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/Dungeon_BossTerminal_Assembly.blend'))
print('BOSS_TERMINAL_SOURCE_ASSEMBLED',len(dst.objects),'existing connector objects reused')
