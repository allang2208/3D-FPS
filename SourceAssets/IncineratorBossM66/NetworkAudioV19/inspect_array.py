from pathlib import Path
import unreal as u
api=u.get_default_object(u.NiagaraToolset_System)
script=u.load_asset('/Niagara/DynamicInputs/Arrays/SelectVector4_FromArray')
schema=api.call_method('GetDynamicInputSchemaFromAsset',(script,))
Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/NetworkAudioV19/array_schema.txt').write_text(schema.export_text(),encoding='utf8')
print('M66_ARRAY_SCHEMA '+schema.export_text())
