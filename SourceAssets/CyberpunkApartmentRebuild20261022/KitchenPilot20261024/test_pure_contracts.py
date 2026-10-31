"""Opt-in pure-function regression tests for the kitchen authoring contract.
Run explicitly with Blender Python or `blender -b -t 1 --python-expr "import unittest; unittest.main(...)"`.
This file is never called by the UE asset or map publication batches.
"""
from pathlib import Path
import hashlib
import json
import sys
import types
import unittest


def collect_case_ids(suite):
    cases = []
    for entry in suite:
        if isinstance(entry, unittest.TestSuite):
            cases.extend(collect_case_ids(entry))
        else:
            cases.append(entry.id())
    return cases

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


class FridgeSlotContractTests(unittest.TestCase):
    def test_replacement_rule(self):
        # Inject only a minimal Unreal reflection shell. The complete production
        # installer is never imported and its main() is never invoked here.
        u = types.ModuleType('unreal')
        u.EditorAssetLibrary = types.SimpleNamespace()
        u.EditorActorSubsystem = types.SimpleNamespace()
        u.MaterialEditingLibrary = types.SimpleNamespace()
        u.AssetToolsHelpers = types.SimpleNamespace(get_asset_tools=lambda: None)
        sys.modules['unreal'] = u
        spec = __import__('importlib.util', fromlist=['util']).spec_from_file_location(
            'kitchen_install_pure_fixture', ROOT / 'install_level.py')
        module = __import__('importlib.util', fromlist=['util']).module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.fridge_slot_role('RS_Ceramic'), 'Enamel')
        self.assertEqual(module.fridge_slot_role('RS_BareSteel'), 'Steel')
        self.assertIsNone(module.fridge_slot_role('RS_PaintedSteel'))
        for slot in ('RS_FreshPlastic', 'RS_PoolIvory', 'RS_Rubber', 'Unknown'):
            self.assertIsNone(module.fridge_slot_role(slot), slot)


class GeometryManifestContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import model as geometry
        source = (ROOT / 'build_kitchen.py').read_text(encoding='utf8')
        begin = source.index('def plate(')
        end = source.index('# Counter:')
        namespace = {'g': geometry}
        exec(compile(source[begin:end], str(ROOT / 'build_kitchen.py'), 'exec'), namespace)
        geometry.clear()
        namespace['plate']('TestPanel', (.2775, .018, .477), .555, .774, thick=.034)
        cls.vertices = geometry.G['TestPanel']['v']
        cls.manifest = json.loads((ROOT / 'assembly.json').read_text(encoding='utf8'))
        cls.receipt = json.loads((ROOT / 'assets_saved.json').read_text(encoding='utf8'))

    def test_panel_geometry_unchanged(self):
        self.assertTrue(self.vertices)
        for axis, expected in ((0, 0.555), (1, .0495 - -.0385), (2, .864 - .09)):
            values = [v[axis] for v in self.vertices]
            self.assertAlmostEqual(max(values) - min(values), expected, places=5)
        self.assertAlmostEqual(min(v[0] for v in self.vertices), 0., places=6)

    def test_manifest_and_receipt_consistency(self):
        self.assertEqual(self.manifest['stage'], 'source_and_fbx_saved')
        self.assertEqual(self.receipt['stage'], 'assets_saved')
        self.assertEqual(len(self.manifest['meshes']), len(self.receipt['meshes']))
        required = {row['key'] for row in self.manifest['meshes']}
        self.assertEqual(required, set(self.receipt['meshes']))
        self.assertEqual(sum(not row.get('reused', False) for row in self.manifest['meshes']), 16)
        for row in self.manifest['meshes']:
            key = row['key']
            entry = self.receipt['meshes'][key]
            self.assertTrue(Path(row['fbx']).is_file(), key)
            digest = hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest()
            self.assertEqual(entry['fbx_sha256'], digest, key)
            self.assertEqual(len(entry['bounds']), 2)
            self.assertEqual(len(entry['bounds'][0]), 3)
            self.assertEqual(len(entry['bounds'][1]), 3)
            self.assertGreaterEqual(len(entry['materials']), 1)
        for key in ('BaseFront', 'UpperFront'):
            self.assertAlmostEqual(self.receipt['meshes'][key]['bounds'][1][0], 55.5, places=3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
