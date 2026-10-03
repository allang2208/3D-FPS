"""Apply this existing-function change to the already running editor, synchronously."""
import unreal as u,json,os,time,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
inputs=json.loads((O/'recovery_inputs.json').read_text())
if os.getpid()!=inputs['pid']:raise RuntimeError('Editor changed; retain the source and compile against its current process')
files=['Source/FPSGAME/FPSGAMECharacter.cpp','Source/FPSGAME/Weapons/RifleReloadRecovery.h']
receipt={'pid':os.getpid(),'started_unix':time.time(),'method':'LiveCoding.CompileSync on existing editor under MCP batch mutex',
 'source_sha256':{f:hashlib.sha256((P/f).read_bytes()).hexdigest() for f in files},'base_editor_dll_rebuilt':False,'game_tested':False}
(O/'compile_request.json').write_text(json.dumps(receipt,indent=2))
u.SystemLibrary.execute_console_command(None,'LiveCoding.CompileSync')
receipt['synchronous_command_returned_unix']=time.time()
(O/'compile_request.json').write_text(json.dumps(receipt,indent=2))
print('RIFLE_RECOVERY_COMPILE_SYNC_RETURNED',os.getpid(),flush=True)
