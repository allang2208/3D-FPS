#include "SniperZhimingWire.h"
#include "Algo/Count.h"
#include "ShotgunWireAudit.h"
#include "SniperSuppressorAssets.h"
#include "RifleSuppressedAudioAssets.h"
#include "M24WeaponAssets.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Combat/WeaponDamageTypes.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterAIController.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISense_Hearing.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Multiplayer/ColdSteelPreparedHit.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Dom/JsonObject.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"

namespace ShotgunWire { void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Pass,const TCHAR* Role); }
namespace M870Wire { FColdSteelProfile Seed(UColdSteelStatusModel* Model,const FString& Id,int32 Phase); }

namespace SniperZhimingWire
{
bool Enabled(){static const bool Active=FParse::Param(FCommandLine::Get(),TEXT("SniperZhimingWire"));return Active;}
const TCHAR* Definition(int32 Phase){return Phase<2?TEXT("ue_m24"):Phase<4?TEXT("ue_svd"):TEXT("ue_svch");}

ANurseZombie* Target(UWorld* World)
{
    for(TActorIterator<ANurseZombie> It(World);It;++It)return *It;
    return nullptr;
}
void EnsureTarget(UWorld* World)
{
    auto* Nurse=Target(World);
    if(!Nurse)Nurse=World->SpawnActor<ANurseZombie>(FVector(400,300,500),FRotator::ZeroRotator);
    if(!Nurse)return;
    Nurse->Health=Nurse->MaxHealth=10000.f;
    if(auto* AI=Cast<AMonsterAIController>(Nurse->GetController()))
    {
        AI->SetDecisionEnabled(false);
        if(auto* Senses=AI->GetPerceptionComponent())Senses->ForgetAll();
    }
    Nurse->GetCharacterMovement()->DisableMovement();
    Nurse->SetActorTickEnabled(false);
}
bool Equipment(const FFPSBodyWeapon& W,int32 Phase)
{
    const bool Mounted=Phase%2==0;
    const auto Meshes=Algo::CountIf(W.Parts,[](const FFPSBodyAttachment& P){
        return P.bVisible&&P.Mesh.ToSoftObjectPath().GetLongPackageName()==SniperSuppressorAssets::ZhimingMesh;});
    if(W.GunDefinition!=Definition(Phase)||W.bGunSuppressed!=Mounted||Meshes!=SIZE_T(Mounted)||W.GunFireSound.IsNull())return false;
    if(Phase<2)return W.GunSuppressedSound.ToSoftObjectPath().GetLongPackageName()==M24WeaponAssets::SuppressedSoundPath;
    const auto* Bank=RifleSuppressedAudioAssets::Bank(Definition(Phase));
    for(int32 I=1;I<=4;++I)
        if(!W.GunSounds.Contains(TSoftObjectPtr<USoundBase>(FSoftObjectPath(RifleSuppressedAudioAssets::SoundPath(Bank,I)))))return false;
    return W.GunSuppressedSound.ToString()==RifleSuppressedAudioAssets::SoundPath(Bank,1);
}
}

void AShotgunWireAuditController::TickSniperZhiming(AFPSGAMECharacter* Subject,double Now)
{
    if(!Subject)return;
    const auto* Target=SniperZhimingWire::Target(GetWorld());
    const auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(Combat&&Combat->bStunned&&Combat->StunSecondsRemaining()>0.f)
    {
        bObservedSniperStun=true;
        SniperStunPeak=FMath::Max(SniperStunPeak,Combat->StunSecondsRemaining());
        if(SniperStunFirstAt<0.)SniperStunFirstAt=Now;
        SniperStunLastAt=Now;
    }
    if(!bSent&&Now-Started>=2.5)
    {
        Subject->ShotsFired=100+Current;
        Subject->FireShot();bSent=true;
        return;
    }
    if(!bSent)return;
    if(SentAt<0&&Now-Started>=2.9){ServerReady(Current);SentAt=Now;}
    if(SentAt<0||Now-SentAt<2.)return;
    auto* Seen=ObserverSubject?ObserverSubject->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    auto* Own=Subject->FindComponentByClass<UFPSPlayerBodyComponent>();
    const bool Remote=Seen&&Seen->MotionBindings.Num()==1&&SniperZhimingWire::Equipment(Seen->MotionBindings[0].Definition,Current);
    const bool Local=Own&&Own->LocalWeapons.Num()==1&&SniperZhimingWire::Equipment(Own->LocalWeapons[0],Current);
    const bool Fired=Subject->ShotsFired==101+Current;
    const bool Stun=Combat&&!Combat->bStunned&&bObservedSniperStun==(Current%2==0)&&Combat->StunSecondsRemaining()==0.f
        &&SniperStunPeak<=.251f&&SniperStunLastAt-SniperStunFirstAt<=.28;
    const bool Passed=Remote&&Local&&Fired&&Stun;
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("phase"),Current);
    Row->SetBoolField(TEXT("host_muzzle_and_audio_manifest"),Remote);Row->SetBoolField(TEXT("owner_muzzle_and_audio_manifest"),Local);
    Row->SetNumberField(TEXT("stun_peak_seconds"),SniperStunPeak);
    Row->SetNumberField(TEXT("stun_observed_seconds"),SniperStunLastAt-SniperStunFirstAt);
    Row->SetBoolField(TEXT("owner_fired"),Fired);Row->SetBoolField(TEXT("observed_stun"),bObservedSniperStun);Row->SetBoolField(TEXT("stun_window_correct"),Stun);
    Results.Add(MakeShared<FJsonValueObject>(Row));bAllPassed&=Passed;bReported=true;
    ServerPresentationResult(Current,Passed,FVector::ZeroVector,FVector::ZeroVector,FVector::ZeroVector);
    ShotgunWire::Save(Results,bAllPassed,TEXT("client"));
}

void AShotgunWireAuditController::ProbeSniperZhiming(int32 Phase)
{
    if(Phase!=Expected||Finished!=Phase||Results.Num()!=Phase)return;
    if(SniperProbePhase!=Phase){SniperProbePhase=Phase;SniperProbeStartedAt=FPlatformTime::Seconds();}
    auto* Shooter=Cast<AFPSGAMECharacter>(GetPawn());
    auto* PS=GetPlayerState<AColdSteelPlayerState>();
    auto* Model=PS?PS->ShadowModel.Get():nullptr;
    auto* Body=Shooter?Shooter->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    auto* Target=SniperZhimingWire::Target(GetWorld());
    auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    const bool Mounted=Phase%2==0;
    bool Heard=false;
    if(auto* AI=Target?Cast<AMonsterAIController>(Target->GetController()):nullptr)
        if(auto* Senses=AI->GetPerceptionComponent())
        {
            FActorPerceptionBlueprintInfo Info;
            if(Senses->GetActorsPerception(Shooter,Info))
                Heard=Info.LastSensedStimuli.ContainsByPredicate([Mounted](const FAIStimulus& Stimulus){
                    return Stimulus.Type==UAISense::GetSenseID<UAISense_Hearing>()&&Stimulus.WasSuccessfullySensed()
                        &&Stimulus.Tag==(Mounted?TEXT("GunshotSuppressed"):TEXT("Gunshot"));});
        }
    // Hearing is processed after network dispatch. A delayed shot and this
    // controller RPC can arrive in the same frame on their separate channels.
    if(!Heard&&FPlatformTime::Seconds()-SniperProbeStartedAt<.5)
    {
        FTimerHandle Retry;
        GetWorld()->GetTimerManager().SetTimer(Retry,FTimerDelegate::CreateWeakLambda(this,[this,Phase]()
            {ProbeSniperZhiming(Phase);}),.05f,false);
        return;
    }
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("phase"),Phase);
    Row->SetNumberField(TEXT("perception_wait_seconds"),FPlatformTime::Seconds()-SniperProbeStartedAt);
    Row->SetStringField(TEXT("weapon"),SniperZhimingWire::Definition(Phase));Row->SetBoolField(TEXT("mounted_at_fire"),Mounted);
    bool Audio=false,Variants=false,Impact=false,NonCritical=false,Critical=false,Amount=false;
    const auto* Launch=PS?PS->M24Launches.Find(101+Phase):nullptr;
    if(Body&&Body->LocalWeapons.Num()==1&&SniperZhimingWire::Equipment(Body->LocalWeapons[0],Phase))
    {
        const auto& W=Body->LocalWeapons[0];
        TGuardValue<uint32> PreviousSequence(Body->ReceivedGunSequence[0],Body->ReceivedGunSequence[0]);
        FFPSGunEvent Event;Event.SentAt=Body->ServerClock();Event.Instance=W.GunInstance;Event.Sequence=Body->ReceivedGunSequence[0]+1;
        Event.Sound=Mounted?W.GunFireSound:W.GunSuppressedSound;
        Audio=Body->AcceptGunEvent(Event)&&Event.bSuppressed==Mounted&&Event.Sound==(Mounted?W.GunSuppressedSound:W.GunFireSound);
        const auto& Bank=Mounted?Shooter->RifleSuppressedVariants:Shooter->RifleFireVariants;
        const TSoftObjectPtr<USoundBase> Chosen=Bank.IsEmpty()?Event.Sound:TSoftObjectPtr<USoundBase>(Bank.Last().Get());
        ++Event.Sequence;Event.Sound=Chosen;
        Variants=!Chosen.IsNull()&&Body->AcceptGunEvent(Event)&&Event.Sound==Chosen;
    }
    if(Launch&&Model&&Combat&&Shooter)
    {
        // Switch only the shadow equipment after the guest's real shot, before adjudicating its contact.
        auto Opposite=M870Wire::Seed(Model,Launch->Item.InstanceId,Phase^1);
        TGuardValue<FColdSteelProfile> Restore(Model->Current,MoveTemp(Opposite));
        const auto CurrentShot=ColdSteelSkills::Snapshot(Shooter,Model->Equipped(),true);
        FColdSteelNetHitReport Hit;Hit.ItemInstance=Launch->Item.InstanceId;Hit.ItemDefinition=Launch->Item.Definition;
        Hit.FireSequence=101+Phase;Hit.Flags=(1<<1)|(1<<6);Hit.ConvergenceRounds=1;Hit.Target=Target;
        Hit.AimOrigin=Launch->Eye;Hit.ImpactPoint=Target->GetActorLocation();Hit.Direction=(FVector(Hit.ImpactPoint)-Launch->Eye).GetSafeNormal();Hit.HitNormal=-FVector(Hit.Direction);
        Hit.ClientFireTime=GetWorld()->GetGameState()->GetServerWorldTimeSeconds();
        FColdSteelPreparedHit Prepared;
        Impact=PS->PrepareHitReport(Hit,Prepared)&&Prepared.Damage>0&&Prepared.bFiredRound;
        if(Impact)
        {
            Amount=FMath::IsNearlyEqual(Prepared.Shot.CriticalDamageBonus-CurrentShot.CriticalDamageBonus,Mounted?.15f:-.15f,.0001f)
                &&FMath::IsNearlyEqual(Prepared.Shot.FirearmCriticalStunSeconds,Mounted?.25f:0.f);
            // Isolate the critical roll and cap fixture damage so the same replicated target survives all cases.
            auto Shot=Prepared.Shot;FWeaponDamageResult Ordinary,Crit;
            Shot.CriticalChance=0.f;Shot.CriticalRoll=1.f;
            const auto HitFor=[&](FWeaponDamageResult& Result){return ColdSteelSkills::ApplyHit(Shooter,Prepared.Hit,8.f,Hit.Direction,Shot,&Result);};
            NonCritical=HitFor(Ordinary)>0.f&&!Ordinary.bCritical&&Combat->StunSecondsRemaining()==0.f;
            Shot.CriticalChance=100.f;Shot.CriticalRoll=0.f;
            Critical=HitFor(Crit)>0.f&&Crit.bCritical&&!Crit.bKilled&&FMath::IsNearlyEqual(Combat->StunSecondsRemaining(),Mounted?.25f:0.f,.001f);
        }
    }
    Row->SetBoolField(TEXT("server_ai_heard_shot"),Heard);
    Row->SetBoolField(TEXT("registered_launch"),Launch!=nullptr);Row->SetBoolField(TEXT("impact_after_muzzle_change"),Impact);
    Row->SetBoolField(TEXT("fire_time_critical_bonus_and_duration"),Amount);Row->SetBoolField(TEXT("noncritical_no_stun"),NonCritical);
    Row->SetBoolField(TEXT("critical_stun_duration"),Critical);Row->SetBoolField(TEXT("audio_bank_corrected"),Audio);Row->SetBoolField(TEXT("audio_variant_preserved"),Variants);
    UE_LOG(LogTemp,Display,TEXT("SNIPER_WIRE phase=%d audio=%d variant=%d impact=%d bonus=%d ordinary=%d crit=%d"),
        Phase,Audio,Variants,Impact,Amount,NonCritical,Critical);
    Results.Add(MakeShared<FJsonValueObject>(Row));bAllPassed&=Heard&&Audio&&Variants&&Impact&&Amount&&NonCritical&&Critical;
}
