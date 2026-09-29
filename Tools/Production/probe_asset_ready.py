"""桥就绪探针：输出 LOAD=M_CutUpperMotion 即代表 MCP+资产注册表可用。"""
import unreal as u
a = u.EditorAssetLibrary.load_asset('/Game/Items/HarvestTimber/M_CutUpperMotion')
print('LOAD=%s' % (a.get_name() if a else 'NONE'))
