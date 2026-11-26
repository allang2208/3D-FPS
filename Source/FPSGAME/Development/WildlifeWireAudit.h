#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "WildlifeWireAudit.generated.h"

class AColdSteelAnimal;

/** Explicit opt-in transport fixture; isolated profiles, no terrain/loot assertions. */
UCLASS()
class AWildlifeWireAuditController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(Replicated) TObjectPtr<AColdSteelAnimal> Subject;
    UPROPERTY(Replicated) int32 Case = -1;
    UPROPERTY(Replicated) uint32 Revision = 0;
    UFUNCTION(Server, Reliable) void ServerObserved(int32 Index, bool Passed, const FString& Detail);
    UFUNCTION(Client, Reliable) void ClientFinish(bool Passed);
    int32 Finished = -1;
    bool AllPassed = true;
    TArray<TSharedPtr<class FJsonValue>> Results;
private:
    TWeakObjectPtr<AColdSteelAnimal> Seen;
    int32 Watching = -1, Reported = -1;
    double WatchStart = 0., ExitAt = -1.;
};

UCLASS()
class AWildlifeWireAuditGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AWildlifeWireAuditGameMode();
    virtual void StartPlay() override;
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Tick(float Delta) override;
private:
    UPROPERTY() TObjectPtr<AWildlifeWireAuditController> Guest;
    UPROPERTY() TObjectPtr<AColdSteelAnimal> Animal;
    int32 Prepared = -1;
    double PreparedAt = 0., Started = 0., DiedAt = 0., ExitAt = -1.;
    bool Revealed = false, Passed = true;
};
