#include "SkillNetworkAuditCommandlet.h"
#include "FPSFireMagicComponent.h"
#include "MeteorAssets.h"
#include "PlayerSkillPreparation.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

// Explicit, isolated commandlet: real resource loading and collision queries,
// without map BeginPlay, gameplay rendering, audio or the user's save slot.
int32 USkillNetworkAuditCommandlet::RunMeteorReadyPreviewAudit(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    const FString Slot=TEXT("SkillNetworkAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("SkillNetworkAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("MeteorReadyPreviewAudit"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool OK,const FString& Name,const FString& Detail=FString())
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);
        Row->SetBoolField(TEXT("passed"),OK);Row->SetStringField(TEXT("detail"),Detail);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("METEOR_READY_PREVIEW %s %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name,*Detail);
    };
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.Hotbar.Init(TEXT(""),4);Seed.HotbarDefinitions.Init(TEXT(""),4);for(auto& B:Seed.QuickBindings)B={};
    Seed.DungeonRun={};Seed.MeteorCooldown=0;Seed.Mana=10000;
    for(auto& Skill:Seed.Skills){Skill.Value.Level=1;Skill.Value.Experience=0;}
    auto Staff=Model->CreateItem(TEXT("ue_apprentice_staff"));Staff.Place=1;Staff.Cell=6;Seed.Items={Staff};
    Model->Current=Seed;
    auto* PC=World->SpawnActor<APlayerController>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,400),FRotator::ZeroRotator);
    PC->SetAsLocalPlayerController();PC->Possess(Pawn);Model->CurrentPawn=Pawn;
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health->Health=Health->MaxHealth;
    auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>();
    auto* Camera=Pawn->FindComponentByClass<UCameraComponent>();
    Camera->SetWorldLocation(FVector(0,0,400));Camera->SetWorldRotation(FRotator(-45,0,0));
    Check(Pawn->IsLocallyControlled()&&Model->HasEquippedStaff(),TEXT("local staff fixture"),
        FString::Printf(TEXT("local=%d staff=%d"),Pawn->IsLocallyControlled(),Model->HasEquippedStaff()));

    TArray<FSoftObjectPath> Paths;PlayerSkillAssets::Gather(TEXT("meteor"),Seed,Paths);
    Check(Paths.Contains(FSoftObjectPath(MeteorSpellAssets::GroundFire))
        &&!Paths.ContainsByPredicate([](const auto& P){return P.ToString().Contains(TEXT("MeteorFilledVolumeV2"));}),
        TEXT("meteor preparation selects V3 without V2 system"));
    // Blocking load belongs only to this offline fixture, never to preview Tick.
    const auto Loaded=UAssetManager::GetStreamableManager().RequestSyncLoad(Paths);
    for(const auto& Path:Paths)Check(Path.ResolveObject()!=nullptr,TEXT("prepared asset resolves"),Path.ToString());
    Fire->ResolveMeteorAssets();
    Check(Fire->bMeteorAssetsReady&&Fire->CastSound&&Fire->MeteorAimMaterial,TEXT("actual readiness callback becomes ready"));
    FFireMagicCast Spell;
    Check(Fire->PrepareCastRequest(TEXT("meteor"),Spell),TEXT("meteor passes actual local cast gate"),Fire->Message);

    auto* Floor=World->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Floor);
    Floor->AddInstanceComponent(Box);Floor->SetRootComponent(Box);Box->SetBoxExtent(FVector(3000,3000,20));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Box->SetCollisionResponseToAllChannels(ECR_Block);
    Box->RegisterComponent();Floor->SetActorLocation(FVector(0,0,-20));
    Fire->SetMeteorAimPreview(true);
    Check(Fire->bMeteorAimPreview&&Fire->bMeteorPreviewValid&&Fire->MeteorAimDecal,
        TEXT("hold resolves real floor and creates preview"),Fire->MeteorPreviewFailure);
    auto* OriginalDecal=Fire->MeteorAimDecal.Get();auto* OriginalMID=Fire->MeteorAimMID.Get();
    const float ManaBefore=Model->Snapshot().Mana;
    for(int32 Hz:{30,60,144})
    {
        int32 MovedFrames=0,AlignedFrames=0;
        for(int32 Frame=0;Frame<30;++Frame)
        {
            const FVector Before=Fire->LockedPoint;
            Camera->SetWorldRotation(FRotator(-45,Frame*.5f+Hz,0));
            Fire->TickComponent(1.f/Hz,LEVELTICK_All,&Fire->PrimaryComponentTick);
            MovedFrames+=Fire->bMeteorPreviewValid&&!Fire->LockedPoint.Equals(Before,.01f);
            AlignedFrames+=Fire->MeteorAimDecal
                &&Fire->MeteorAimDecal->GetComponentLocation().Equals(Fire->LockedPoint+FVector(0,0,4),.01f)
                &&Fire->MeteorAimMID->K2_GetVectorParameterValue(TEXT("Center")).Equals(FLinearColor(Fire->LockedPoint),.01f);
        }
        Check(MovedFrames==30&&AlignedFrames==30,FString::Printf(TEXT("every-frame tracking at %d Hz input"),Hz),
            FString::Printf(TEXT("moved=%d/30 aligned=%d/30"),MovedFrames,AlignedFrames));
    }
    Check(OriginalDecal&&OriginalMID&&Fire->MeteorAimDecal==OriginalDecal&&Fire->MeteorAimMID==OriginalMID,
        TEXT("drag reuses decal and material instance"));
    Check(Model->Snapshot().Mana==ManaBefore&&Model->FireMagicCooldown(TEXT("meteor"))==0,
        TEXT("preview does not spend mana or start cooldown"));
    Camera->SetWorldRotation(FRotator(40,0,0));Fire->TickComponent(1.f/144,LEVELTICK_All,&Fire->PrimaryComponentTick);
    Check(!Fire->bMeteorPreviewValid&&Fire->MeteorAimDecal&&Fire->MeteorAimDecal->bHiddenInGame,
        TEXT("invalid sky target hides preview immediately"));
    Camera->SetWorldRotation(FRotator(-45,0,0));Fire->TickComponent(1.f/144,LEVELTICK_All,&Fire->PrimaryComponentTick);
    Check(Fire->bMeteorPreviewValid&&Fire->MeteorAimDecal&&!Fire->MeteorAimDecal->bHiddenInGame,
        TEXT("return to floor restores preview next frame"));
    Fire->SetMeteorAimPreview(false);

    auto Root=MakeShared<FJsonObject>();Root->SetNumberField(TEXT("checks"),Rows.Num());Root->SetNumberField(TEXT("failures"),Failures);
    Root->SetBoolField(TEXT("rendered_gameplay"),false);Root->SetBoolField(TEXT("real_network_transport"),false);
    Root->SetArrayField(TEXT("results"),Rows);FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*(FPaths::ProjectDir()/TEXT("SourceAssets/MeteorReadyPreview20261022/native-result.json")));
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
