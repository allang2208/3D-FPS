#include "TwoHandInspectAudio.h"
#include "Components/AudioComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

const FSoftObjectPath FTwoHandInspectAudio::Paths[]={
    FSoftObjectPath(TEXT("/Game/Audio/TwoHandInspect/S_TwoHandInspect_Air_01.S_TwoHandInspect_Air_01")),
    FSoftObjectPath(TEXT("/Game/Audio/TwoHandInspect/S_TwoHandInspect_Air_02.S_TwoHandInspect_Air_02"))
};

void FTwoHandInspectAudio::PrepareSounds(bool bLoadSynchronously)
{
    Sounds.Reset();
    for(const FSoftObjectPath& Path:Paths)
        if(auto* Sound=Cast<USoundBase>(bLoadSynchronously?Path.TryLoad():Path.ResolveObject()))
            Sounds.Add(Sound);
}

void FTwoHandInspectAudio::PlayBeat(const UObject* Context,float From,float To,float Peak,float Volume,float ActionRate)
{
    // Both imported takes peak 150 ms after file start. All times below are in
    // clip seconds, including the portion of the wave already passed this frame.
    const float Start=Peak-.15f;
    if(From>=Start||To<Start||Sounds.IsEmpty())return;
    USoundBase* Sound=Sounds[FMath::RandHelper(Sounds.Num())];
    if(To-Start>=Sound->GetDuration())return;
    Stop();
    Playing=UGameplayStatics::SpawnSound2D(Context,Sound,Volume,ActionRate,To-Start);
}

void FTwoHandInspectAudio::Stop(float FadeSeconds)
{
    if(IsValid(Playing))
    {
        if(FadeSeconds>0.f)Playing->FadeOut(FadeSeconds,0.f);
        else Playing->Stop();
    }
    Playing=nullptr;
}
