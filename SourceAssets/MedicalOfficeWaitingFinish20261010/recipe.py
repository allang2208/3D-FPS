"""Reuse the ward bench at the four existing waiting anchors; retain the old asset."""
BENCH='/Game/Props/HospitalWaitingBench20260929/SM_Hospital_Waiting_Bench'
RETAINED='/Game/HospitalCorridor/Meshes/Objects/SM_HospitalBench_01'
REVISION='medical_waiting_benches_and_mid_rail_20261010'
def apply(module):
 changes=[]
 for i,x in enumerate((420,680,1290,1540)):
  part=next(p for p in module['parts'] if p.get('id')=='MedicalOffice.Waiting.Bench'+str(i))
  # The ward bench has a floor-centred pivot; its backrest is local -Y in UE.
  part.update(mesh=BENCH,position=[x,-940,.8],yaw=180,scale=[1,1,1],materials=[],collision=True,affects_navigation=True,cast_shadow=True)
  changes.append(part)
 used={p['mesh'] for p in module['parts']}
 dependencies=set(module.get('runtime_assets',[])+[BENCH])
 if RETAINED not in used:dependencies.discard(RETAINED)
 module['runtime_assets']=sorted(dependencies)
 module.setdefault('authoring',{})['waiting_finish']=dict(revision=REVISION,bench=BENCH,count=4,retained_previous_mesh=RETAINED,
  mid_rail_tile_cut_cm=[91,98],floor_gap_cm=.2)
 return changes
