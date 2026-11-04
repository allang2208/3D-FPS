"""Synchronize literal copy and the serialization boundary of existing authors.

This edits Python source only; it does not run asset producers or imports.
"""
import ast
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PAIRS = json.loads((HERE/'literal-copy-replacements.json').read_text(encoding='utf-8'))
HEADER = '''# Apply the shared workbench copy standard when publishing catalogs.
from pathlib import Path as _WorkbenchCopyPath
import runpy as _workbench_copy_runpy
_workbench_copy_root = next(p for p in _WorkbenchCopyPath(__file__).resolve().parents if (p / 'FPSGAME.uproject').exists())
_apply_workbench_copy = _workbench_copy_runpy.run_path(str(_workbench_copy_root / 'SourceAssets/WorkbenchCopy20261101/copy_rules.py'))['apply_for_target']
'''


def sync(path):
    raw = path.read_bytes()
    original = raw.decode('utf-8-sig')
    text = original
    for old, new in sorted(PAIRS.items(), key=lambda p: -len(p[0])):
        text = text.replace(old, new)
    if path.parts[-2:] == ('RuneSwordFrostMaterial20261101','install_catalog.py'):
        text = text.replace("'tier':'exclusive'", "'tier':'legendary'")
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:offsets.append(offsets[-1]+len(line))
    def position(node, end=False):
        line = node.end_lineno if end else node.lineno
        col = node.end_col_offset if end else node.col_offset
        # AST columns are UTF-8 byte offsets, not Unicode character offsets.
        return offsets[line-1] + len(lines[line-1].encode('utf-8')[:col].decode('utf-8'))
    def source(node):return text[position(node):position(node,True)]
    edits = []
    helper_ranges = []
    for node in ast.walk(tree):
        if not isinstance(node,ast.FunctionDef) or len(node.args.args)<2:continue
        if node.name not in ('write','save_json','write_json','save'):continue
        target, value = [arg.arg for arg in node.args.args[:2]]
        dumps = [x for x in ast.walk(node) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
                 and x.func.attr=='dumps' and x.args and isinstance(x.args[0],ast.Name) and x.args[0].id==value]
        if not dumps:continue
        if '_apply_workbench_copy' in source(node):continue
        first = node.body[0]
        if isinstance(first,ast.Expr) and isinstance(first.value,ast.Constant) and isinstance(first.value.value,str):
            first = node.body[1]
        at = offsets[first.lineno-1]
        indent = lines[first.lineno-1][:len(lines[first.lineno-1])-len(lines[first.lineno-1].lstrip())]
        edits.append((at,at,f'{indent}{value} = _apply_workbench_copy({target}, {value})\n'))
        helper_ranges.append((node.lineno,node.end_lineno))
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute) or node.func.attr!='write_text':continue
        if any(a<=node.lineno<=b for a,b in helper_ranges):continue
        for dump in ast.walk(node):
            if not isinstance(dump,ast.Call) or not isinstance(dump.func,ast.Attribute) or dump.func.attr!='dumps' or not dump.args:continue
            value=dump.args[0]
            if '_apply_workbench_copy' in source(value):continue
            edits.append((position(value),position(value,True),f'_apply_workbench_copy({source(node.func.value)}, {source(value)})'))
    if edits and '_apply_workbench_copy =' not in text:
        index=0
        for node in tree.body:
            if (isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str)) or (isinstance(node,ast.ImportFrom) and node.module=='__future__'):
                index=offsets[node.end_lineno]
            else:break
        # Keep an existing encoding header above inserted imports.
        while index<len(text) and text[index:index+1]=='#':
            index=text.find('\n',index)+1
        edits.append((index,index,HEADER+'\n'))
    for start,end,replacement in sorted(edits,reverse=True):text=text[:start]+replacement+text[end:]
    if text==original:return None
    ast.parse(text)
    backup=HERE/'before-authors'/path.relative_to(ROOT)
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(raw)
    if path.read_bytes()!=raw:raise RuntimeError(f'Concurrent edit: {path}')
    path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
    return {'path':path.relative_to(ROOT).as_posix(),'publication_hooks':len(edits)-(1 if HEADER in text and HEADER not in original else 0)}


if __name__ == '__main__':
    candidates=[ROOT/x['path'] for x in json.loads((HERE/'author-candidates.json').read_text(encoding='utf-8'))
                if 'IndexCandidates' not in x['path']]
    candidates += [ROOT/'SourceAssets/ApprenticeStaff20260927/create_catalog.py',
                   ROOT/'SourceAssets/TimeSandPolish20261101/install_materials.py']
    report=[result for path in candidates if (result:=sync(path))]
    (HERE/'author-sync.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'updated_authors':len(report),'hooks':sum(x['publication_hooks'] for x in report)},ensure_ascii=False))
