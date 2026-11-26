#include "SkillNetworkAuditCommandlet.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/UppercutStaminaReceipt.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Production/ProductionToolComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "FPSFireMagicComponent.h"
#include "FPSMeteorStrike.h"
#include "SwordUppercutTuning.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/StreamableManager.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

int32 USkillNetworkAuditCommandlet::Main(const FString& Params)
{
    if(FParse::Param(*Params,TEXT("PojunChainPose")))return RunPojunChainPoseAudit();
    if(FParse::Param(*Params,TEXT("SessionSkillsOnly")))return RunSessionSkillsAudit(Params);
    if(FParse::Param(*Params,TEXT("ConversationCombatOnly")))return RunConversationCombatReview(Params);
    if(FParse::Param(*Params,TEXT("LightningHasteVisual")))return CaptureLightningHaste(Params);
    if(FParse::Param(*Params,TEXT("LightningHasteOnly")))return RunLightningHasteAudit(Params);
    if(FParse::Param(*Params,TEXT("MeteorFormulaNetOnly")))return RunMeteorFormulaNetAudit(Params);
    if(FParse::Param(*Params,TEXT("MeteorReadyPreviewOnly")))return RunMeteorReadyPreviewAudit(Params);
    if(FParse::Param(*Params,TEXT("SkillBatch20261020")))return RunSkillBatchReview(Params);
    if(FParse::Param(*Params,TEXT("ZhufengOnly")))return RunZhufengAudit(Params);
    if(FParse::Param(*Params,TEXT("IceArmorOnly")))return RunIceArmorAudit(Params);
    if(FParse::Param(*Params,TEXT("FlameArmorStatsOnly")))return RunFlameArmorStatsAudit(Params);
    if(FParse::Param(*Params,TEXT("FlameArmorOnly")))return RunFlameArmorAudit(Params);
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("SkillNetworkAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("SkillNetworkAuditWorld"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool OK,const FString& Name,const FString& Detail=FString())
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);Row->SetStringField(TEXT("detail"),Detail);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("SKILL_NETWORK_AUDIT %s %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name,*Detail);
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.Hotbar.Init(TEXT(""),4);Seed.HotbarDefinitions.Init(TEXT(""),4);for(auto& B:Seed.QuickBindings)B={};
    Seed.Stamina=150;Seed.bSprintExhausted=false;Seed.SwordUppercutCooldown=0;Seed.UppercutStaminaSpent=0;Seed.DungeonRun={};
    for(auto& Skill:Seed.Skills){Skill.Value.Level=1;Skill.Value.Experience=0;}
    auto SwordItem=Host->CreateItem(TEXT("ue_rune_sword"));SwordItem.Place=1;SwordItem.Cell=6;Seed.Items={SwordItem};
    Seed.NetworkProfileId=FGuid::NewGuid();
    auto* Shadow=Host->CreateShadowModel(Seed);
    auto* PC=World->SpawnActor<ASkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);
    PS->SetOwner(PC);PS->ShadowModel=Shadow;PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    Pawn->NetShadowProfile=Shadow;Shadow->CurrentPawn=Pawn;Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();Sword->Character=Pawn;Sword->InstanceId=SwordItem.InstanceId;
    auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool->Character=Pawn;
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health->Health=Health->MaxHealth;
    auto* Status=UCombatStatusFormula::GetOrAdd(Pawn);
    const auto Base=Shadow->Snapshot();
    const auto Reset=[&]()
    {
        PS->SettleSwordUppercut();Shadow->Current=Base;Shadow->CurrentPawn=Pawn;
        Status->TickComponent(UCombatStatusFormula::ExhaustionDuration,LEVELTICK_All,&Status->PrimaryComponentTick);
        Sword->bCharging=false;Tool->bBluntServerCharging=false;
    };
    Check(Pawn->HasAuthority()&&!Pawn->IsLocallyControlled()&&Pawn->IsPlayerControlled(),TEXT("remote authority fixture identity"));

    const float Cost=Shadow->SwordUppercutStaminaCost();
    PS->ServerSwordUppercut_Implementation(1,Pawn,SwordItem.InstanceId,false);
    Check(PS->UppercutActiveSequence==1&&FMath::IsNearlyEqual(Shadow->Stamina(),Base.Stamina-Cost)&&Shadow->SwordUppercutCooldown()>0,
        TEXT("sword uppercut server commits cost and cooldown"));
    PS->ServerSwordUppercut_Implementation(1,Pawn,SwordItem.InstanceId,false);
    Check(FMath::IsNearlyEqual(Shadow->Stamina(),Base.Stamina-Cost),TEXT("duplicate release costs once"));
    auto* Target=World->SpawnActor<ANurseZombie>(FVector(120,0,560),FRotator::ZeroRotator);Target->Health=Target->MaxHealth=100000;
    Target->GetCharacterMovement()->Activate(true);Target->Combat->ConfigureToughnessBar(FMonsterToughnessBarTuning());
    FColdSteelNetHitReport Hit;Hit.Target=Target;Hit.ItemDefinition=SwordItem.Definition;Hit.AttackMeta=SwordUppercut::AttackMeta;
    Hit.UppercutSerial=1;Hit.Flags=1<<3;Hit.AimOrigin=Pawn->GetPawnViewLocation();Hit.ImpactPoint=Target->GetActorLocation();
    Hit.Direction=FVector::ForwardVector;Hit.HitNormal=-FVector::ForwardVector;Hit.ClientFireTime=World->GetTimeSeconds();
    const float BeforeHP=Target->Health;PS->ServerReportHit_Implementation(Hit);
    Check(Target->Health<BeforeHP&&Target->GetCharacterMovement()->HandlePendingLaunch(),TEXT("committed remote sword hit damages and launches"));
    const float AfterHP=Target->Health;PS->ServerReportHit_Implementation(Hit);
    Check(Target->Health==AfterHP,TEXT("duplicate uppercut contact cannot damage twice"));
    PS->ServerSwordUppercut_Implementation(1,Pawn,SwordItem.InstanceId,true);
    Check(Shadow->MasteryProgress(TEXT("swordUppercut")).Experience==Shadow->MasteryDefinition(TEXT("swordUppercut")).HitExperience,
        TEXT("one server hit training batch"));
    const int32 XP=Shadow->MasteryProgress(TEXT("swordUppercut")).Experience;PS->SettleSwordUppercut();
    Check(Shadow->MasteryProgress(TEXT("swordUppercut")).Experience==XP,TEXT("duplicate finish does not train again"));
    PS->ServerSwordUppercut_Implementation(2,Pawn,SwordItem.InstanceId,false);
    Check(!PS->UppercutActiveSequence&&FMath::IsNearlyEqual(Shadow->Stamina(),Base.Stamina-Cost),TEXT("cooldown rejects another release without payment"));
    const float CD=Shadow->SwordUppercutCooldown();PS->ServerMartialCooldowns_Implementation(Pawn,999,0,0,0,0,World->GetTimeSeconds());
    Check(Shadow->SwordUppercutCooldown()==CD,TEXT("owner cooldown publication cannot erase authority uppercut cooldown"));
    Reset();Shadow->Current.Stamina=Cost-1;
    PS->ServerSwordUppercut_Implementation(3,Pawn,SwordItem.InstanceId,false);
    Check(!PS->UppercutActiveSequence&&Shadow->Stamina()==Cost-1,TEXT("insufficient stamina rejects before hit"));
    Reset();PS->ServerSwordUppercut_Implementation(4,Pawn,SwordItem.InstanceId,false);PS->UppercutUntil=-1;PS->TickSwordUppercut();
    Check(!PS->UppercutActiveSequence&&Shadow->MasteryProgress(TEXT("swordUppercut")).Experience==1,TEXT("missing finish settles release training on expiry"));
    Hit.UppercutSerial=4;PS->ServerReportHit_Implementation(Hit);
    Check(Target->Health==AfterHP,TEXT("expired uppercut hit rejected"));Target->Destroy();
    FColdSteelProfile Old=Base;UppercutStaminaReceipt::Merge(Old,Cost);UppercutStaminaReceipt::Merge(Old,Cost);
    Check(Old.Stamina==Base.Stamina-Cost&&Old.UppercutStaminaSpent==Cost,TEXT("old upload plus repeated receipt charges once"));
    auto Mirror=Old;UppercutStaminaReceipt::Merge(Mirror,Cost);
    Check(Mirror.Stamina==Old.Stamina,TEXT("mirror arriving before receipt cannot double charge"));

    for(const bool Hammer:{false,true})
    {
        Reset();
        if(Hammer){auto Item=Host->CreateItem(TEXT("ue_steel_warhammer"));Item.Place=1;Item.Cell=6;Shadow->Current.Items={Item};Tool->ServerBeginBluntCharge_Implementation(10,Item.InstanceId);}
        else Sword->ServerSetSwordHeavyCharge_Implementation(SwordItem.InstanceId,true,false,FMath::Max(.001,World->GetTimeSeconds()),0);
        const FString Name=Hammer?TEXT("hammer"):TEXT("sword");
        Check(Hammer?Tool->IsHeavyCharging():Sword->IsHeavyCharging(),Name+TEXT(" remote charging begins"));
        Shadow->Current.Stamina=5; // Drain after a valid start, not an unaffordable initial attack.
        Shadow->TickRuntime(1.f,Pawn);
        Check(FMath::IsNearlyEqual(Shadow->Stamina(),3.f),Name+TEXT(" charge consumes two stamina per second"));
        Shadow->TickRuntime(1.f,Pawn);Shadow->TickRuntime(1.f,Pawn);
        Check(Shadow->Stamina()==0&&!(Hammer?Tool->IsHeavyCharging():Sword->IsHeavyCharging())&&Status->ExhaustionRemaining()>4.9f,
            Name+TEXT(" zero stamina cancels charging and applies exhaustion"));
        Shadow->Current.Stamina=100;Shadow->Current.bSprintExhausted=false;
        auto* Move=CastChecked<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
        Move->UpdateFromCompressedFlags(FSavedMove_Character::FLAG_Custom_0);
        Check(!Move->bWantsToSprint&&!Shadow->CanSprint()&&FMath::IsNearlyEqual(Status->MovementMultiplier(),.5f),Name+TEXT(" recovered stamina cannot bypass timed sprint lock"));
        Status->TickComponent(4.9f,LEVELTICK_All,&Status->PrimaryComponentTick);Move->UpdateFromCompressedFlags(FSavedMove_Character::FLAG_Custom_0);
        Check(!Move->bWantsToSprint,Name+TEXT(" still locked before five seconds"));
        Status->TickComponent(.2f,LEVELTICK_All,&Status->PrimaryComponentTick);Move->UpdateFromCompressedFlags(FSavedMove_Character::FLAG_Custom_0);
        Check(Move->bWantsToSprint&&Shadow->CanSprint(),Name+TEXT(" sprint returns after five seconds"));
    }

    Reset();Shadow->Current.Mana=10000;
    Check(!Shadow->BeginBlizzardCast(Shadow->BlizzardStats()),TEXT("authority blizzard rejects no staff"));
    Check(!Shadow->BeginFireMagicCast(Shadow->FireMagicStats(TEXT("meteor"))),TEXT("authority meteor rejects no staff"));
    Check(!Shadow->BeginFireMagicCast(Shadow->FireMagicStats(TEXT("dragonBreath"))),TEXT("authority dragon rejects no staff"));
    auto Staff=Host->CreateItem(TEXT("ue_apprentice_staff"));Staff.Place=1;Staff.Cell=6;Shadow->Current.Items={Staff};
    auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>();
    const auto Dragon=Shadow->FireMagicStats(TEXT("dragonBreath"));
    const bool Prepared=Shadow->BeginFireMagicCast(Dragon);
    FColdSteelNetCastRequest Request;Request.SkillId=TEXT("dragonBreath");Request.CastId=42;Request.AimPoint=FVector(60,0,0);
    Check(Prepared&&Fire->NetRelease(Pawn,Request,Shadow,Dragon)&&Fire->IsDragonBreathActive(),TEXT("remote dragon starts without local GPU visuals"));
    Fire->DragonRewards.Hits=1;const int32 DragonHostXP=Host->FireMagicProgress(TEXT("dragonBreath")).Experience;
    Fire->NetStopDragonBreath(41);Check(Fire->IsDragonBreathActive(),TEXT("stale dragon stop cannot cancel current cast"));
    Fire->NetStopDragonBreath(42);const int32 DragonXP=Shadow->FireMagicProgress(TEXT("dragonBreath")).Experience;Fire->NetStopDragonBreath(42);
    Check(!Fire->IsDragonBreathActive()&&DragonXP>0&&Shadow->FireMagicProgress(TEXT("dragonBreath")).Experience==DragonXP
        &&Host->FireMagicProgress(TEXT("dragonBreath")).Experience==DragonHostXP,TEXT("dragon stop trains guest once and never host"));

    const auto Meteor=Shadow->FireMagicStats(TEXT("meteor"));
    auto* Strike=World->SpawnActor<AFPSMeteorStrike>();
    const FVector Point(2000,0,0);Check(Strike->InitializeStrike(Pawn,Meteor,Point,FVector::UpVector),TEXT("meteor gameplay initializes independently of FX"));
    if(Strike->VisualLoad)Strike->VisualLoad->CancelHandle();Strike->VisualLoad.Reset();
    Strike->NetStartedAt=Strike->ServerClock()-Meteor.FallSeconds-2.;Strike->Tick(.1f);
    Check(Strike->bImpacted&&FMath::IsNearlyEqual(Strike->LavaAge,2.f,.01f)&&Strike->Start.Equals(Point+FVector(0,0,1320)),TEXT("meteor server clock advances directly to correct field age"));
    Strike->Rewards.Hits=1;
    const int32 HostMeteorXP=Host->FireMagicProgress(TEXT("meteor")).Experience;
    Pawn->NetShadowProfile=nullptr;PS->ShadowModel=nullptr;Strike->FinishForRemoval();Strike->FinishForRemoval();
    Check(Strike->bSettled&&Shadow->FireMagicProgress(TEXT("meteor")).Experience>0&&Host->FireMagicProgress(TEXT("meteor")).Experience==HostMeteorXP,
        TEXT("meteor removal retains original guest reward owner and settles once"));
    Pawn->NetShadowProfile=Shadow;PS->ShadowModel=Shadow;
    for(int32 Frame=0;Frame<100;++Frame)World->Tick(LEVELTICK_TimeOnly,.1f);
    auto* Replica=World->SpawnActor<AFPSMeteorStrike>();Replica->SwapRoles();
    Replica->NetCaster=Pawn;Replica->NetCast=Meteor;Replica->NetDestination=Point;Replica->NetNormal=FVector::UpVector;
    Replica->NetStartedAt=Replica->ServerClock()-Meteor.FallSeconds-2.;Replica->Tick(.1f);
    Check(!Replica->HasAuthority()&&Replica->bNetInit&&Replica->bImpacted&&FMath::IsNearlyEqual(Replica->LavaAge,2.f,.01f)&&Replica->Fragments.IsEmpty(),TEXT("late meteor replica resumes field without old impact burst"),
        FString::Printf(TEXT("role=%d init=%d impact=%d started=%.3f age=%.3f fieldAge=%.3f"),int32(Replica->GetLocalRole()),Replica->bNetInit,Replica->bImpacted,Replica->NetStartedAt,Replica->Age,Replica->LavaAge));
    Replica->Destroy();
    Shadow->Current.Items={SwordItem};Request.SkillId=TEXT("meteor");Request.AimNormal=FVector::UpVector;
    Check(!Fire->NetRelease(Pawn,Request,Shadow,Meteor),TEXT("switching off staff between prepare and release rejects meteor"));

    auto HammerItem=Host->CreateItem(TEXT("ue_steel_warhammer"));
    const auto SwordStats=ColdSteelMelee::Evaluate(SwordItem,Shadow),HammerStats=ColdSteelMelee::Evaluate(HammerItem,Shadow);
    Check(FMath::IsNearlyEqual(SwordStats.SlashReach,HammerStats.SlashReach,.01),TEXT("hammer and unextended sword share normal reach"));
    Check(FMath::IsNearlyEqual(HammerStats.AttackSeconds,SwordStats.AttackSeconds*1.15,.001),TEXT("hammer normal base interval is fifteen percent longer"));
    auto WheelSeed=Seed;WheelSeed.Items={Staff};Host->CommitState(WheelSeed);
    Check(Host->Snapshot().MagicWheelSkills.Num()==10&&Host->BindMagic(0,TEXT("fireball"))&&Host->BindMagic(1,TEXT("meteor")),TEXT("ten-slot wheel accepts learned spells"));
    Check(Host->SelectMagic(0)&&Host->SelectedMagicSkill()==TEXT("fireball"),TEXT("wheel selection routes the requested spell"));
    Host->Current.FireballCooldown=Host->Current.FireballCooldownDuration=7.f;
    Check(Host->MagicCooldownRemaining(Host->SelectedMagicSkill())==7.f,TEXT("staff readout uses the spell cooldown"));
    // The wheel maps an empty sector to INDEX_NONE, like its center.
    Check(Host->Snapshot().MagicWheelSkills[2].IsNone()&&Host->SelectMagic(INDEX_NONE)&&Host->SelectedMagicSkill().IsNone(),TEXT("empty wheel selection restores unselected state"));
    Host->SelectMagic(1);Check(Host->SelectMagic(INDEX_NONE)&&Host->SelectedMagicSkill().IsNone(),TEXT("wheel center clears selection"));
    Host->SelectMagic(1);Check(Host->ClearMagic(1)&&Host->SelectedMagicSkill().IsNone(),TEXT("removing selected registration clears selection"));

    auto Root=MakeShared<FJsonObject>();Root->SetNumberField(TEXT("checks"),Rows.Num());Root->SetNumberField(TEXT("failures"),Failures);Root->SetArrayField(TEXT("results"),Rows);
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    const FString Path=FPaths::ProjectSavedDir()/TEXT("SkillNetworkReview20261015/authority-result.json");IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);return Failures?1:0;
}
