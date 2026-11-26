#include "HillsWildlifeAudio.h"
#include "WildlifeSubsystem.h"
#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundWave.h"
#include "TimerManager.h"

namespace
{
    void AppendTakes(TArray<FSoftObjectPath>& Out,const FString& Prefix,const TCHAR* Role,int32 Count)
    {
        for(int32 Index=1;Index<=Count;++Index)
        {
            const FString Name=FString::Printf(TEXT("SW_%s_%s_%02d"),*Prefix,Role,Index);
            Out.Emplace(FString::Printf(TEXT("/Game/Monsters/Wildlife/Audio/%s.%s"),*Name,*Name));
        }
    }
    void LoadTakes(TArray<TObjectPtr<USoundWave>>& Out, const FString& Prefix, const TCHAR* Role, int32 Count)
    {
        Out.Reset(Count);
        TArray<FSoftObjectPath> Paths;AppendTakes(Paths,Prefix,Role,Count);
        for (const auto& Path:Paths)
        {
            if (USoundWave* Wave = LoadObject<USoundWave>(nullptr, *Path.ToString())) Out.Add(Wave);
        }
    }

    USoundWave* Choose(const TArray<TObjectPtr<USoundWave>>& Takes)
    {
        return Takes.IsEmpty() ? nullptr : Takes[FMath::RandHelper(Takes.Num())].Get();
    }
}

TArray<FSoftObjectPath> UHillsWildlifeAudio::AssetPaths(const FString& Id)
{
    TArray<FSoftObjectPath> Paths;
    AppendTakes(Paths,Id,TEXT("Alarm"),2);AppendTakes(Paths,Id,TEXT("Hurt"),2);AppendTakes(Paths,Id,TEXT("Death"),1);
    if(Id==TEXT("boar")||Id.StartsWith(TEXT("deer_")))AppendTakes(Paths,Id==TEXT("boar")?TEXT("boar"):TEXT("deer"),TEXT("Hoof"),4);
    else if(Id==TEXT("crow"))AppendTakes(Paths,Id,TEXT("Wings"),2);
    return Paths;
}

UHillsWildlifeAudio::UHillsWildlifeAudio()
{
    SetIsReplicatedByDefault(true);
}

void UHillsWildlifeAudio::SetSpecies(const FString& Id)
{
    if (Id.IsEmpty() || Species == Id || !UWildlifeSubsystem::IsWildlifeMap(GetWorld())) return;
    Species = Id;
    if (GetNetMode() == NM_DedicatedServer) return;
    LoadTakes(Alarm, Id, TEXT("Alarm"), 2);
    LoadTakes(Hurt, Id, TEXT("Hurt"), 2);
    LoadTakes(Death, Id, TEXT("Death"), 1);
    Hooves.Reset();
    Wings.Reset();
    if (Id == TEXT("boar") || Id.StartsWith(TEXT("deer_")))
        LoadTakes(Hooves, Id == TEXT("boar") ? TEXT("boar") : TEXT("deer"), TEXT("Hoof"), 4);
    else if (Id == TEXT("crow"))
        LoadTakes(Wings, Id, TEXT("Wings"), 2);
}

void UHillsWildlifeAudio::Signal(EHillsAnimalSound Event)
{
    if (Species.IsEmpty() || !GetOwner()->HasAuthority() || bDeathSent) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (Event == EHillsAnimalSound::Alarm)
    {
        if (Now < NextAlarm) return;
        NextAlarm = Now + 6.;
    }
    else if (Event == EHillsAnimalSound::Hurt)
    {
        if (Now < NextHurt) return;
        NextHurt = Now + .45;
        NextAlarm = FMath::Max(NextAlarm, Now + 2.);
    }
    else if (Event == EHillsAnimalSound::Death) bDeathSent = true;
    MulticastSound(Event);
}

void UHillsWildlifeAudio::PlayVoice(USoundWave* Sound)
{
    if (!Sound) return;
    if (UAudioComponent* Previous = Voice.Get()) Previous->FadeOut(.025f, 0.f);
    Voice = UGameplayStatics::SpawnSoundAttached(Sound, GetOwner()->GetRootComponent(), NAME_None,
        FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, true, 1.f, FMath::FRandRange(.96f, 1.04f));
}

void UHillsWildlifeAudio::MulticastSound_Implementation(EHillsAnimalSound Event)
{
    if (GetNetMode() == NM_DedicatedServer || bDeathHeard) return;
    auto& Timers = GetWorld()->GetTimerManager();
    switch (Event)
    {
    case EHillsAnimalSound::Alarm:
        // Delay individuals slightly; a hit during this interval replaces the call.
        Timers.SetTimer(PendingAlarm, FTimerDelegate::CreateWeakLambda(this, [this]() { PlayVoice(Choose(Alarm)); }),
            FMath::FRandRange(.025f, .38f), false);
        break;
    case EHillsAnimalSound::Hurt:
        Timers.ClearTimer(PendingAlarm);
        PlayVoice(Choose(Hurt));
        break;
    case EHillsAnimalSound::Death:
        bDeathHeard = true;
        Timers.ClearTimer(PendingAlarm);
        PlayVoice(Choose(Death));
        break;
    case EHillsAnimalSound::TakeOff:
        if (auto* Sound = Choose(Wings))
            UGameplayStatics::SpawnSoundAttached(Sound, GetOwner()->GetRootComponent(), NAME_None, FVector::ZeroVector,
                EAttachLocation::KeepRelativeOffset, true, 1.f, FMath::FRandRange(.94f, 1.08f));
        break;
    }
}

void UHillsWildlifeAudio::UpdateHooves(bool bRunningOnGround, float RunPhase, const FVector& Feet)
{
    if (Hooves.IsEmpty()) return;
    if (!bRunningOnGround || bDeathHeard) { LastRunPhase = -1.f; return; }
    const float Previous = LastRunPhase;
    LastRunPhase = RunPhase;
    if (Previous < 0.f || Previous == RunPhase) return;

    // Each take is one close pair of contacts. Hind and fore pairs fall at different points in the gait.
    const float ForeContact = Species == TEXT("boar") ? .48f : .38f;
    const bool bHind = RunPhase < Previous;
    const bool bFore = Previous < ForeContact && RunPhase >= ForeContact;
    if (!bHind && !bFore) return;
    const int32 Count = Hooves.Num();
    LastHoof = LastHoof == INDEX_NONE || Count == 1 ? FMath::RandHelper(Count)
        : (LastHoof + 1 + FMath::RandHelper(Count - 1)) % Count;
    UGameplayStatics::PlaySoundAtLocation(this, Hooves[LastHoof], Feet, bHind ? .86f : 1.f, FMath::FRandRange(.93f, 1.07f));
}
