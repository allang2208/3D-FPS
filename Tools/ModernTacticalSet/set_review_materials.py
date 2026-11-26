"""Read cloth material and texture settings without saving packages."""
import json,hashlib
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/SetFitReview20261115';rows=[]
for name in ['CombatRipstop','CombatCarrier','CombatStretch','CombatCuff','CombatLining','CombatThread']:
    path='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3/Materials/M_'+name
    mat=u.load_asset(path);row=dict(name=name,path=path,shading_model=str(mat.get_editor_property('shading_model')),two_sided=mat.get_editor_property('two_sided'),uses_attributes=mat.get_editor_property('use_material_attributes'),textures={})
    for channel in ['BaseColor','NormalGL','ORM']:
        tex=u.MaterialEditingLibrary.get_material_default_texture_parameter_value(mat,channel)
        if not tex:raise RuntimeError('Missing bound texture '+name+' '+channel)
        source=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR3/Textures'/(name+'_'+channel+'.png')
        row['textures'][channel]=dict(path=tex.get_path_name(),srgb=tex.get_editor_property('srgb'),compression=str(tex.get_editor_property('compression_settings')),flip_green=tex.get_editor_property('flip_green_channel'),source_matches=u.EditorAssetLibrary.get_metadata_tag(tex,'CombatTextureSHA')==hashlib.sha256(source.read_bytes()).hexdigest())
    rows.append(row);print('CLOTH_MATERIAL_REVIEW',name,flush=True)
(R/'materials-review.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('CLOTH_MATERIAL_REVIEW_COMPLETE',flush=True)
