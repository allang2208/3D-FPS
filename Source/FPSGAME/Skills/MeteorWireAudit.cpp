#include "SkillWireAudit.h"
#include "FPSFireMagicComponent.h"
#include "FPSMeteorStrike.h"
#include "PlayerSkillPreparation.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/MonsterAIController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "HAL/PlatformMisc.h"
#include "Serialization/JsonSerializer.h"

namespace MeteorWire
{
const FVector TargetPoint(400,0,0),LatePoint(2500,0,0);
FColdSteelProfile Seed(UColdSteelStatusModel* M)
{
    auto P=M->Snapshot();P.Items.Reset();P.ActiveWeaponSlot=6;P.ActiveProductionTool.Reset();P.DungeonRun={};
    P.MeteorCooldown=P.MeteorCooldownDuration=0;P.NetworkProfileId=FGuid::NewGuid();
    for(auto& S:P.Skills){S.Value.Level=1;S.Value.Experience=0;}
    auto Staff=M->CreateItem(TEXT("ue_apprentice_staff"));Staff.Place=1;Staff.Cell=6;P.Items={Staff};return P;
}
void Save(const TSharedRef<FJsonObject>& Data)
{
    FString Json;FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&Json));
    FString Path;if(FParse::Value(FCommandLine::Get(),TEXT("SkillWireOutput="),Path))FFileHelper::SaveStringToFile(Json,*Path);
    UE_LOG(LogTemp,Display,TEXT("METEOR_WIRE_RESULT %s"),*Json);
}
}

void ASkillWireAuditController::ClientSetupMeteor_Implementation(float Mana,float Cost)
{
    if(!FParse::Param(FCommandLine::Get(),TEXT("MeteorWireAudit"))||HasAuthority()||bSetup)return;
    auto* Controlled=Cast<AFPSGAMECharacter>(GetPawn());auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* PS=GetPlayerState<AColdSteelPlayerState>();if(!Controlled||!M||!PS||PS->GetPawn()!=Controlled||!M->IsAudit())return;
    M->Current=MeteorWire::Seed(M);M->Current.Mana=Mana;M->CurrentPawn=Controlled;
    Controlled->SetActorTickEnabled(false);Controlled->GetCharacterMovement()->SetComponentTickEnabled(false);PS->SetActorTickEnabled(false);
    TArray<FSoftObjectPath> Paths;PlayerSkillAssets::Gather(TEXT("meteor"),M->Snapshot(),Paths);
    const auto Loaded=UAssetManager::GetStreamableManager().RequestSyncLoad(Paths); // Fixture warmup only.
    auto* Fire=Controlled->FindComponentByClass<UFPSFireMagicComponent>();Fire->ResolveMeteorAssets();
    const auto Spell=M->FireMagicStats(TEXT("meteor"));const float Before=M->Snapshot().Mana;
    if(!M->BeginFireMagicCast(Spell))return;
    FColdSteelNetCastRequest Request;Request.SkillId=TEXT("meteor");Request.AimPoint=MeteorWire::TargetPoint;Request.AimNormal=FVector::UpVector;
    MeteorCastId=PS->RequestCastSpell(Request);Fire->MeteorLocalCastId=MeteorCastId;
    Fire->MeteorPendingRefund=Before-M->Snapshot().Mana;Fire->MeteorReleasedCast=Spell;Fire->bMeteorAwaitingResult=true;
    Request.Phase=1;Request.CastId=MeteorCastId;PS->RequestCastSpell(Request);PS->RequestCastSpell(Request);
    MeteorInitialMana=Before;MeteorCost=Cost;bSetup=true;Started=GetWorld()->GetRealTimeSeconds();
}

void ASkillWireAuditController::TickMeteor()
{
    if(HasAuthority()||!IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!bSetup||bDone)return;
    auto* Controlled=Cast<AFPSGAMECharacter>(GetPawn());auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Controlled||!M)return;
    auto* Fire=Controlled->FindComponentByClass<UFPSFireMagicComponent>();
    bMeteorReceipt|=Fire->MeteorResolvedCastId==MeteorCastId&&!Fire->bMeteorAwaitingResult;
    const auto Expected=M->FireMagicStats(TEXT("meteor"));
    int32 LiveOriginal=0;
    for(TActorIterator<AFPSMeteorStrike> It(GetWorld());It;++It)
    {
        auto* Strike=*It;if(Strike->HasAuthority()||!Strike->bNetInit)continue;
        if(Strike->Destination.Equals(MeteorWire::TargetPoint,2.f))
        {
            ++LiveOriginal;
            bMeteorReplica|=Strike->NetCaster==Controlled&&Strike->bImpacted
                &&FMath::IsNearlyEqual(Strike->CastSnapshot.Radius,Expected.Radius)
                &&FMath::IsNearlyEqual(Strike->CastSnapshot.AuraRadius,Expected.AuraRadius);
        }
        if(Strike->Destination.Equals(MeteorWire::LatePoint,2.f))
            bMeteorLate|=Strike->bImpacted&&Strike->LavaAge>1.f&&Strike->Fragments.IsEmpty()&&!Strike->bImpactBreakPending;
    }
    bHit|=LiveOriginal>1;
    if((bMeteorReplica&&bMeteorLate&&bMeteorReceipt&&Now-Started>5.)||Now-Started>35.)
    {
        bDone=true;const bool Paid=FMath::IsNearlyEqual(M->Snapshot().Mana,MeteorInitialMana-MeteorCost,.01f)&&!bHit;
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("role"),TEXT("client"));R->SetBoolField(TEXT("paid_once"),Paid);
        R->SetBoolField(TEXT("replicated_ranges_and_impact"),bMeteorReplica);R->SetBoolField(TEXT("late_no_replayed_burst"),bMeteorLate);
        R->SetBoolField(TEXT("identified_receipt"),bMeteorReceipt);R->SetBoolField(TEXT("duplicate_actor"),bHit);
        R->SetBoolField(TEXT("passed"),Paid&&bMeteorReplica&&bMeteorLate&&bMeteorReceipt);MeteorWire::Save(R);
        ServerMeteorResult(Paid,bMeteorReplica,bMeteorLate,bMeteorReceipt);ExitAt=Now+2.;
    }
}
void ASkillWireAuditController::ServerMeteorResult_Implementation(bool PaidOnce,bool Replica,bool Late,bool Receipt)
{if(FParse::Param(FCommandLine::Get(),TEXT("MeteorWireAudit"))){bReported=true;bPassed=PaidOnce&&Replica&&Late&&Receipt;}}

void ASkillWireAuditGameMode::TickMeteor()
{
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Guest)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();if(!Pawn||!PS)return;
    auto* Host=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Host||!Host->IsAudit())return;
    if(!GuestModel)
    {
        GuestModel=Host->CreateShadowModel(MeteorWire::Seed(Host));GuestModel->Current.Mana=GuestModel->Derived(TEXT("maxMp"));
        GuestModel->CurrentPawn=Pawn;PS->ShadowModel=GuestModel;Pawn->NetShadowProfile=GuestModel;
        Pawn->SetActorTickEnabled(false);Pawn->GetCharacterMovement()->SetComponentTickEnabled(false);PS->SetActorTickEnabled(false);
        Pawn->SetActorLocation(FVector(0,0,100));Pawn->ForceNetUpdate();
        Target=GetWorld()->SpawnActor<ANurseZombie>(FVector(400,0,100),FRotator::ZeroRotator);
        Target->Health=Target->MaxHealth=100000;Target->Knockdown=nullptr;
        Target->Combat->ConfigureToughnessBar(FMonsterToughnessBarTuning());
        if(auto* AI=Cast<AMonsterAIController>(Target->GetController()))AI->SetDecisionEnabled(false);
        Target->SetActorTickEnabled(false);Target->GetCharacterMovement()->SetComponentTickEnabled(false);
        Target->OnTakeAnyDamage.AddDynamic(this,&ThisClass::CountContact);
        ArmorInitialMana=GuestModel->Snapshot().Mana;ArmorManaCost=GuestModel->FireMagicStats(TEXT("meteor")).ManaCost;
        ArmorHostXP=Host->FireMagicProgress(TEXT("meteor")).Experience;
    }
    if(Stage==0&&Now-LastSetup>2.){LastSetup=Now;Guest->ClientSetupMeteor(ArmorInitialMana,ArmorManaCost);}
    int32 OriginalCount=0;for(TActorIterator<AFPSMeteorStrike> It(GetWorld());It;++It)
        if(It->GetActorLocation().Equals(MeteorWire::TargetPoint,2.f)&&!It->IsActorBeingDestroyed())++OriginalCount;
    if(OriginalCount>1)Stage=99;
    if(Stage==0&&OriginalCount==1)
    {
        Stage=1;auto Spell=GuestModel->FireMagicStats(TEXT("meteor"));Spell.Duration=8.f;
        Meteor=GetWorld()->SpawnActor<AFPSMeteorStrike>();Meteor->SetReplicates(false);
        Meteor->InitializeStrike(Pawn,Spell,MeteorWire::LatePoint,FVector::UpVector);MeteorAt=Now;
    }
    if(Stage==1&&Meteor&&Now-MeteorAt>2.2){Meteor->SetReplicates(true);Meteor->ForceNetUpdate();Stage=2;}
    // Client presentation can finish its assertions before the authority field
    // ends (especially during initial asset loading). Training settles at expiry.
    if((Guest->bReported&&Stage==2&&OriginalCount==0)||Now-Joined>55.)
    {
        const bool Paid=FMath::IsNearlyEqual(GuestModel->Snapshot().Mana,ArmorInitialMana-ArmorManaCost,.01f);
        const bool Training=GuestModel->FireMagicProgress(TEXT("meteor")).Experience>0&&Host->FireMagicProgress(TEXT("meteor")).Experience==ArmorHostXP;
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("role"),TEXT("listen_host"));R->SetBoolField(TEXT("authority_paid_once"),Paid);
        R->SetNumberField(TEXT("authority_damage_contacts"),Contacts);R->SetBoolField(TEXT("guest_training_only"),Training);
        R->SetNumberField(TEXT("guest_meteor_experience"),GuestModel->FireMagicProgress(TEXT("meteor")).Experience);
        R->SetNumberField(TEXT("host_meteor_experience_before"),ArmorHostXP);
        R->SetNumberField(TEXT("host_meteor_experience_after"),Host->FireMagicProgress(TEXT("meteor")).Experience);
        R->SetNumberField(TEXT("active_original_meteors"),OriginalCount);
        R->SetBoolField(TEXT("client_reported"),Guest->bReported);R->SetBoolField(TEXT("client_passed"),Guest->bPassed);
        R->SetBoolField(TEXT("passed"),Paid&&Contacts>0&&Training&&Stage==2&&Guest->bReported&&Guest->bPassed);MeteorWire::Save(R);ExitAt=Now+2.;
    }
}
