#include "M66AudioComponent.h"
#include "M66IncineratorMonster.h"
#include "M66AnimInstance.h"
#include "M66SweepTiming.h"
#include "M66BreathTiming.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/AudioComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"
#include "Sound/SoundBase.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

UM66AudioComponent::UM66AudioComponent()
{
    SetIsReplicatedByDefault(true);PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostPhysics;PrimaryComponentTick.TickInterval=.033f;
}
void UM66AudioComponent::BeginPlay()
{
    Super::BeginPlay();Monster=Cast<AM66IncineratorMonster>(GetOwner());
    if(Monster)AddTickPrerequisiteComponent(Monster->GetMesh());OnRep_Events();
}
double UM66AudioComponent::Clock() const
{
    const auto* State=GetWorld()->GetGameState();
    const double Now=State?State->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    // The actor channel can arrive before GameState's first clock correction.
    // Never classify retained events using a time before this channel opened.
    return GetOwner()->HasAuthority()?Now:FMath::Max(Now,InitialServerTime);
}
void UM66AudioComponent::PreReplication(IRepChangedPropertyTracker& Tracker)
{
    Super::PreReplication(Tracker);
    if(GetOwner()->HasAuthority())InitialServerTime=Clock();
}
void UM66AudioComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(UM66AudioComponent,InitialServerTime,COND_InitialOnly);
    DOREPLIFETIME(UM66AudioComponent,Events);
}
void UM66AudioComponent::Emit(FName Cue,const FVector& At,double Time)
{
    if(!GetOwner()->HasAuthority())return;
    if(Cue==TEXT("Hurt")){if(Clock()<NextHurtAt)return;NextHurtAt=Clock()+.3;}
    FM66SoundEvent Event;Event.Serial=++NextSerial;Event.Cue=Cue;Event.At=Time<0?Clock():Time;Event.Location=At;
    if(Events.Num()>=12)Events.RemoveAt(0);Events.Add(Event);
    OnRep_Events();GetOwner()->ForceNetUpdate();
}
void UM66AudioComponent::OnRep_Events()
{
    if(!Monster)Monster=Cast<AM66IncineratorMonster>(GetOwner());
    if(!Monster||!HasBegunPlay())return;
    for(const auto& Event:Events)
    {
        if(Event.Serial<=LastConsumed)continue;LastConsumed=Event.Serial;
        const auto* Found=Monster->BodySounds.Find(Event.Cue);
        if(!Found||!IsValid(Found->Get()))continue;
        const float Age=FMath::Max(0.f,float(Clock()-Event.At));auto* Sound=Found->Get();
        if(Age>=Sound->GetDuration())continue;
        ++ResolvedCount;
        if(GetNetMode()!=NM_DedicatedServer)
            UGameplayStatics::PlaySoundAtLocation(this,Sound,Event.Location,Monster->BodyAudioGain,1.f,Age,Monster->BodyAudioAttenuation);
    }
}
void UM66AudioComponent::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Function)
{
    Super::TickComponent(Dt,Type,Function);if(!Monster)return;
    if(GetOwner()->HasAuthority())
    {
        if(AttackSerial!=Monster->SweepSerial()){AttackSerial=Monster->SweepSerial();bSwingPlayed=bRecoveryPlayed=false;}
        if(Monster->IsSweeping())
        {
            const float Age=Monster->SweepAge();
            if(!Monster->IsGroundSlamming()&&!Monster->IsBreathing()&&!bSwingPlayed&&Age>=M66SweepTiming::ContactStart-.16f)
            {bSwingPlayed=true;Emit(TEXT("SweepSwing"),Monster->GetMesh()->GetSocketLocation(TEXT("Bone_036")),Clock()-Age+M66SweepTiming::ContactStart-.16f);}
            if(Monster->IsBreathing()&&!bRecoveryPlayed&&Age>=M66BreathTiming::FireEnd)
            {bRecoveryPlayed=true;Emit(TEXT("Recover"),Monster->GetMesh()->GetSocketLocation(TEXT("Bone_006")),Clock()-Age+M66BreathTiming::FireEnd);}
        }
        auto* Anim=Cast<UM66AnimInstance>(Monster->GetMesh()->GetAnimInstance());
        const bool Walking=Anim&&!Monster->Busy()&&Monster->GetCharacterMovement()->IsMovingOnGround()&&Anim->Activity>.15f;
        if(Walking)
        {
            const float Phase=Anim->Phase;
            if(bHavePhase&&Clock()>=NextStepAt)
            {
                const bool Left=Phase<PreviousPhase,Right=PreviousPhase<.5f&&Phase>=.5f;
                if(Left||Right){Emit(Left?TEXT("FootLeft"):TEXT("FootRight"),Monster->GetMesh()->GetSocketLocation(Left?TEXT("Bone_010"):TEXT("Bone_015")));NextStepAt=Clock()+.12;}
            }
            PreviousPhase=Phase;bHavePhase=true;
        }
        else bHavePhase=false;
    }
    if(GetNetMode()!=NM_DedicatedServer)
    {
        const bool EmitSmoke=Monster->bEnableBackSmoke&&!Monster->Dead();
        const auto* Sound=Monster->BodySounds.Find(TEXT("BackSmoke"));
        if(EmitSmoke&&Sound&&*Sound)
        {
            if(!SmokeVoice)SmokeVoice=UGameplayStatics::SpawnSoundAttached(*Sound,Monster->GetMesh(),TEXT("M66_Vent_Rear_Tip"),FVector::ZeroVector,EAttachLocation::KeepRelativeOffset,true,
                Monster->BodyAudioGain*.20f,1.f,0.f,Monster->BodyAudioAttenuation);
        }
        else if(SmokeVoice){SmokeVoice->FadeOut(.2f,0.f);SmokeVoice=nullptr;}
    }
    if(Monster->Dead())SetComponentTickEnabled(false);
}
void UM66AudioComponent::EndPlay(const EEndPlayReason::Type Reason)
{if(SmokeVoice){SmokeVoice->Stop();SmokeVoice=nullptr;}Super::EndPlay(Reason);}
