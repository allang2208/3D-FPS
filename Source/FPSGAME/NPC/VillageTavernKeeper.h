#pragma once

#include "GameFramework/Actor.h"
#include "ResidentConversation.h"
#include "VillageTavernKeeper.generated.h"

class USkeletalMeshComponent;

/** Stationary resident. The actor origin is the standing point on the tavern floor. */
UCLASS()
class FPSGAME_API AVillageTavernKeeper : public AActor
{
    GENERATED_BODY()

public:
    AVillageTavernKeeper();
    bool CanServe(const APawn* Pawn) const;
    bool GetCounterTalkPoint(const APawn& Guest, FVector& Point) const;
    void SetLocalConversation(APlayerController* Player);

protected:
    virtual void BeginPlay() override;

private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Body;
    FResidentConversationFacing ConversationFacing;

    void ApplyAppearance();
};
