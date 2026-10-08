#include "RuneSwordAuditCommandlet.h"
#include "JingangRuneComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

int32 URuneSwordAuditCommandlet::AuditXuanChiRunes()
{
    FString Report;int32 Checks=0,Failures=0;
    auto Check=[&](bool Passed,const TCHAR* Label)
    {
        ++Checks;if(!Passed)++Failures;
        const FString Line=FString::Printf(TEXT("XUANCHI_RUNE_AUDIT %s %s"),Passed?TEXT("PASS"):TEXT("FAIL"),Label);
        Report+=Line+TEXT("\n");UE_LOG(LogTemp,Display,TEXT("%s"),*Line);
    };
    FString Text;TSharedPtr<FJsonObject> Catalog,Stats;
    if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/melee-gunsmith.json")))
        &&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Catalog))
        for(const auto& Column:Catalog->GetArrayField(TEXT("columns")))
            for(const auto& Option:Column->AsObject()->GetArrayField(TEXT("options")))
                if(Option->AsObject()->GetStringField(TEXT("id"))==TEXT("jingang_rune"))
                    Stats=Option->AsObject()->GetObjectField(TEXT("stats"));
    if(!Stats){UE_LOG(LogTemp,Error,TEXT("XUANCHI_RUNE_AUDIT missing installed rune stats"));return 2;}

    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("XuanChiRuneAudit"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!World)return 2;
    // No GameInstance initialization, BeginPlay, player save load, profile save or HUD.
    auto* GI=NewObject<UGameInstance>();World->SetGameInstance(GI);
    auto* SeedModel=NewObject<UColdSteelStatusModel>(GI);
    FColdSteelProfile State;FColdSteelItem Sword;
    Sword.InstanceId=TEXT("xuanchi-isolated-audit");Sword.Definition=TEXT("ue_xuanchi_zhenyue");
    Sword.Place=1;Sword.Cell=State.ActiveWeaponSlot;Sword.Data=TEXT("{\"gunsmith_parts\":{\"blade_2\":\"jingang_rune\"}}");
    State.Items.Add(Sword);
    auto* Model=SeedModel->CreateShadowModel(State);
    auto* Pawn=World->SpawnActor<APawn>();auto* Target=World->SpawnActor<APawn>();
    auto* Health=NewObject<UFPSCombatHealthComponent>(Pawn);Pawn->AddInstanceComponent(Health);Health->RegisterComponent();
    auto* Combat=NewObject<UMonsterCombatComponent>(Target);Target->AddInstanceComponent(Combat);Combat->RegisterComponent();
    auto* Rune=NewObject<UJingangRuneComponent>(Pawn);Pawn->AddInstanceComponent(Rune);Rune->RegisterComponent();
    // Inject only the equipped binding that normally requires initialized GI subsystems.
    // All thresholds, multipliers, timers and healing below execute production methods.
    Rune->Profile=Model;Rune->EquippedInstance=Sword.InstanceId;Rune->EquippedData=Sword.Data;
    Rune->Modifiers.JingangBonus=Stats->GetNumberField(TEXT("jingang_bonus"));
    Rune->Modifiers.JingangHighThreshold=Stats->GetNumberField(TEXT("jingang_high_threshold"));
    Rune->Modifiers.JingangLowThreshold=Stats->GetNumberField(TEXT("jingang_low_threshold"));
    Rune->Modifiers.JingangLeechSeconds=Stats->GetNumberField(TEXT("jingang_leech_seconds"));
    Rune->Modifiers.JingangLeechRatio=Stats->GetNumberField(TEXT("jingang_leech_ratio"));
    Health->MaxHealth=100.f;
    auto Near=[](float A,float B){return FMath::IsNearlyEqual(A,B,.001f);};
    auto At=[&](float HP){Health->Health=HP;Rune->ObserveHealth();};
    At(70.f);
    Check(Rune->State()==EJingangState::High,TEXT("70 percent is high state"));
    Check(Near(Rune->DefenseMultiplier(),1.25f)&&Near(Rune->DamageMultiplier(),1.25f)
        &&Near(Rune->AttackSpeedMultiplier(),1.f)&&Near(Rune->CooldownMultiplier(),1.f),TEXT("high state modifiers"));
    At(69.99f);
    Check(Rune->State()==EJingangState::Middle,TEXT("below 70 percent is middle state"));
    Check(Near(Rune->DefenseMultiplier(),1.25f)&&Near(Rune->DamageMultiplier(),1.f)
        &&Near(Rune->AttackSpeedMultiplier(),1.25f)&&Near(Rune->CooldownMultiplier(),.75f),TEXT("middle state modifiers"));
    At(30.f);Check(Rune->State()==EJingangState::Middle,TEXT("30 percent is middle state"));
    At(29.99f);Check(Rune->State()==EJingangState::Low,TEXT("below 30 percent is low state"));
    Check(Near(Rune->DefenseMultiplier(),1.5f)&&Near(Rune->DamageMultiplier(),1.5f)
        &&Near(Rune->AttackSpeedMultiplier(),1.5f)&&Near(Rune->CooldownMultiplier(),.5f),TEXT("low state doubles all four bonuses"));
    Check(Near(Rune->LeechRemaining(),10.f),TEXT("entering low health grants 10 seconds of leech"));
    At(20.f);Rune->LeechEndsAt=Rune->Clock()+3.;Rune->ConfirmAttack(Target,20.f);
    Check(Near(Health->Health,22.f)&&Near(Rune->LeechRemaining(),10.f),TEXT("authority hit heals 10 percent and refreshes remaining time"));
    Rune->LeechEndsAt=Rune->Clock()+3.;Rune->ConfirmAttack(Target,0.f);
    Check(Near(Health->Health,22.f)&&Near(Rune->LeechRemaining(),3.f),TEXT("zero applied damage neither heals nor refreshes"));
    Target->Tags.Add(TEXT("Friendly"));Rune->ConfirmAttack(Target,20.f);Target->Tags.Remove(TEXT("Friendly"));
    Check(Near(Health->Health,22.f)&&Near(Rune->LeechRemaining(),3.f),TEXT("friendly contact neither heals nor refreshes"));
    At(29.f);Rune->ConfirmAttack(Target,20.f);
    Check(Near(Health->Health,31.f)&&Rune->State()==EJingangState::Middle&&Near(Rune->LeechRemaining(),10.f),
        TEXT("healing across 30 percent retains leech"));
    Rune->LeechEndsAt=Rune->Clock()+3.;Rune->ConfirmAttack(Target,20.f);
    Check(Near(Health->Health,33.f)&&Near(Rune->LeechRemaining(),3.f),TEXT("middle state heals during remaining time without refreshing"));
    At(99.f);Rune->ConfirmAttack(Target,50.f);
    Check(Near(Health->Health,100.f),TEXT("healing is capped at maximum health"));
    At(50.f);Rune->LeechEndsAt=Rune->Clock()-1.;Rune->ConfirmAttack(Target,20.f);
    Check(Near(Health->Health,50.f)&&Near(Rune->LeechRemaining(),0.f),TEXT("expired leech does not heal"));
    At(20.f);Check(Near(Rune->LeechRemaining(),10.f),TEXT("reentering low health grants a fresh duration"));
    auto Switched=State;Switched.ActiveWeaponSlot=7;Model->AdoptNetMirror(Switched);Rune->ObserveHealth();
    Check(Rune->State()==EJingangState::None&&Near(Rune->LeechRemaining(),0.f)
        &&Near(Rune->DefenseMultiplier(),1.f)&&Near(Rune->DamageMultiplier(),1.f)
        &&Near(Rune->AttackSpeedMultiplier(),1.f)&&Near(Rune->CooldownMultiplier(),1.f),TEXT("switching weapon clears all effects"));
    Model->AdoptNetMirror(State);At(20.f);At(0.f);
    Check(Rune->State()==EJingangState::None&&Near(Rune->LeechRemaining(),0.f),TEXT("death clears rune effects"));
    const FString Summary=FString::Printf(TEXT("XUANCHI_RUNE_AUDIT checks=%d failures=%d; isolated component test, not network or visual acceptance\n"),Checks,Failures);
    Report+=Summary;UE_LOG(LogTemp,Display,TEXT("%s"),*Summary);
    const FString Directory=FPaths::ProjectSavedDir()/TEXT("XuanChiReview20261006");
    IFileManager::Get().MakeDirectory(*Directory,true);
    FFileHelper::SaveStringToFile(Report,*(Directory/TEXT("rune-audit.txt")));
    World->DestroyWorld(false);
    return Failures?1:0;
}
