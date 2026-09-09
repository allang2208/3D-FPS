#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Subsystems/WorldSubsystem.h"
#include "SceneTestPortal.generated.h"

class UTextRenderComponent;

UCLASS()
class FPSGAME_API ASceneTestPortal : public AActor
{
    GENERATED_BODY()
public:
    ASceneTestPortal();
    void Configure(const FString& Map, const FString& Label);
protected:
    virtual void BeginPlay() override;
private:
    void UsePortal();
    UPROPERTY() TObjectPtr<UTextRenderComponent> Sign;
    UPROPERTY() FString Destination;
    bool bTravelling = false;
};

// Installs inspection portals only in the three explicitly supported test maps.
UCLASS()
class FPSGAME_API USceneTestPortalSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    virtual void Deinitialize() override;
private:
    void SpawnPortals();
    FTimerHandle SpawnTimer;
    int32 Attempts = 0;
};
