"""Stage only the twelve existing texture packages for background authoring."""
import json, hashlib, shutil
from pathlib import Path
P = Path(__file__).resolve().parent
PROJECT = P.parents[1]
HOST = P / 'StagingHost'
(HOST / 'Config').mkdir(parents=True, exist_ok=True)
(HOST / 'KukriGripAuthoring.uproject').write_text(json.dumps({
    'FileVersion': 3, 'EngineAssociation': '5.8', 'Plugins': [
    {'Name': 'PythonScriptPlugin', 'Enabled': True},
    {'Name': 'EditorScriptingUtilities', 'Enabled': True}]}, indent=2), encoding='utf-8')
(HOST / 'Config/DefaultEngine.ini').write_text(
    '[/Script/Engine.RendererSettings]\nr.Substrate=True\nr.Substrate.ProjectGBufferFormat=0\n', encoding='utf-8')
data = json.loads((P / 'surfaces.json').read_text(encoding='utf-8'))
final = json.loads((P.parent / 'KukriFinalIntegration20261026/manifest.json').read_text(encoding='utf-8'))
variants = {v['icon_key']: v for v in data['variants']}
jobs = []
for v in variants.values():
    folder = v['material'].split('/Materials/')[0] + '/Textures/'
    for suffix, source in v['textures'].items():
        jobs.append({'package': folder + Path(source).stem, 'source_image': source, 'channel': suffix})
for binding in final['bindings']:
    if binding['master'] in variants:
        jobs.append({'package': binding['texture'].split('.')[0], 'source_image': variants[binding['master']]['icon'],
                     'channel': 'Icon', 'binding': binding})
baseline = []
for job in jobs:
    relative = Path(job['package'].removeprefix('/Game/'))
    for suffix in ('.uasset', '.uexp', '.ubulk'):
        target = (PROJECT / 'Content' / relative).with_suffix(suffix)
        staged = (HOST / 'Content' / relative).with_suffix(suffix)
        if not target.exists():
            if suffix == '.uasset':
                raise RuntimeError('Existing texture missing: ' + str(target))
            continue
        if staged.exists():
            raise RuntimeError('Use a fresh staging directory: ' + str(staged))
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, staged)
        baseline.append({'package': job['package'], 'target': str(target), 'staged': str(staged),
                         'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    if job['channel'] == 'Icon':
        target = Path(job['binding']['runtime_png'])
        baseline.append({'package': job['package'], 'target': str(target), 'staged': job['source_image'],
                         'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
(P / 'Receipts/staging-inputs.json').write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding='utf-8')
(P / 'import-jobs.json').write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding='utf-8')
print('KUKRI_GRIP_STAGED_PACKAGES ' + str(len(jobs)))
