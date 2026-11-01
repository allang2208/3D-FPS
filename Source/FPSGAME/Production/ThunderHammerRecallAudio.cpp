#include "ThunderHammerRecallAudio.h"
#include "ThunderHammerThrown.h"
#include "WarhammerAudioPaths.h"
#include "Components/AudioComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

void AThunderHammerThrown::MulticastCaught_Implementation(double ContactTime)
{
    if(Phase==4)return;
    Phase=3;CaughtAt=ContactTime;
    StopRecallAudio(0.f);
    PlayRecallCatchAudio();
}

void AThunderHammerThrown::TickRecallAudio()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    if(Phase!=2)
    {
        StopRecallAudio(.035f);
        if(Phase==3)PlayRecallCatchAudio();
        return;
    }
    const float Age=RecallAge(),T=FMath::Clamp(Age/FMath::Max(.01f,RecallDuration),0.f,1.f);
    const float Fade=FMath::Clamp(Age/.08f,0.f,1.f);
    auto Present=[&](TObjectPtr<UAudioComponent>& Audio,USoundBase* Sound,float Volume,float Pitch)
    {
        if(!Sound)return;
        if(!IsValid(Audio))
        {
            Audio=NewObject<UAudioComponent>(this);AddInstanceComponent(Audio);
            Audio->SetAutoActivate(false);Audio->bAutoDestroy=true;Audio->bStopWhenOwnerDestroyed=true;
            Audio->SetupAttachment(GetRootComponent());Audio->SetSound(Sound);
            Audio->SetVolumeMultiplier(Volume);Audio->SetPitchMultiplier(Pitch);Audio->RegisterComponent();
            // Seek a late-loaded/remote loop into the same recall, never replay
            // a fixed-length approach sound whose catch would drift with range.
            // Duration is the imported clip length; GetDuration() on a looping
            // SoundWave reports an indefinite duration instead.
            Audio->Play(FMath::Fmod(Age,FMath::Max(.001f,Sound->Duration)));
        }
        else
        {Audio->SetVolumeMultiplier(Volume);Audio->SetPitchMultiplier(Pitch);}
    };
    Present(RecallMetalAudio,RecallMetalSound,Fade*(.48f+.30f*T),.88f+.20f*T);
    Present(RecallAirAudio,RecallAirSound,Fade*(.42f+.48f*T),1.f);
    // Add the actual outbound release recording, with the same source offset
    // and original pitch. Keep the user's existing air/metal layers intact.
    if(RecallThrowWhooshSound)
    {
        if(!IsValid(RecallThrowWhooshAudio))
        {
            auto* Audio=NewObject<UAudioComponent>(this);RecallThrowWhooshAudio=Audio;AddInstanceComponent(Audio);
            Audio->SetAutoActivate(false);Audio->bAutoDestroy=false;Audio->bStopWhenOwnerDestroyed=true;
            Audio->SetupAttachment(GetRootComponent());Audio->SetSound(RecallThrowWhooshSound);Audio->RegisterComponent();
        }
        const float SpinEnvelope=.8f+.2f*FMath::Cos(2.f*PI*RecallSpinTurns());
        RecallThrowWhooshAudio->SetVolumeMultiplier(.72f*Fade*SpinEnvelope);
        RecallThrowWhooshAudio->SetPitchMultiplier(1.f);
        // Repeat the same trimmed clip for long returns, without accumulating
        // overlapping voices. A late asset load seeks into the current return.
        if(!RecallThrowWhooshAudio->IsPlaying())
        {
            const float Length=FMath::Max(.001f,RecallThrowWhooshSound->Duration-WarhammerAudioPaths::HeavyStartSeconds);
            RecallThrowWhooshAudio->Play(WarhammerAudioPaths::HeavyStartSeconds+FMath::Fmod(Age,Length));
        }
    }
}

void AThunderHammerThrown::StopRecallAudio(float FadeSeconds)
{
    for(auto* Audio:{RecallMetalAudio.Get(),RecallAirAudio.Get(),RecallThrowWhooshAudio.Get()})if(IsValid(Audio))
    {
        if(FadeSeconds>0.f)Audio->FadeOut(FadeSeconds,0.f);
        else Audio->Stop();
    }
    RecallMetalAudio=nullptr;RecallAirAudio=nullptr;RecallThrowWhooshAudio=nullptr;
}

void AThunderHammerThrown::PlayRecallCatchAudio()
{
    if(bRecallCatchAudioPlayed||GetNetMode()==NM_DedicatedServer||!RecallCatchSound)return;
    bRecallCatchAudioPlayed=true;
    // Exactly the authoritative contact/hand-compression instant, not the
    // predicted travel timeout. Independent component keeps the clip's full tail.
    UGameplayStatics::SpawnSoundAtLocation(this,RecallCatchSound,GetActorLocation());
}
