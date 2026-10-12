#include "BellowSacLobber.h"
#include "MonsterCombatComponent.h"
#include "MonsterCorpseRagdollComponent.h"
#include "QuadrupedAnimationTemplate.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Sound/SoundBase.h"

void ABellowSacLobber::InitializeBellowAudio()
{
    if (PressureVoice || GetNetMode()==NM_DedicatedServer) return;
    const auto CreateVoice=[this](FName Name,float Near,float Falloff)
    {
        auto* Voice=NewObject<UAudioComponent>(this,Name);
        Voice->SetupAttachment(GetRootComponent());
        Voice->bAutoActivate=false; Voice->bAutoDestroy=false; Voice->bStopWhenOwnerDestroyed=true;
        Voice->bOverrideAttenuation=true;
        Voice->AttenuationOverrides.bAttenuate=true;
        Voice->AttenuationOverrides.bSpatialize=true;
        Voice->AttenuationOverrides.AttenuationShapeExtents=FVector(Near,0,0);
        Voice->AttenuationOverrides.FalloffDistance=Falloff;
        Voice->RegisterComponent();
        return Voice;
    };
    PressureVoice=CreateVoice(TEXT("BellowPressureVoice"),350.f,2850.f);
    PressureVoice->AttachToComponent(GetMesh(),FAttachmentTransformRules::SnapToTargetNotIncludingScale,TEXT("Bone_028"));
    CreatureVoice=CreateVoice(TEXT("BellowCreatureVoice"),300.f,3300.f);
    ContactVoice=CreateVoice(TEXT("BellowContactVoice"),250.f,2150.f);
    ContactVoice->SetAbsolute(true,false,false);
    FootstepVoice=CreateVoice(TEXT("BellowFootstepVoice"),180.f,1420.f);
    FootstepVoice->SetAbsolute(true,false,false);
    HurtVoice=CreateVoice(TEXT("BellowHurtVoice"),250.f,1750.f);
}

void ABellowSacLobber::PlayBellowVoice(UAudioComponent* Voice,FName CueRole,float Gain,float Age)
{
    const auto* Entry=BellowSounds.Find(CueRole);
    USoundBase* Sound=Entry?Entry->Get():nullptr;
    if (!Voice || !Sound || Age<0.f || Age>=Sound->GetDuration()) return;
    Voice->Stop(); Voice->SetSound(Sound);
    Voice->SetVolumeMultiplier(CreatureAudioGain*Gain);
    Voice->SetPitchMultiplier(1.f);
    Voice->Play(Age);
}

void ABellowSacLobber::NotifyDiscovery(bool DirectDiscovery)
{
    if (!HasAuthority() || Dead() || Clock()<NextAlertSoundAt) return;
    NextAlertSoundAt=Clock()+8.;
    MulticastBellowAccent(FMath::RandBool()?TEXT("AlertA"):TEXT("AlertB"),GetActorLocation(),Clock(),DirectDiscovery?1.f:.60f);
}

void ABellowSacLobber::MulticastBellowAccent_Implementation(FName CueRole,FVector_NetQuantize Location,double StartedAt,float Gain)
{
    if (Dead() || GetNetMode()==NM_DedicatedServer) return;
    InitializeBellowAudio();
    const float Age=FMath::Max(0.f,float(Clock()-StartedAt));
    if (Age>.35f) return;
    if (CueRole==TEXT("SpitA") || CueRole==TEXT("SpitB"))
    {
        PressureVoice->Stop();
        ContactVoice->SetWorldLocation(Location);
        PlayBellowVoice(ContactVoice,CueRole,Gain,Age);
    }
    else if (CueRole==TEXT("HurtA") || CueRole==TEXT("HurtB") || CueRole==TEXT("HurtC"))
    {
        // A short hit accent has its own voice and never cuts a warning/build-up.
        if (Age>.18f) return;
        PlayBellowVoice(HurtVoice,CueRole,Gain,Age);
    }
    else PlayBellowVoice(CreatureVoice,CueRole,Gain,Age);
}

float ABellowSacLobber::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    const float Applied=Super::TakeDamage(Damage,Event,EventInstigator,Causer);
    // Fatal hits already start the death cue. Blocked/zero damage makes no cry.
    if (HasAuthority() && Applied>0.f && !Dead() && Clock()>=NextHurtSoundAt)
    {
        NextHurtSoundAt=Clock()+.42;
        LastHurtVariant=(LastHurtVariant+1+FMath::RandRange(0,1))%3;
        static const FName Cues[]={TEXT("HurtA"),TEXT("HurtB"),TEXT("HurtC")};
        const float Gain=FMath::Clamp(.72f+Applied/FMath::Max(1.f,MaxHealth)*1.5f,.72f,1.f);
        MulticastBellowAccent(Cues[LastHurtVariant],GetActorLocation(),Clock(),Gain);
    }
    return Applied;
}

void ABellowSacLobber::UpdateFootstepAudio(float DeltaSeconds)
{
    if (GetNetMode()==NM_DedicatedServer) return;
    const auto* Movement=GetCharacterMovement();
    const auto* Anim=Cast<UQuadrupedTemplateAnimInstance>(GetMesh()->GetAnimInstance());
    const float Speed=GetVelocity().Size2D();
    if (!FootstepVoice || !Anim || !Anim->AnimationSet || !Anim->ActiveAction.IsNone()
        || Busy() || Combat->IsControlled() || Speed<12.f || !Movement->IsMovingOnGround()
        || !Movement->CurrentFloor.IsWalkableFloor())
    {
        bHadFootstepPhase=false;
        return;
    }
    const auto* Set=Anim->AnimationSet.Get();
    // The V01 slow/normal walks share the same four contacts. Read the actual
    // animation clock; no second stride timer or distance-driven approximation.
    const float Offset=FMath::Lerp(Set->WalkPhaseOffset,Set->RunPhaseOffset,Anim->WalkRunAlpha);
    const float Phase=FMath::Fmod(Anim->GaitPhase+Offset,1.f);
    const float Previous=LastFootstepPhase;
    LastFootstepPhase=Phase;
    if (!bHadFootstepPhase || DeltaSeconds>.2f)
    {
        bHadFootstepPhase=true;
        return;
    }
    const float Advance=FMath::Fmod(Phase-Previous+1.f,1.f);
    if (Advance<=KINDA_SMALL_NUMBER || Advance>.35f) return;
    // Author phase = gait + leg offset; touchdown is its wrap to zero.
    static const FName Feet[]={TEXT("Bone_005"),TEXT("Bone_024"),TEXT("Bone_011"),TEXT("Bone_019")};
    int32 FootIndex=INDEX_NONE;
    float LatestCrossing=-1.f;
    for (int32 I=0;I<4;++I)
    {
        const float Crossing=FMath::Fmod(.25f*I-Previous+1.f,1.f);
        if (Crossing>KINDA_SMALL_NUMBER && Crossing<=Advance && Crossing>LatestCrossing)
        { FootIndex=I; LatestCrossing=Crossing; }
    }
    if (FootIndex==INDEX_NONE) return;
    // Reuse the movement component's real walkable support plane. No per-tick
    // foot raycasts; airborne, idle and action poses cannot emit footsteps.
    const auto& Floor=Movement->CurrentFloor.HitResult;
    const FVector Foot=GetMesh()->GetSocketLocation(Feet[FootIndex]);
    const FVector Contact=FVector::PointPlaneProject(Foot,Floor.ImpactPoint,Floor.ImpactNormal);
    FootstepVoice->SetWorldLocation(Contact);
    LastFootstepVariant=(LastFootstepVariant+1+FMath::RandRange(0,2))%4;
    static const FName Cues[]={TEXT("FootstepA"),TEXT("FootstepB"),TEXT("FootstepC"),TEXT("FootstepD")};
    const float Gain=FMath::GetMappedRangeValueClamped(FVector2D(20.f,80.f),FVector2D(.48f,.76f),Speed);
    PlayBellowVoice(FootstepVoice,Cues[LastFootstepVariant],Gain);
}

void ABellowSacLobber::UpdatePressureAudio()
{
    if (GetNetMode()==NM_DedicatedServer) return;
    InitializeBellowAudio();
    const float Age=FMath::Max(0.f,float(Clock()-AttackClock.StartedAt));
    if (AttackClock.Kind!=EBellowAttack::Lob || Dead() || Combat->IsControlled() || State==EWolfState::Stagger || Age>=1.2f)
    {
        if (PressureVoice->IsPlaying()) PressureVoice->Stop();
        return;
    }
    if (AudioAttackStartedAt!=AttackClock.StartedAt)
    {
        AudioAttackStartedAt=AttackClock.StartedAt;
        PlayBellowVoice(PressureVoice,TEXT("Charge"),.95f,Age);
    }
}

void ABellowSacLobber::StopBellowAudio()
{
    for (auto* Voice : {PressureVoice.Get(),CreatureVoice.Get(),ContactVoice.Get(),FootstepVoice.Get(),HurtVoice.Get()})
        if (Voice) Voice->Stop();
    bHadFootstepPhase=false;
}

void ABellowSacLobber::PlayDeathAudio()
{
    if (bDeathAudioPlayed || GetNetMode()==NM_DedicatedServer) return;
    bDeathAudioPlayed=true;
    InitializeBellowAudio(); StopBellowAudio();
    PlayBellowVoice(CreatureVoice,FMath::RandBool()?TEXT("DeathA"):TEXT("DeathB"),1.f);
}

void ABellowSacLobber::OnCorpseGroundImpact(const FVector& Location,float SpeedCm)
{
    if (bCorpseImpactPlayed || !Dead() || GetNetMode()==NM_DedicatedServer) return;
    bCorpseImpactPlayed=true;
    ContactVoice->SetWorldLocation(Location);
    PlayBellowVoice(ContactVoice,TEXT("BodyFall"),FMath::Clamp(SpeedCm/160.f,.55f,1.f));
}

void ABellowSacLobber::EndPlay(const EEndPlayReason::Type Reason)
{
    if (CorpseRagdoll) CorpseRagdoll->OnSoftBodyImpact.RemoveAll(this);
    StopBellowAudio();
    Super::EndPlay(Reason);
}
