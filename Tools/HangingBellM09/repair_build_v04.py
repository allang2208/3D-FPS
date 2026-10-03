from pathlib import Path
import re
p=Path('Source/FPSGAME/Monsters/HangingBellM09.cpp');s=p.read_text(encoding='utf8')
s=s.replace('FObjectFinder<USkeletalMesh> Mesh(', 'FObjectFinder<USkeletalMesh> MeshAsset(').replace('VisualMesh=Mesh.Object','VisualMesh=MeshAsset.Object')
s=re.sub(r'\bRole\b','ClipRole',s)
s=s.replace('const FString Path=FString::Printf','const FString AssetPath=FString::Printf').replace('A(*Path)','A(*AssetPath)').replace('S(*Path)','S(*AssetPath)')
s=s.replace('TArray<FLifetimeProperty>& O)','TArray<FLifetimeProperty>& OutLifetimeProps)').replace('Super::GetLifetimeReplicatedProps(O)','Super::GetLifetimeReplicatedProps(OutLifetimeProps)')
s=re.sub(r'\bInstigator\b','EventInstigator',s)
p.write_text(s,encoding='utf8')
p=Path('Config/DefaultGame.ini');s=p.read_text(encoding='utf8')
if '/Game/Tests/HangingBellM09/L_M09CeilingTest' not in s:
 s+='\n; M09 authored ceiling-room entry and string-loaded monster assets.\n[/Script/UnrealEd.ProjectPackagingSettings]\n+MapsToCook=(FilePath="/Game/Tests/HangingBellM09/L_M09CeilingTest")\n+DirectoriesToAlwaysCook=(Path="/Game/Monsters/HangingBellM09/V04")\n'
 p.write_text(s,encoding='utf8')
