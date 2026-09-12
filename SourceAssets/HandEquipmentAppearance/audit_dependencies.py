"""Read-only package reference audit before/after retiring appearance trials."""
import json
from pathlib import Path
import unreal as u

OUT=Path(__file__).parent
registry=u.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
options=u.AssetRegistryDependencyOptions(include_hard_package_references=True,
    include_soft_package_references=True, include_searchable_names=True,
    include_hard_management_references=True, include_soft_management_references=True)
retired=[
    '/Game/Characters/ArmsBlackWhiteTrial/M_Manny_BlackWhite_01',
    '/Game/Characters/ArmsBlackWhiteTrial/M_Manny_BlackWhite_02',
    '/Game/Characters/ArmsBlackWhiteTrial/T_Manny_GloveMask',
    '/Game/Characters/ArmsBlackWhiteTrial/Backup/MI_Manny_01_Original',
    '/Game/Characters/ArmsBlackWhiteTrial/Backup/MI_Manny_02_Original',
    '/Game/Characters/ArmsLeatherCandidate/M_Manny_WhiteLeather',
    '/Game/Characters/ArmsLeatherCandidate/M_Manny_OriginalLeather',
    '/Game/Characters/ArmsLeatherCandidate/Backup/MI_Manny_02_BeforeLeather',
    '/Game/Characters/ArmsSkinSleeveCandidate/M_Manny_SkinGlove_02',
    '/Game/Characters/ArmsGloveCuffCandidate/M_Manny_LongCuff_02',
    '/Game/Characters/ArmsGloveCuffCandidate/T_Manny_LongCuffField',
]
roots=['/Game/Weapons/M4InfimaV3/MI_Manny_01','/Game/Weapons/M4InfimaV3/MI_Manny_02']
pending=list(roots);closure=set()
while pending:
    package=pending.pop()
    if package in closure:continue
    closure.add(package)
    pending += [str(p) for p in (registry.get_dependencies(package,options) or []) if str(p).startswith('/Game/')]
rows=[]
for package in retired:
    # Removed packages return None after archive; existing unreferenced ones return [].
    refs=sorted(str(p) for p in (registry.get_referencers(package,options) or []))
    external=[p for p in refs if p not in retired]
    rows.append({'package':package,'exists':u.EditorAssetLibrary.does_asset_exist(package),
                 'referencers':refs,'external_referencers':external})
report={'active_roots':roots,'active_dependency_closure':sorted(closure),'retired':rows,
        'retired_in_active_closure':sorted(closure.intersection(retired)),
        'external_referencers':{r['package']:r['external_referencers'] for r in rows if r['external_referencers']}}
(OUT/'dependency_audit.json').write_text(json.dumps(report,indent=2))
assert not report['retired_in_active_closure'],report
assert not report['external_referencers'],report
u.log('HAND_APPEARANCE_DEPENDENCY_AUDIT_PASS')
