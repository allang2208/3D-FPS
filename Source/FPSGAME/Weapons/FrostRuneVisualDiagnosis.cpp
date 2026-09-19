#include "FrostRuneVisualDiagnosis.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "RuneSwordComponent.h"
#include "MeleeRuneVisual.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/GameInstance.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "TimerManager.h"
#include "UnrealClient.h"

void TickFrostRuneVisualDiagnosis(AFPSGAMECharacter* C)
{
    static bool Started=false;
    if(Started||!C||!C->GetController())return;
    Started=true;
    auto* P=C->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!P||!P->IsAudit()||!P->ProfileSlot().StartsWith(TEXT("ColdSteel_FrostRuneVisualAudit_")))
    {UE_LOG(LogTemp,Error,TEXT("FROST_RUNE_VISUAL: isolated profile required"));FPlatformMisc::RequestExitWithStatus(false,2);return;}
    C->GetCharacterMovement()->DisableMovement();
    C->SetActorLocation(FVector(0,0,200));C->SetActorRotation(FRotator::ZeroRotator);
    C->GetController()->SetControlRotation(FRotator::ZeroRotator);
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("FrostRuneVisualDiagnosis")/P->ProfileSlot();
    IFileManager::Get().MakeDirectory(*Dir,true);
    for(const FRotator R:{FRotator(-40,-30,0),FRotator(-10,160,0)})
    {auto* L=C->GetWorld()->SpawnActor<ADirectionalLight>(FVector::ZeroVector,R);L->GetLightComponent()->SetIntensity(3.f);}
    auto Later=[C](float Seconds,TFunction<void()> F){FTimerHandle H;C->GetWorldTimerManager().SetTimer(H,[F](){F();},Seconds,false);};
    auto Record=[C,P,Dir](const FString& Tag)
    {
        FString Rows=FString::Printf(TEXT("equipped=%s\n"),P->Equipped()?*P->Equipped()->Data:TEXT("none"));
        TArray<USkeletalMeshComponent*> Meshes;C->GetComponents(Meshes);
        for(auto* M:Meshes)if(M->GetName()==TEXT("RuneSwordViewmodel"))
        {
            Rows+=FString::Printf(TEXT("mesh=%s visible=%d hidden=%d transform=%s\n"),*GetPathNameSafe(M->GetSkeletalMeshAsset()),M->IsVisible(),M->bHiddenInGame,*M->GetComponentTransform().ToString());
            for(int32 I=0;I<M->GetNumMaterials();++I)
            {
                auto* O=M->GetOverlayMaterial(true,I);
                Rows+=FString::Printf(TEXT("slot=%d material=%s overlay=%s\n"),I,*GetPathNameSafe(M->GetMaterial(I)),*GetPathNameSafe(O));
                if(auto* D=Cast<UMaterialInstanceDynamic>(O))Rows+=FString::Printf(TEXT("origin=%s axis=%s mode=%.1f texture=%s\n"),*D->K2_GetVectorParameterValue(TEXT("BladeOrigin")).ToString(),*D->K2_GetVectorParameterValue(TEXT("BladeAxis")).ToString(),D->K2_GetScalarParameterValue(TEXT("RuneMode")),*GetPathNameSafe(D->K2_GetTextureParameterValue(TEXT("RuneTexture"))));
            }
        }
        FFileHelper::SaveStringToFile(Rows,*(Dir/(Tag+TEXT(".txt"))));
        FScreenshotRequest::RequestScreenshot(Dir/(Tag+TEXT(".png")),false,false);
        UE_LOG(LogTemp,Display,TEXT("FROST_RUNE_VISUAL: %s %s"),*Tag,*Rows);
    };
    Later(6,[C,P]()
    {
        auto State=P->Snapshot();State.Items.Reset();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);
        auto Sword=P->CreateItem(TEXT("ue_frost_crystal_sword"));Sword.Place=1;Sword.Cell=9;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Sword.Data),Data);
        auto Parts=MakeShared<FJsonObject>();
        FString Rune=TEXT("erosion_rune"),Guard=TEXT("riposte_guard");
        FParse::Value(FCommandLine::Get(),TEXT("Rune="),Rune);FParse::Value(FCommandLine::Get(),TEXT("Guard="),Guard);
        Parts->SetStringField(TEXT("blade_2"),Rune);Parts->SetStringField(TEXT("guard"),Guard);Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
        Sword.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Sword.Data));
        State.Items.Add(Sword);State.ActiveWeaponSlot=9;P->CommitState(State);
    });
    Later(10,[C](){
        C->FindComponentByClass<URuneSwordComponent>()->SetComponentTickEnabled(false);
        TArray<USkeletalMeshComponent*> Meshes;C->GetComponents(Meshes);
        for(auto* M:Meshes)if(M->GetName()==TEXT("RuneSwordViewmodel"))ColdSteelMeleeRune::Apply(M,FString());
    });
    Later(11,[Record](){Record(TEXT("hold_without_rune"));});
    Later(11.2f,[C,P](){
        TArray<USkeletalMeshComponent*> Meshes;C->GetComponents(Meshes);
        for(auto* M:Meshes)if(M->GetName()==TEXT("RuneSwordViewmodel"))ColdSteelMeleeRune::Apply(M,ColdSteelMeleeRune::Selected(*P->Equipped()));
    });
    Later(12,[Record](){Record(TEXT("hold"));});
    Later(12.8f,[C](){C->FindComponentByClass<URuneSwordComponent>()->SetComponentTickEnabled(true);});
    Later(13,[C](){C->FindComponentByClass<URuneSwordComponent>()->BeginInspect();});
    Later(14.2f,[Record](){Record(TEXT("inspect"));});
    Later(13.4f,[Record](){Record(TEXT("inspect_front"));});
    Later(15.2f,[Record](){Record(TEXT("inspect_back"));});
    Later(18,[Dir](){UE_LOG(LogTemp,Display,TEXT("FROST_RUNE_VISUAL: COMPLETE %s"),*Dir);FPlatformMisc::RequestExitWithStatus(false,0);});
}
