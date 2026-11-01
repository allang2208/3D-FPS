#include "WarhammerModificationAuditCommandlet.h"
#include "ThunderHammerZhenTing.h"
#include "ThunderHammerThrown.h"
#include "ThunderHammerTuning.h"
#include "WarhammerShockwave.h"
#include "ProductionToolComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "TimerManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

int32 UWarhammerModificationAuditCommandlet::AuditZhenTing(const FString& Params)
{
    const FString Original=FCommandLine::Get(),Slot=TEXT("HammerModsAudit_ZhenTing_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("WarhammerModificationAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("ZhenTingAuditWorld"));
    auto* World=GI->GetWorld();auto* Profile=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Profile||!Profile->IsAudit())return 2;
    World->InitializeActorsForPlay(FURL());
    const auto Pump=[&](float Delta){++GFrameCounter;World->GetTimerManager().Tick(Delta);};
    Pump(.001f);
    auto* FloorActor=World->SpawnActor<AActor>();auto* Floor=NewObject<UBoxComponent>(FloorActor);
    FloorActor->AddInstanceComponent(Floor);FloorActor->SetRootComponent(Floor);
    Floor->SetBoxExtent(FVector(5000,5000,20));Floor->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Floor->SetCollisionResponseToAllChannels(ECR_Block);Floor->RegisterComponent();FloorActor->SetActorLocation(FVector(0,0,-20));
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(-500,0,100),FRotator::ZeroRotator);
    auto* PC=World->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();PC->Possess(Pawn);Profile->AttachPawn(Pawn);
    if(auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>())Health->Health=Health->MaxHealth;
    auto Item=Profile->CreateItem(ThunderHammer::Definition);
    Item.Place=1;Item.Cell=6;
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("head_mount"),TEXT("guan_lei_seat"));
    Parts->SetStringField(TEXT("pommel"),TEXT("zhen_ting_pommel"));Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
    const auto SetItem=[&]()
    {
        Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
        auto Seed=Profile->Snapshot();Seed.Items={Item};Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();Seed.Stamina=150;
        Profile->AdoptNetMirror(Seed);
    };
    SetItem();
    auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool->Character=Pawn;Tool->Kind=TEXT("warhammer");
    Tool->EquippedId=Item.InstanceId;Tool->bUsesArms=false;
    Tool->ToolMesh=NewObject<UStaticMeshComponent>(Pawn);Tool->ToolMesh->SetStaticMesh(NewObject<UStaticMesh>());
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool OK,const TCHAR* Name)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("check"),Name);Row->SetBoolField(TEXT("pass"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("ZHENTING %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);
    };
    const auto BeginLocal=[&](bool Heavy,bool Sprint)
    {
        SetItem();Tool->Elapsed=Tool->EquipElapsed=-1.f;Tool->bBluntCharging=false;
        Tool->bBluntReleaseCharge=Heavy;Tool->bBluntHeavy=Heavy;Tool->bBluntSprintAttack=Sprint;
        Tool->BeginUse();return Tool->AxeStrike;
    };
    Check(World->GetNetMode()==NM_Standalone&&Pawn->IsLocallyControlled(),TEXT("uses standalone local input path"));
    const auto Shot=BeginLocal(true,false);
    Check(Tool->Elapsed>=0.f&&Tool->bThunderThrowSeat,TEXT("standalone charged throw accepted"));
    Check(!Shot.ZhenTingForward.IsNearlyZero(),TEXT("standalone charged throw commits continuation"));
    FActorSpawnParameters Spawn;Spawn.Owner=Pawn;Spawn.Instigator=Pawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Hammer=World->SpawnActor<AThunderHammerThrown>(FVector(0,0,100),FRotator::ZeroRotator,Spawn);
    // Use the production launch snapshot, then the actual landing entry point.
    Hammer->Launch(Item,Shot,50.f);
    Check(!Hammer->DamageShot.ZhenTingForward.IsNearlyZero(),TEXT("throw retains continuation"));
    FHitResult Landing;World->LineTraceSingleByChannel(Landing,FVector(0,0,100),FVector(0,0,-100),ECC_Visibility);
    Hammer->Land(Landing);
    const auto Waves=[&]()
    {
        TArray<AWarhammerShockwave*> Found;
        for(TActorIterator<AWarhammerShockwave> It(World);It;++It)if(IsValid(*It))Found.Add(*It);
        return Found;
    };
    const auto Initial=Waves();Check(Initial.Num()==1,TEXT("landing emits original strike"));
    Pump(.24f);Check(Waves().Num()==1,TEXT("no additional strike before 0.25s"));
    Pump(.02f);Check(Waves().Num()==2,TEXT("nearest strike at 0.25s"));
    Hammer->Destroy();if(!Initial.IsEmpty())Initial[0]->Destroy();
    Pump(.25f);Check(Waves().Num()==2,TEXT("middle strike survives retired hammer and origin"));
    Pump(.25f);const auto Final=Waves();Check(Final.Num()==3,TEXT("farthest strike at 0.75s"));
    for(auto* Wave:Final)
    {
        Check(Wave->Shot.ZhenTingForward.IsNearlyZero(),TEXT("additional strike cannot recurse"));
        Check(FMath::IsNearlyEqual(Wave->Shot.DamagePanel.Total(),50.),TEXT("additional strike retains magic damage only"));
    }
    Parts->RemoveField(TEXT("head_mount"));
    Check(!BeginLocal(true,false).ZhenTingForward.IsNearlyZero(),TEXT("standalone ordinary heavy commits continuation"));
    Check(BeginLocal(false,false).ZhenTingForward.IsNearlyZero(),TEXT("ordinary attack clears heavy continuation"));
    Check(BeginLocal(false,true).ZhenTingForward.IsNearlyZero(),TEXT("sprint attack cannot trigger continuation"));
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("checks"),Rows);Report->SetNumberField(TEXT("failures"),Failures);
    Report->SetBoolField(TEXT("user_profile_modified"),false);Report->SetBoolField(TEXT("visual_tested"),false);
    FString Out=FPaths::ProjectSavedDir()/TEXT("ZhenTingAudit.json");FParse::Value(*Params,TEXT("Out="),Out);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*Out);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
