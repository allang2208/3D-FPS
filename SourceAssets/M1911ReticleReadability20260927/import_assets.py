"""Import the two reticle revisions with the proven socket/material-preserving importer."""
import ast
from pathlib import Path
O=Path(__file__).parent
source=O.parent/'M1911AttachmentPolish20260927/import_assets.py'
tree=ast.parse(source.read_text(encoding='utf-8'))
for node in tree.body:
    if isinstance(node,ast.Assign):
        names={target.id for target in node.targets if isinstance(target,ast.Name)}
        if 'mag' in names:node.value=ast.Dict(keys=[],values=[])
        if 'entries' in names:node.value=ast.Name(id='optics',ctx=ast.Load())
        if 'ICON_ROOT' in names:node.value=ast.Constant('/Game/Weapons/M1911/CompactFit20260913/ReticleIcons20260927')
exec(compile(ast.fix_missing_locations(tree),str(source),'exec'),{'__file__':__file__,'__name__':'__main__'})
