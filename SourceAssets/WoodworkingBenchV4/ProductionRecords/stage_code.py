from pathlib import Path
import json,hashlib
W=Path(__file__).resolve().parent;P=Path('D:/FPS3D/FPSGAME');B=W/'Before';S=W/'Staged'
paths=['Source/FPSGAME/Building/VoxelBuildPrefabActor.cpp','Source/FPSGAME/UI/ColdSteelWoodworkingWidget.cpp','Source/FPSGAME/UI/ColdSteelWoodworkingWidget.h']
for rel in paths:
    src=(B/rel).read_text(encoding='utf-8-sig')
    if rel.endswith('VoxelBuildPrefabActor.cpp'):
        src=src.replace('#include "CastingToolRackComponent.h"','#include "CastingToolRackComponent.h"\n#include "WoodworkingSawVisualComponent.h"')
        src=src.replace('    MeshComponent->SetStaticMesh(Mesh);','    if(auto* PreviousSaw=FindComponentByClass<UWoodworkingSawVisualComponent>())PreviousSaw->DestroyComponent();\n    MeshComponent->SetStaticMesh(Mesh);',1)
        old='        AddInstanceComponent(Rack);Rack->RegisterComponent();Rack->Configure(MeshComponent);\n    }'
        assert old in src
        src=src.replace(old,old+'\n    if(Id==VoxelWoodworkingBenchId&&GetWorld()->IsGameWorld()&&MeshComponent->DoesSocketExist(TEXT("WoodworkingSawPivot")))\n    {\n        auto* Saw=NewObject<UWoodworkingSawVisualComponent>(this,NAME_None,RF_Transient);\n        AddInstanceComponent(Saw);Saw->RegisterComponent();Saw->Configure(MeshComponent);\n    }',1)
    elif rel.endswith('.h'):
        src=src.replace('class UWoodworkingSystem;','class UWoodworkingSystem;\nclass UWoodworkingSawVisualComponent;')
        src=src.replace('    UPROPERTY(Transient) TObjectPtr<UAudioComponent> CutAudio;','    UPROPERTY(Transient) TObjectPtr<UAudioComponent> CutAudio;\n    TWeakObjectPtr<UWoodworkingSawVisualComponent> SawVisual;')
    else:
        src=src.replace('#include "ColdSteelWoodworkingWidget.h"\n','#include "ColdSteelWoodworkingWidget.h"\n#include "../Building/WoodworkingSawVisualComponent.h"\n',1)
        old='{Workbench=Station;bPracticeOnly=PracticeOnly;if(Woodworking){Woodworking->Open(PracticeOnly);}LastRevision=-1;}'
        new='''{
    if(auto* Saw=SawVisual.Get())Saw->SetPowered(false);
    Workbench=Station;bPracticeOnly=PracticeOnly;
    SawVisual=Station&&!PracticeOnly?Station->FindComponentByClass<UWoodworkingSawVisualComponent>():nullptr;
    if(Woodworking)Woodworking->Open(PracticeOnly);LastRevision=-1;
}'''
        assert old in src;src=src.replace(old,new)
        src=src.replace('    CancelInput();if(Woodworking)Woodworking->Close();','    if(auto* Saw=SawVisual.Get())Saw->SetPowered(false);SawVisual.Reset();\n    CancelInput();if(Woodworking)Woodworking->Close();')
        src=src.replace('    Super::NativeTick(G,Delta);if(!Woodworking)return;','    Super::NativeTick(G,Delta);if(!Woodworking)return;\n    if(auto* Saw=SawVisual.Get())Saw->SetPowered(Woodworking->MotorRunning());')
        src=src.replace('{CancelInput();if(Woodworking)Woodworking->Abandon();','{if(auto* Saw=SawVisual.Get())Saw->SetPowered(false);CancelInput();if(Woodworking)Woodworking->Abandon();')
    target=S/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(src,encoding='utf-8')
for name in ['WoodworkingSawVisualComponent.h','WoodworkingSawVisualComponent.cpp']:
    rel='Source/FPSGAME/Building/'+name;target=S/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((W/name).read_bytes());paths.append(rel)
(W/'code_paths.json').write_text(json.dumps(paths,indent=2))
print('CODE_STAGED',len(paths))
