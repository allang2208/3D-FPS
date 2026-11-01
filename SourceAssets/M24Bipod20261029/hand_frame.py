from pathlib import Path
exec(compile((Path(__file__).parent.parent/'M24QuickMeleeContact20261028/library.py').read_text().split("if __name__=='__main__':")[0],'library','exec'))
idle,local=pose('idle',0);native=rest['WPN_root']@idle['WPN_root'].inverted()
report={'points':{n:list((native@idle[n]).translation) for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l','thumb_01_l','thumb_02_l','thumb_03_l','index_01_l','index_02_l','index_03_l','middle_01_l','middle_02_l','middle_03_l','ring_01_l','pinky_01_l')},'fingers':{n:list((local_rest[n].inverted()@local[n]).to_euler()) for n in names if any(n.startswith(d+'_') for d in ('index','middle','ring','pinky','thumb')) and n.endswith('_l')},'hand':[list(v) for v in native@idle['hand_l']]}
(O/'hand_frame.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
