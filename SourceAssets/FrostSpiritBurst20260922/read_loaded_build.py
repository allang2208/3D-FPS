"""Read the loaded module build identity to determine whether reload is needed.

This reads editor process state only; it does not start gameplay or test combat.
"""
from pathlib import Path
import ctypes,json,os,struct
import unreal as u

P=Path(__file__).resolve().parent
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p]
kernel.GetModuleHandleW.restype=ctypes.c_void_p
base=kernel.GetModuleHandleW('UnrealEditor-FPSGAME.dll')
path=P.parents[1]/'Binaries/Win64/UnrealEditor-FPSGAME.dll'
disk=path.read_bytes()
def identity(header):
    pe=struct.unpack_from('<I',header,0x3c)[0]
    return {'timestamp':struct.unpack_from('<I',header,pe+8)[0],
            'image_size':struct.unpack_from('<I',header,pe+24+56)[0]}
loaded=identity(ctypes.string_at(base,4096)) if base else None
current=identity(disk)
row={'pid':os.getpid(),'loaded':loaded,'disk':current,'matches_current_build':loaded==current,
     'pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),
     'command_line':u.SystemLibrary.get_command_line()}
(P/'editor_module_receipt.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
print(json.dumps(row))
