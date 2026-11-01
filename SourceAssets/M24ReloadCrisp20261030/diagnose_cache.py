from pathlib import Path
TARGET=Path(__file__).resolve().parent
__file__=str(TARGET.parent/'M24GripOutfit20261030/setup.py')
exec(compile(Path(__file__).read_text(),'previous_saved_setup','exec'))
ue['profiles']=json.loads((O/'profiles_saved.json').read_text())
O=TARGET
tree=ast.parse((O/'setup.py').read_text())
for node in tree.body:
    if isinstance(node,ast.FunctionDef):exec(compile(ast.unparse(node),'reload_helper','exec'))
code=(O/'diagnose.py').read_text();code=code[code.index("folder=O/'Diagnosis'"):]
exec(compile(code,'cached_motion_comparison','exec'))
(O/'diagnosis_input_label.txt').write_text('Provisional analysis of the last saved GripOutfit profiles; refresh against current UE inputs before installation.')
