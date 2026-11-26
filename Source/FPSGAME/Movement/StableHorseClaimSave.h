#pragma once

#include "GameFramework/SaveGame.h"
#include "StableHorseClaimSave.generated.h"

// A title to an authored resident survives its owner's disconnect and level streaming.
UCLASS()
class UStableHorseClaimSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() FGuid Profile;
    UPROPERTY() FGuid Individual;
    UPROPERTY() uint8 BirthVersion=0;
};
