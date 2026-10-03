from pathlib import Path
p=Path('Source/FPSGAME/Monsters/HangingBellM09.cpp')
s=p.read_text(encoding='utf8')
s=s.replace('for(auto* W:Waves)','for(const auto& W:Waves)').replace('for(auto* Cmp:Waves)','for(const auto& Cmp:Waves)')
s=s.replace('if(!HasAuthority()||!R)return;','if(!HasAuthority()||!R||!VisualMesh)return;')
s=s.replace('AI.Class?AI.Class:AMonsterAIController::StaticClass()','AI.Class?AI.Class.Get():AMonsterAIController::StaticClass()')
s=s.replace('GetCharacterMovement()->GravityScale=1;GetCharacterMovement()->SetMovementMode(MOVE_Falling);','GetCharacterMovement()->DefaultLandMovementMode=MOVE_Walking;\n     GetCharacterMovement()->GravityScale=1;GetCharacterMovement()->SetMovementMode(MOVE_Falling);')
p.write_text(s,encoding='utf8')
base=Path('Tools/HangingBellM09')
for stage in ['materials','motion','fx']:
 (base/('import_'+stage+'_v04.py')).write_text("M09_STAGE='"+stage+"'\nexec(compile(open('D:/FPS3D/FPSGAME/Tools/HangingBellM09/import_assets_v04.py',encoding='utf8').read(),'import_assets_v04.py','exec'))\n",encoding='utf8')
