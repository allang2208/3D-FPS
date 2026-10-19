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
    virtual void InitGame(const FString& MapName,const FString& Options,FString& ErrorMessage) override;
    virtual void PreLogin(const FString& Options,const FString& Address,const FUniqueNetIdRepl& UniqueId,FString& ErrorMessage) override;

protected:
    virtual void BeginPlay() override;
private:
    FString ServerPassword;
    void SpawnAfterStreaming(TWeakObjectPtr<AController> Player);
    void TryInstallHillsPortal();
};
