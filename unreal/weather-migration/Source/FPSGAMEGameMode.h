#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "FPSGAMEGameMode.generated.h"

UCLASS()
class FPSGAME_API AFPSGAMEGameMode : public AGameModeBase
{
    GENERATED_BODY()

public:
    AFPSGAMEGameMode();

protected:
    virtual void BeginPlay() override;
};
