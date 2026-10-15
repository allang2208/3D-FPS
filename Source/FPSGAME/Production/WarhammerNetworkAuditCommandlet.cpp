#include "WarhammerNetworkAuditCommandlet.h"
#include "WarhammerModificationAuditCommandlet.h"
#include "ProductionToolComponent.h"
#include "WarhammerGuardMotion.h"
#include "WarhammerCombat.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Movement/PlayerGuardBreakComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Characters/FPSPlayerBodyTypes.h"
#include "Animation/AnimSequence.h"
#include "Components/SceneComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/DamageType.h"
#include "TimerManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"

int32 UWarhammerNetworkAuditCommandlet::Main(const FString& Params)
{
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_Hammer_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("WarhammerNetworkAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("WarhammerNetworkAuditWorld"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Check=[&](bool OK,const FString& Name)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("HAMMER_NETWORK %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name);
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.Stamina=100;Seed.bSprintExhausted=false;Seed.SwordUppercutCooldown=Seed.WhirlwindCooldown=0.f;
    for(auto& Entry:Seed.Skills)Entry.Value.Level=1;
    auto Hammer=Host->CreateItem(TEXT("ue_steel_warhammer"));Hammer.Place=1;Hammer.Cell=6;Seed.Items={Hammer};
    auto* Shadow=Host->CreateShadowModel(Seed);
    auto* PC=World->SpawnActor<AWarhammerAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);
    PS->SetOwner(PC);PS->ShadowModel=Shadow;PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    Pawn->NetShadowProfile=Shadow;Shadow->AttachPawn(Pawn);
    auto* Guard=Pawn->FindComponentByClass<URuneSwordComponent>();Guard->Character=Pawn;
    auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool->Character=Pawn;
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health->Health=Health->MaxHealth;
    auto* Attacker=World->SpawnActor<AActor>();auto* AttackerRoot=NewObject<USceneComponent>(Attacker);
    Attacker->AddInstanceComponent(AttackerRoot);Attacker->SetRootComponent(AttackerRoot);AttackerRoot->RegisterComponent();
    Attacker->SetActorLocation(Pawn->GetActorLocation()+FVector(200,0,0));
    uint32 Serial=0;
    const auto Reset=[&]()
    {
        if(auto* Broken=Pawn->FindComponentByClass<UPlayerGuardBreakComponent>())Broken->ClearTransient();
        Tool->CancelUse();Shadow->AdoptNetMirror(Seed);
        Guard->InstanceId.Reset();Guard->RefreshToolGuardEquipment(Shadow);
        Tool->Kind=TEXT("warhammer");Tool->EquippedId=Hammer.InstanceId;
        Tool->BluntServerReadyAt=0.;PS->QuickCombatUntil=0.;PS->QuickCombatTargets.Reset();
    };
    const auto Raise=[&](){Guard->ServerSetSwordGuard_Implementation(Hammer.InstanceId,true,++Serial);};
    Reset();
    Check(Pawn->HasAuthority()&&!Pawn->IsLocallyControlled()&&ColdSteelAuthority::ForPawn(Pawn)==Shadow,TEXT("guest authority resolves own shadow"));
    const auto Stats=ColdSteelTool::Evaluate(Hammer,Shadow);
    Check(FMath::IsNearlyEqual(WarhammerCombat::Damage(Stats.Damage,Shadow,false,false,2.5f,0).Total(),Stats.Damage.Total())&&
        FMath::IsNearlyEqual(WarhammerCombat::Damage(Stats.Damage,Shadow,false,false,2.5f,1).Total(),Stats.Damage.Total()),
        TEXT("first two ordinary stages retain base damage"));
    Check(FMath::IsNearlyEqual(WarhammerCombat::Damage(Stats.Damage,Shadow,false,false,2.5f,2).Total(),Stats.Damage.Total()*1.25),
        TEXT("third ordinary stage retains 1.25 damage"));
    const double Sprint=FMath::FloorToDouble(Stats.Damage.Total()*Shadow->DashAttackStats().DamageMultiplier);
    Check(FMath::IsNearlyEqual(WarhammerCombat::Damage(Stats.Damage,Shadow,true,true,2.5f,2).Total(),Sprint),
        TEXT("sprint slam uses dash damage without heavy or third-stage multiplier"));
    const float HostStamina=Host->Stamina();Raise();
    Check(Guard->IsGuarding(),TEXT("remote hammer guard accepted"));
    const float Started=Guard->GuardStartedAt;
    Guard->ServerSetSwordGuard_Implementation(Hammer.InstanceId,true,Serial);
    Check(Guard->GuardStartedAt==Started,TEXT("duplicate raise does not refresh parry window"));
    Guard->GuardStartedAt=-10.;
    const float Reduced=Guard->ResolveGuardDamage(100.f,GetDefault<UDamageType>(),nullptr,nullptr);
    Check(FMath::IsNearlyEqual(Reduced,50.f)&&FMath::IsNearlyEqual(Shadow->Stamina(),80.f),TEXT("guest block halves damage and spends 20 stamina once"));
    Check(Host->Stamina()==HostStamina,TEXT("guest block leaves host stamina untouched"));
    Reset();Raise();
    Check(Guard->ResolveGuardDamage(100.f,GetDefault<UDamageType>(),nullptr,Attacker)==0.f&&Shadow->Stamina()==100.f,
        TEXT("front parry prevents damage without block cost"));
    Guard->ServerSetSwordGuard_Implementation(TEXT("unequipped-weapon"),true,Serial+1);
    Check(Guard->ServerGuardIntentSerial==Serial,TEXT("wrong weapon cannot supersede current guard intent"));
    Guard->ServerSetSwordGuard_Implementation(Hammer.InstanceId,false,Serial);
    Guard->ServerSetSwordGuard_Implementation(Hammer.InstanceId,true,Serial);
    Check(!Guard->IsGuarding(),TEXT("old raise cannot reopen released intent"));
    const uint32 Old=Serial;Raise();Guard->ServerSetSwordGuard_Implementation(Hammer.InstanceId,false,Old);
    Check(Guard->IsGuarding(),TEXT("old release cannot lower newer guard"));

    Reset();Raise();const float Before=Shadow->Stamina();
    Tool->ServerBeginBluntCharge_Implementation(40);
    Check(!Tool->bBluntServerCharging&&Shadow->Stamina()==Before,TEXT("guard excludes authoritative heavy charge"));
    Tool->ServerBeginBluntAttack_Implementation(41,false,false);
    Check(Shadow->Stamina()==Before&&!World->GetTimerManager().IsTimerActive(Tool->BluntContactTimer),TEXT("guard excludes authoritative ordinary attack"));
    Tool->ServerBeginBluntUppercut_Implementation(42);
    Check(!Tool->bBluntUppercut&&Shadow->Stamina()==Before,TEXT("guard excludes authoritative uppercut"));
    Tool->ServerBeginBluntWhirlwind_Implementation(43);
    Check(!Tool->bBluntWhirlwind&&Shadow->Stamina()==Before,TEXT("guard excludes authoritative whirlwind"));
    Reset();Tool->bBluntServerCharging=true;Raise();
    Check(!Guard->IsGuarding(),TEXT("heavy charge excludes server guard"));
    Reset();Tool->bBluntUppercut=true;Raise();
    Check(!Guard->IsGuarding(),TEXT("uppercut excludes server guard"));
    Tool->bBluntUppercut=false;Reset();Tool->bBluntWhirlwind=true;Raise();
    Check(!Guard->IsGuarding(),TEXT("whirlwind excludes server guard"));
    Tool->bBluntWhirlwind=false;Reset();Tool->ServerBeginBluntAttack_Implementation(44,false,false);Raise();
    Check(!Guard->IsGuarding()&&Tool->HasAuthorityAttackInFlight(),TEXT("ordinary attack and recovery exclude server guard"));
    Tool->ServerCancelBluntAttack_Implementation(44);Raise();
    Check(Guard->IsGuarding(),TEXT("cancelled attack releases the guard gate"));

    Reset();Raise();Guard->GuardIntentSerial=Serial;
    Guard->GuardPoseTime=WarhammerGuard::EnterSeconds;Guard->ToolGuardClip=TEXT("GuardHold");
    Guard->ReceiveGuardResult(Hammer.InstanceId,3,0.f,World->GetTimeSeconds(),Serial-1);
    Check(Guard->IsGuarding(),TEXT("late rejected old intent cannot cancel new guard"));
    Guard->ReceiveGuardResult(Hammer.InstanceId,0,20.f,World->GetTimeSeconds(),Serial-1);
    Check(Shadow->Stamina()==80.f&&!Guard->bGuardReacting,TEXT("late accepted block still spends cost without hijacking new pose"));
    Guard->ReceiveGuardResult(Hammer.InstanceId,0,0.f,World->GetTimeSeconds(),Serial);
    Check(Guard->bGuardReacting&&Guard->ToolGuardClip==TEXT("GuardHit"),TEXT("current block receipt starts hammer hit response"));
    Guard->ReleaseGuard();Guard->GuardFeedback(false);
    Check(!Guard->bGuardReacting&&Guard->ToolGuardClip==TEXT("GuardExit"),TEXT("late impact cannot replace guard exit with hold"));
    Guard->bGuardBreakPose=true;Guard->ToolGuardClip=TEXT("GuardBreak");Guard->ToolGuardAge=.4f;
    Guard->ReceiveGuardResult(Hammer.InstanceId,2,0.f,World->GetTimeSeconds(),Serial);
    Check(Guard->ToolGuardAge==.4f&&Guard->bGuardBreakPose,TEXT("break receipt does not restart replicated break animation"));

    Reset();Raise();PS->ServerQuickCombat_Implementation(1,Pawn,.72f,false);
    Check(PS->IsQuickCombatExecuting(Pawn)&&!Guard->IsGuarding(),TEXT("quick melee priority clears authoritative guard"));
    Check(Host->Stamina()==HostStamina&&Guard->ToolGuardInstance==Hammer.InstanceId,
        TEXT("guest quick interruption preserves host resources and guest equipment"));
    Raise();Check(!Guard->IsGuarding(),TEXT("quick melee excludes server guard during action"));
    PS->ServerQuickCombat_Implementation(1,Pawn,0.f,true);Raise();
    Check(Guard->IsGuarding(),TEXT("guard resumes after quick melee completion"));
    Reset();Tool->ServerBeginBluntAttack_Implementation(45,false,false);PS->ServerQuickCombat_Implementation(2,Pawn,.72f,false);
    Check(PS->IsQuickCombatExecuting(Pawn)&&!World->GetTimerManager().IsTimerActive(Tool->BluntContactTimer),
        TEXT("quick melee cancels prior authoritative hammer contact"));
    PS->ServerQuickCombat_Implementation(2,Pawn,0.f,true);
    Reset();auto Low=Seed;Low.Stamina=5.f;Shadow->AdoptNetMirror(Low);Raise();Guard->GuardStartedAt=-10.;
    Guard->ResolveGuardDamage(100.f,GetDefault<UDamageType>(),nullptr,nullptr);
    auto* Broken=Pawn->FindComponentByClass<UPlayerGuardBreakComponent>();
    Check(Broken&&Broken->IsActive()&&Shadow->Stamina()==0.f&&!Guard->IsGuarding(),TEXT("insufficient guest stamina causes independent guard break"));
    Check(PC->IsMoveInputIgnored()&&PC->IsLookInputIgnored(),TEXT("authoritative break locks movement and look"));
    Shadow->AdoptNetMirror(Seed);PS->ServerQuickCombat_Implementation(3,Pawn,.72f,false);
    Check(!PS->IsQuickCombatExecuting(Pawn)&&Shadow->Stamina()==100.f,TEXT("quick melee cannot bypass guard break lock"));
    Raise();Check(!Guard->IsGuarding(),TEXT("guard cannot restart during break lock"));
    if(Broken)Broken->ClearTransient();Raise();
    Check(Guard->IsGuarding()&&!PC->IsMoveInputIgnored()&&!PC->IsLookInputIgnored(),TEXT("break cleanup restores input and guard"));

    // Baseline sword follows the same shared resolver after the hammer changes.
    Reset();auto SwordSeed=Seed;auto Sword=Host->CreateItem(TEXT("ue_rune_sword"));Sword.Place=1;Sword.Cell=6;SwordSeed.Items={Sword};
    Shadow->AdoptNetMirror(SwordSeed);Guard->RefreshToolGuardEquipment(Shadow);Guard->InstanceId=Sword.InstanceId;
    Guard->MeleeModifiers=ColdSteelMelee::Evaluate(Sword,Shadow).Modifiers;Tool->Kind.Reset();Tool->EquippedId.Reset();
    Guard->ServerSetSwordGuard_Implementation(Sword.InstanceId,true,++Serial);Guard->GuardStartedAt=-10.;
    Check(Guard->ResolveGuardDamage(100.f,GetDefault<UDamageType>(),nullptr,nullptr)==50.f&&Shadow->Stamina()==80.f,
        TEXT("shared sword normal block remains unchanged"));
    Reset();Raise();auto Empty=Seed;Empty.Items.Reset();Shadow->AdoptNetMirror(Empty);Guard->TickNetworkGuard();
    Check(!Guard->IsGuarding(),TEXT("authoritative equipment change cancels held guard"));
    Reset();Raise();Health->Health=0.f;Guard->TickNetworkGuard();
    Check(!Guard->IsGuarding(),TEXT("death clears authoritative guard"));Health->Health=Health->MaxHealth;

    USkeleton* Skeleton=nullptr;const float Durations[]={.22f,1.6f,.30f,1.5f,.25f};int32 Index=0;
    for(const TCHAR* Name:WarhammerGuard::Clips)
    {
        auto* Clip=LoadObject<UAnimSequence>(nullptr,*WarhammerGuard::ClipPath(Name));
        Check(Clip&&FMath::IsNearlyEqual(Clip->GetPlayLength(),Durations[Index],.005f),FString(TEXT("saved guard clip and duration "))+Name);
        if(Clip){if(!Skeleton)Skeleton=Clip->GetSkeleton();Check(Clip->GetSkeleton()==Skeleton,FString(TEXT("shared native skeleton "))+Name);}
        ++Index;
    }
    for(const auto Action:{EFPSBodyAction::Guard,EFPSBodyAction::GuardHit,EFPSBodyAction::GuardBreak})
    {
        FFPSBodyState In;In.Family=TEXT("Tool");In.ActionVariant=TEXT("WarhammerGuard");In.Action=Action;
        In.Weapon=TEXT("pickaxe");In.WeaponInstance=Hammer.InstanceId;In.bHasActionProgress=true;In.ActionProgress=.4f;In.ActionWeight=.6f;
        TArray<uint8> Bytes;
        {FMemoryWriter Writer(Bytes);FObjectAndNameAsStringProxyArchive Ar(Writer,false);FFPSBodyState::StaticStruct()->SerializeItem(Ar,&In,nullptr);}
        FFPSBodyState Out;
        {FMemoryReader Reader(Bytes);FObjectAndNameAsStringProxyArchive Ar(Reader,true);FFPSBodyState::StaticStruct()->SerializeItem(Ar,&Out,nullptr);}
        Check(Out.Action==In.Action&&Out.ActionVariant==In.ActionVariant&&Out.WeaponInstance==In.WeaponInstance&&Out.ActionWeight==.6f,
            FString::Printf(TEXT("observer guard state serialization %d"),int32(Action)));
    }
    Tool->CancelUse();Guard->ClearGuard();
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("checks"),Rows);Report->SetNumberField(TEXT("count"),Rows.Num());
    Report->SetNumberField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("authority_runtime_executed"),true);
    Report->SetBoolField(TEXT("real_network_transport_tested"),false);Report->SetBoolField(TEXT("user_profile_modified"),false);
    FString Out=FPaths::ProjectSavedDir()/TEXT("WarhammerNetworkAudit.json");FParse::Value(*Params,TEXT("Out="),Out);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*Out);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    UE_LOG(LogTemp,Display,TEXT("HAMMER_NETWORK_DONE checks=%d failures=%d"),Rows.Num(),Failures);return Failures?1:0;
}
