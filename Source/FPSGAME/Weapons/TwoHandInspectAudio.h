#pragma once

#include "CoreMinimal.h"
#include "TwoHandInspectAudio.generated.h"

class UAudioComponent;
class USoundBase;

/** The same two air recordings are used with each inspect clip's own movement peaks. */
USTRUCT()
struct FTwoHandInspectAudio
{
    GENERATED_BODY()

    static const FSoftObjectPath Paths[2];
    void PrepareSounds(bool bLoadSynchronously);
    void PlayBeat(const UObject* Context,float From,float To,float Peak,float Volume,float ActionRate);
    void Stop(float FadeSeconds=.04f);

private:
    UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> Sounds;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> Playing;
};
