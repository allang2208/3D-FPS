"""Use the existing production icon pipeline for the two updated optic meshes."""
import ast
from pathlib import Path
O=Path(__file__).parent
source=O.parent/'M1911AttachmentPolish20260927/author_icons.py'
tree=ast.parse(source.read_text(encoding='utf-8'))
entries=[('optic_'+key,'M1911_'+key+'_ReadableReticle_Editable.blend','SM_M1911_'+key+'_ReadableReticle20260927',False)
         for key in ['holographic','panoramic_red_dot']]
for node in tree.body:
    if isinstance(node,ast.Assign):
        names={target.id for target in node.targets if isinstance(target,ast.Name)}
        if 'mag' in names:node.value=ast.Dict(keys=[],values=[])
        if 'entries' in names:node.value=ast.parse(repr(entries),mode='eval').body
exec(compile(ast.fix_missing_locations(tree),str(source),'exec'),{'__file__':__file__,'__name__':'__main__'})
