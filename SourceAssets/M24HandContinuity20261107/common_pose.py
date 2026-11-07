"""Read the saved V9 motion and the two current model surfaces in bind space."""
from pathlib import Path
WORK = Path(__file__).resolve().parent
PREVIOUS = WORK.parent / 'M24StockQuickMelee20261106'
__file__ = str(PREVIOUS / 'clearance.py')
exec(compile((PREVIOUS / 'clearance.py').read_text().split("if __name__=='__main__':")[0], 'V9 surface and pose helpers', 'exec'))
D['profiles'] = json.load(gzip.open(PREVIOUS / 'saved_motion.json.gz', 'rt'))
thumb = [f'thumb_{i:02}_r' for i in (1, 2, 3)]
owned = ['clavicle_r', *[n for n in names if under(n, 'upperarm_r')], 'ik_hand_r']
transport_source = ast.parse((S / 'M24QuickMeleeRightHandR3_20261104/release_arc.py').read_text())
transport = next(node for node in transport_source.body if isinstance(node, ast.FunctionDef) and node.name == 'move_hand')
exec(compile(ast.unparse(transport), 'native arm transport', 'exec'))
