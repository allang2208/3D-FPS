#include "FPSFireMagicComponent.h"
#include "DragonBreathAudioAssets.h"
#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/Pawn.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundWave.h"

void UFPSFireMagicComponent::PrepareDragonBreathAudio()
{
    if(GetNetMode()==NM_DedicatedServer||GetOwner()->IsActorBeingDestroyed())return;
    auto* Start=Cast<USoundBase>(FSoftObjectPath(DragonBreathAudio::Start).ResolveObject());
    auto* Loop=Cast<USoundBase>(FSoftObjectPath(DragonBreathAudio::Loop).ResolveObject());
    auto* Stop=Cast<USoundBase>(FSoftObjectPath(DragonBreathAudio::Stop).ResolveObject());
    if(!Start||!Loop||!Stop)return;
    const auto MakeVoice=[this](TObjectPtr<UAudioComponent>& Voice,USoundBase* Sound)
    {
        if(Voice)return;
        Voice=NewObject<UAudioComponent>(GetOwner());
        GetOwner()->AddInstanceComponent(Voice);
        Voice->bAutoActivate=false;Voice->bAutoDestroy=false;Voice->bStopWhenOwnerDestroyed=true;
        Voice->SetupAttachment(GetOwner()->GetRootComponent());
        Voice->bOverrideAttenuation=true;
        Voice->AttenuationOverrides.bAttenuate=true;
        Voice->AttenuationOverrides.bSpatialize=true;
        Voice->AttenuationOverrides.AttenuationShapeExtents=FVector(150.f);
        Voice->AttenuationOverrides.FalloffDistance=2200.f;
        Voice->SetVolumeMultiplier(.85f);Voice->SetSound(Sound);Voice->RegisterComponent();
    };
    MakeVoice(DragonStartAudio,Start);MakeVoice(DragonLoopAudio,Loop);MakeVoice(DragonStopAudio,Stop);
}

void UFPSFireMagicComponent::RefreshDragonBreathAudio()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    const auto& State=DragonView();
    if(!State.bActive||!State.CastId){StopDragonBreathAudio();return;}
    if(!DragonStartAudio||!DragonLoopAudio||!DragonStopAudio)
    {
        // Recreate the bounded voices if this pawn survived an explicit cleanup.
        PrepareDragonBreathAudio();
        if(!DragonStartAudio||!DragonLoopAudio||!DragonStopAudio)return;
    }
    const auto* Clock=GetWorld()->GetGameState<AGameStateBase>();
    const double Now=Clock?Clock->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    const float Age=FMath::Max(0.f,float(Now-State.StartedAt));
    if(Age>=State.Cast.Duration){StopDragonBreathAudio();return;}
    if(DragonSoundCastId==State.CastId)return;
    // Subsequent frames reuse the nozzle computed by TickDragonBreath for FX.
    FVector Origin;FQuat Rotation;DragonBreathFrame(Origin,Rotation);
    DragonStartAudio->SetWorldLocation(Origin);DragonLoopAudio->SetWorldLocation(Origin);
    DragonStopAudio->SetWorldLocation(Origin);
    const auto* Pawn=Cast<APawn>(GetOwner());
    const bool Spatial=!(Pawn&&Pawn->IsLocallyControlled());
    for(auto* Voice:{DragonStartAudio.Get(),DragonLoopAudio.Get(),DragonStopAudio.Get()})
    {
        Voice->bAllowSpatialization=Spatial;
        Voice->AttenuationOverrides.bAttenuate=Spatial;
    }
    DragonStartAudio->Stop();DragonLoopAudio->Stop();DragonStopAudio->Stop();
    DragonSoundCastId=State.CastId;
    const bool HasOnset=Age<.30f;
    if(HasOnset)DragonStartAudio->Play(Age);
    // GetDuration() returns an indefinite sentinel for looping SoundWaves.
    const auto* Wave=Cast<USoundWave>(DragonLoopAudio->GetSound());
    const float LoopSeconds=Wave?Wave->Duration:0.f;
    const float Offset=LoopSeconds>0.f?FMath::Fmod(Age,LoopSeconds):0.f;
    DragonLoopAudio->FadeIn(HasOnset?.40f:.08f,1.f,Offset);
}

void UFPSFireMagicComponent::StopDragonBreathAudio()
{
    if(!DragonSoundCastId)return;
    DragonSoundCastId=0;
    if(DragonStartAudio)DragonStartAudio->Stop();
    if(DragonLoopAudio)DragonLoopAudio->FadeOut(.12f,0.f);
    if(DragonStopAudio)DragonStopAudio->Play();
}

void UFPSFireMagicComponent::DestroyDragonBreathAudio()
{
    DragonSoundCastId=0;
    for(auto* Voice:{DragonStartAudio.Get(),DragonLoopAudio.Get(),DragonStopAudio.Get()})
        if(Voice){Voice->Stop();Voice->DestroyComponent();}
    DragonStartAudio=nullptr;DragonLoopAudio=nullptr;DragonStopAudio=nullptr;
}
