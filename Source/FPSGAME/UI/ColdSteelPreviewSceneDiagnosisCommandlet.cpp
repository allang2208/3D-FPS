#include "ColdSteelPreviewSceneDiagnosisCommandlet.h"
#include "ColdSteelPreviewScene.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "Components/SceneComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Misc/ScopeExit.h"
#include "UObject/StrongObjectPtr.h"

int32 UColdSteelPreviewSceneDiagnosisCommandlet::Main(const FString&)
{
    // No GameInstance, player profile, map loading or gameplay. The deliberately
    // invalid CDO exists only in this commandlet process and is restored in scope.
    int32 Checks=0, Failures=0;
    auto Require=[&](bool Pass,const TCHAR* Label)
    {
        ++Checks; if(!Pass)++Failures;
        UE_LOG(LogTemp,Display,TEXT("[PreviewSceneDiagnosis] %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Label);
    };
    auto Values=FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false)
        .SetCreateDefaultLighting(false).SetTransactional(false).SetForceMipsResident(false);
    UClass* Class=UDungeonRunSubsystem::StaticClass();
    TStrongObjectPtr<UObject> OriginalDefaults(Class->GetDefaultObject());
    TStrongObjectPtr<UObject> WrongDefaults(NewObject<USceneComponent>(GetTransientPackage(),NAME_None,RF_Transient));
    const int32 WorldContextsBefore=GEngine->GetWorldContexts().Num();
    FString Failure;
    {
        Class->SetDefaultObject(WrongDefaults.Get());
        ON_SCOPE_EXIT { Class->SetDefaultObject(OriginalDefaults.Get()); };
        auto Scene=FColdSteelPreviewScene::TryCreate(Values,Failure);
        Require(!Scene,TEXT("wrong subsystem CDO is rejected before engine assertion"));
        Require(Failure.Contains(Class->GetPathName())&&Failure.Contains(TEXT("default_class=/Script/Engine.SceneComponent")),
            TEXT("failure identifies subsystem class and actual CDO type"));
        Require(GEngine->GetWorldContexts().Num()==WorldContextsBefore,TEXT("rejected preview allocates no world context"));
    }
    Require(Class->GetDefaultObject()==OriginalDefaults.Get(),TEXT("fixture restores the original subsystem CDO"));
    {
        auto Scene=FColdSteelPreviewScene::TryCreate(Values,Failure);
        Require(Scene&&Scene->GetWorld()&&Scene->GetWorld()->WorldType==EWorldType::GamePreview,
            TEXT("valid subsystem CDOs create the normal game-preview world"));
        Require(Failure.IsEmpty(),TEXT("successful creation clears the old failure"));
    }
    Require(GEngine->GetWorldContexts().Num()==WorldContextsBefore,TEXT("normal preview teardown releases its world context"));
    UE_LOG(LogTemp,Display,TEXT("[PreviewSceneDiagnosis] checks=%d failures=%d"),Checks,Failures);
    return Failures?1:0;
}
