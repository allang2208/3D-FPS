"""Resolve newly imported resources in this rendering host using synchronous texture compilation."""
from pathlib import Path
import json
import unreal as u
R=Path(__file__).resolve().parent;BASE='/Game/SceneTests/FreightOppositePlatform20261113/Textures/'
def apply(w,req):
    u.SystemLibrary.execute_console_command(w,'Editor.AsyncTextureCompilation 0')
    result={}
    for path in sorted((R/'Textures').glob('*.png')):
        asset=u.load_asset(BASE+path.stem)
        if not asset:continue
        before=(asset.blueprint_get_size_x(),asset.blueprint_get_size_y())
        if min(before)<=32:
            # Rebuild the resource from its saved source; leave its original streaming limit in place.
            bias=asset.get_editor_property('lod_bias')
            asset.modify();asset.set_editor_property('lod_bias',bias+1);asset.set_editor_property('lod_bias',bias)
        result[path.stem]=[before,(asset.blueprint_get_size_x(),asset.blueprint_get_size_y())]
    return result
