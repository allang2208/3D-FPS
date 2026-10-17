#include "SkillNetworkAuditCommandlet.h"
#include "FPSFireMagicComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

int32 USkillNetworkAuditCommandlet::RunFlameArmorAudit(const FString& Params)
{
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_FlameArmor_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("SkillNetworkAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("FlameArmorAuditWorld"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool OK,const TCHAR* Name)
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(R));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("FLAME_ARMOR_AUDIT %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();Seed.DungeonRun={};
    Seed.Hotbar.Init(TEXT(""),4);Seed.HotbarDefinitions.Init(TEXT(""),4);for(auto& B:Seed.QuickBindings)B={};
    for(auto& Skill:Seed.Skills){Skill.Value.Level=1;Skill.Value.Experience=0;}
    Seed.NetworkProfileId=FGuid::NewGuid();auto* Shadow=Host->CreateShadowModel(Seed);
    auto* PC=World->SpawnActor<ASkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);
    PS->SetOwner(PC);PS->ShadowModel=Shadow;PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    Pawn->NetShadowProfile=Shadow;Shadow->CurrentPawn=Pawn;Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health->Health=Health->MaxHealth;
    auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>();auto* Status=UStatusEffectsComponent::GetOrCreate(Pawn);
    const auto HasCard=[&](){return Status->Snapshot().ContainsByPredicate([](const auto& V){return V.Type==TEXT("flameArmor")&&V.Remaining>0.f;});};
    auto Spell=Shadow->FireMagicStats(TEXT("flameArmor"));Spell.Duration=10.f;
    FColdSteelNetCastRequest Req;Req.SkillId=TEXT("flameArmor");
    Check(!Fire->NetRelease(Pawn,Req,Shadow,Spell),TEXT("unidentified release rejected"));
    Req.CastId=11;Check(Fire->NetRelease(Pawn,Req,Shadow,Spell)&&Fire->NetArmor.bActive&&Fire->NetArmor.CastId==11&&HasCard(),TEXT("guest authority release publishes identity and card"));
    Fire->ArmorRewards.Hits=1;const int32 HostXP=Host->FireMagicProgress(TEXT("flameArmor")).Experience;
    Pawn->NetShadowProfile=nullptr;PS->ShadowModel=nullptr;
    Fire->FinishFireMagicForRemoval();const int32 GuestXP=Shadow->FireMagicProgress(TEXT("flameArmor")).Experience;Fire->FinishFireMagicForRemoval();
    Check(GuestXP>0&&Shadow->FireMagicProgress(TEXT("flameArmor")).Experience==GuestXP&&Host->FireMagicProgress(TEXT("flameArmor")).Experience==HostXP,
        TEXT("detached guest removal settles original reward owner exactly once"));
    Check(!Fire->NetArmor.bActive&&Fire->ArmorTime==0&&!HasCard(),TEXT("removal clears replicated state and card"));
    Pawn->NetShadowProfile=Shadow;PS->ShadowModel=Shadow;
    Req.CastId=12;Fire->NetRelease(Pawn,Req,Shadow,Spell);Fire->ArmorRewards.Hits=1;const uint32 Serial=Fire->NetArmor.Serial;
    Req.CastId=13;Fire->NetRelease(Pawn,Req,Shadow,Spell);
    Check(Fire->NetArmor.Serial==Serial+1&&Fire->NetArmor.CastId==13&&Fire->ArmorRewards.Hits==0&&Shadow->FireMagicProgress(TEXT("flameArmor")).Experience>GuestXP,
        TEXT("recast settles prior batch and replaces state"));
    const int32 BeforeDeath=Shadow->FireMagicProgress(TEXT("flameArmor")).Experience;Fire->ArmorRewards.Hits=1;Health->Health=0;Fire->FinishFireMagicForRemoval();
    Check(Shadow->FireMagicProgress(TEXT("flameArmor")).Experience==BeforeDeath&&!Fire->NetArmor.bActive,TEXT("death clears armor without training dead player"));
    Health->Health=Health->MaxHealth;

    // Exercise production reservation matching, without a socket transport here.
    PS->PendingCastSkill=TEXT("flameArmor");PS->PendingIdentifiedCastId=100;PS->PendingCastPawn=Pawn;PS->PendingFireMagicStats=Spell;
    Req.CastId=99;Req.Phase=2;PS->ExecuteCastRequest(Req);
    Check(PS->PendingCastSkill==TEXT("flameArmor")&&PS->PendingIdentifiedCastId==100,TEXT("stale cancel preserves newer reservation"));
    Req.Phase=1;PS->ExecuteCastRequest(Req);
    Check(PS->PendingCastSkill==TEXT("flameArmor")&&Fire->ArmorTime==0,TEXT("stale release cannot consume newer reservation"));
    Req.CastId=100;PS->ExecuteCastRequest(Req);
    Check(PS->PendingCastSkill.IsNone()&&Fire->NetArmor.CastId==100&&Fire->NetArmor.bActive,TEXT("matching release consumes reservation"));
    Fire->FinishFireMagicForRemoval();

    // Client-role OnRep / receipt permutations. No render or network claims.
    Pawn->SwapRoles();Check(!Pawn->HasAuthority(),TEXT("client-role fixture"));
    Fire->NetArmor.Cast=Spell;Fire->NetArmor.StartedAt=World->GetTimeSeconds()-3.;Fire->NetArmor.bActive=true;Fire->NetArmor.Serial=20;Fire->NetArmor.CastId=200;
    Fire->OnRep_Armor();
    Check(FMath::IsNearlyEqual(Fire->ArmorTime,7.f,.01f)&&HasCard(),TEXT("late replica reconstructs remaining duration and status card"));
    Fire->CastSnapshot=Spell;Fire->ArmorLocalCastId=201;Fire->StartArmor();
    Fire->NetArmor.bActive=false;Fire->OnRep_Armor();Fire->RefreshArmorVisuals();
    Check(Fire->bArmorAwaitingReplication&&Fire->ArmorTime==10.f&&HasCard(),TEXT("stale inactive state and asset arrival preserve prediction"));
    Fire->NetArmor.bActive=true;Fire->NetArmor.CastId=201;Fire->NetArmor.Serial=21;Fire->NetArmor.StartedAt=World->GetTimeSeconds()-1.;Fire->OnRep_Armor();
    Check(!Fire->bArmorAwaitingReplication&&Fire->ArmorConfirmedCastId==201&&FMath::IsNearlyEqual(Fire->ArmorTime,9.f,.01f)&&HasCard(),TEXT("matching replication confirms and retains status card"));
    Fire->ArmorLocalCastId=202;Fire->StartArmor();Fire->NetArmor.bActive=false;Fire->NetArmor.CastId=201;
    Fire->NetArmorCastResult(1,0,202);Fire->RefreshArmorVisuals();
    Check(Fire->bArmorAwaitingReplication&&Fire->ArmorTime>0,TEXT("success receipt before property keeps prediction"));
    Fire->NetArmorCastResult(1,3,202);
    Check(Fire->bArmorAwaitingReplication&&Fire->ArmorTime>0,TEXT("duplicate rejection cannot undo confirmed release"));
    Fire->ArmorLocalCastId=203;Fire->StartArmor();Fire->NetArmorCastResult(1,3,202);
    Check(Fire->bArmorAwaitingReplication&&Fire->ArmorTime>0,TEXT("old receipt cannot clear successor cast"));
    Fire->NetArmor.bActive=true;Fire->NetArmor.CastId=201;Fire->NetArmor.StartedAt=World->GetTimeSeconds()-4.;
    Host->Current.Mana=50;Host->Current.FlameArmorCooldown=5;Fire->ArmorPendingRefund=10;
    Fire->NetArmorCastResult(1,3,203);const float Refunded=Host->Snapshot().Mana;Fire->NetArmorCastResult(1,3,203);
    Check(FMath::IsNearlyEqual(Refunded,60.f)&&Host->Snapshot().Mana==Refunded&&Host->FireMagicCooldown(TEXT("flameArmor"))==0,
        TEXT("rejected released prediction refunds local payment once"));
    Check(!Fire->bArmorAwaitingReplication&&FMath::IsNearlyEqual(Fire->ArmorTime,6.f,.01f)&&HasCard(),TEXT("rejected refresh restores prior authority buff"));
    Fire->ArmorTime=9.f;Fire->TickArmor(0.f);
    Check(FMath::IsNearlyEqual(Fire->ArmorTime,6.f,.01f),TEXT("confirmed replica follows authoritative clock"));
    Health->Health=0;Fire->OnRep_Armor();Fire->RefreshArmorVisuals();
    Check(Fire->ArmorTime==0&&!HasCard(),TEXT("late replication and asset arrival cannot revive dead player visuals"));
    Health->Health=Health->MaxHealth;Fire->NetArmor.bActive=false;Fire->OnRep_Armor();
    Check(Fire->ArmorTime==0&&!HasCard(),TEXT("inactive replication removes status"));
    auto Root=MakeShared<FJsonObject>();Root->SetNumberField(TEXT("checks"),Rows.Num());Root->SetNumberField(TEXT("failures"),Failures);Root->SetArrayField(TEXT("results"),Rows);
    Root->SetStringField(TEXT("scope"),TEXT("production methods with isolated authority and client-role state; wire checked separately"));
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));FString Path;
    if(!FParse::Value(*Params,TEXT("Output="),Path))Path=FPaths::ProjectSavedDir()/TEXT("FlameArmorNetworkAudit20261017/authority.json");
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);
    Pawn->SwapRoles();GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);return Failures?1:0;
}
