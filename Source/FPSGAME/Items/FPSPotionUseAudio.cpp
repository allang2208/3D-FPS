#include "FPSPotionUseComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Sound/SoundBase.h"

bool UFPSPotionUseComponent::PlayHydrationAudio(float Duration)
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||!Pawn->IsLocallyControlled()||!SwallowAudio||WaterSwallowSounds.IsEmpty())return false;
    StopSwallowAudio();
    HydrationAudioEnd=Duration>0.f?GetWorld()->GetTimeSeconds()+Duration:0.;
    PlayNextWaterSwallow();
    return true;
}

void UFPSPotionUseComponent::PlayNextWaterSwallow()
{
    if(!SwallowAudio||WaterSwallowSounds.IsEmpty())return;
    const double Remaining=HydrationAudioEnd-GetWorld()->GetTimeSeconds();
    if(HydrationAudioEnd>0.&&Remaining<=0.){EndHydrationAudio();return;}
    auto* Sound=WaterSwallowSounds[FMath::RandRange(0,WaterSwallowSounds.Num()-1)].Get();
    SwallowAudio->SetSound(Sound);SwallowAudio->Play();
    if(HydrationAudioEnd<=0.)return; // Instant refills play the complete sample once.
    // Use the decoded clip length plus a small breath; never overlap swallows
    // or loop a single sample through a long drink.
    const float Delay=FMath::Max(.1f,Sound->GetDuration())+FMath::FRandRange(.12f,.20f);
    if(Delay<Remaining)
        GetWorld()->GetTimerManager().SetTimer(SwallowTimer,this,&UFPSPotionUseComponent::PlayNextWaterSwallow,Delay,false);
    else
        GetWorld()->GetTimerManager().SetTimer(SwallowTimer,this,&UFPSPotionUseComponent::EndHydrationAudio,static_cast<float>(Remaining),false);
}

void UFPSPotionUseComponent::EndHydrationAudio()
{
    GetWorld()->GetTimerManager().ClearTimer(SwallowTimer);HydrationAudioEnd=0.;
    if(SwallowAudio&&SwallowAudio->IsPlaying())SwallowAudio->FadeOut(.06f,0.f);
}

void UFPSPotionUseComponent::StopSwallowAudio()
{
    if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(SwallowTimer);
    HydrationAudioEnd=0.;
    if(SwallowAudio)SwallowAudio->Stop();
}

void UFPSPotionUseComponent::PlayFoodSwallow()
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||!Pawn->IsLocallyControlled()||!SwallowAudio||!FoodSwallowSound)return;
    StopSwallowAudio();SwallowAudio->SetSound(FoodSwallowSound);SwallowAudio->Play();
    // Let the single swallow finish naturally while the hand retracts. Cancel
    // and EndPlay stop it immediately; the next consumable replaces its tail.
}
