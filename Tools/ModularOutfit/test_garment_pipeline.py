"""Regression fixtures for the actual shoulder-sheet failure and gate semantics."""
import unittest
import tempfile
from pathlib import Path
from garment_pipeline import read,write,mesh_issues,PROJECT,gate,publish

class GarmentStructureTests(unittest.TestCase):
    def test_original_shoulder_sheet_is_rejected(self):
        d=read(PROJECT/'SourceAssets/SVDOutfitSpike20260929/ue_chainmail_shirt_rig_meshes.json')
        self.assertIn('oversized_rest_edge',mesh_issues(d,{'max_rest_edge_cm':5}))

    def test_repaired_three_garments_have_no_original_sheet(self):
        root=PROJECT/'SourceAssets/SVDOutfitSpike20260929'
        for name in ['ue_chainmail_shirt','ue_field_sweater','ue_field_sweater_charcoal']:
            with self.subTest(name=name):
                self.assertEqual([],mesh_issues(read(root/(name+'_fixed.json')),{'max_rest_edge_cm':5}))

    def sample(self):
        return dict(positions=[[0,0,0],[1,0,0],[0,1,0]],triangles=[[0,1,2]],weights=[{'upperarm_l':1}]*3,rest={'upperarm_l':{},'upperarm_r':{}})

    def test_duplicate_geometry_is_detected_despite_split_vertex_ids(self):
        d=self.sample();d['positions']*=2;d['weights']*=2;d['triangles'].append([5,4,3])
        self.assertTrue(any(x.startswith('coincident_duplicate_faces') for x in mesh_issues(d,{'max_rest_edge_cm':5})))

    def test_opposite_arm_transfer_is_rejected(self):
        d=self.sample();d['weights'][1]={'upperarm_l':.5,'upperarm_r':.5}
        self.assertTrue(any(x.startswith('cross_arm_weights') for x in mesh_issues(d,{'max_rest_edge_cm':5})))

    def test_invalid_bind_and_nonfinite_weights_are_rejected(self):
        d=self.sample();d['weights'][1]={'missing':1}
        self.assertTrue(any(x.startswith('unknown_weight_bone') for x in mesh_issues(d,{'max_rest_edge_cm':5})))
        d['weights'][1]={'upperarm_l':float('nan')}
        self.assertTrue(any(x.startswith('invalid_weights') for x in mesh_issues(d,{'max_rest_edge_cm':5})))

    def test_missing_visual_evidence_cannot_publish(self):
        source=PROJECT/'SourceAssets/GarmentFoundation20260929/ue_chainmail_shirt/candidate.json'
        config=PROJECT/'Content/ColdSteelData/modular_outfits.json';prior=config.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'candidate.json';write(path,read(source));result=gate(path)
            self.assertEqual('blocked',result['status']);self.assertIn('pending:runtime_visual',result['errors'])
            with self.assertRaises(RuntimeError):publish(path)
        self.assertEqual(prior,config.read_bytes())

    def test_changed_snapshot_cannot_reuse_receipt(self):
        source=PROJECT/'SourceAssets/GarmentFoundation20260929/ue_chainmail_shirt/candidate.json'
        with tempfile.TemporaryDirectory() as tmp:
            m=read(source);path=Path(tmp)/'candidate.json';snap=Path(tmp)/'LOD0.json'
            ref=m['candidates']['M4']['snapshots']['0'];d=read(ref['path']);d['positions'][0][0]+=30;write(snap,d);ref['path']=str(snap);write(path,m)
            self.assertIn('snapshot_changed:M4',gate(path)['errors'])

if __name__=='__main__':unittest.main()
