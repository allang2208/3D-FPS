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
    virtual void RestartPlayer(AController* NewPlayer) override;

protected:
    virtual void BeginPlay() override;
private:
    void SpawnAfterStreaming(TWeakObjectPtr<AController> Player);
};
