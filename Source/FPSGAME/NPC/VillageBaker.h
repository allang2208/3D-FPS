#pragma once

#include "GameFramework/Actor.h"
#include "ResidentConversation.h"
#include "VillageBaker.generated.h"

class USkeletalMeshComponent;

UCLASS()
class FPSGAME_API AVillageBaker : public AActor
{
    GENERATED_BODY()

public:
    AVillageBaker();
    static FTransform GetStandingTransform(const AActor& BakerySite);
    bool CanServe(const APawn* Pawn) const;
    bool GetCounterTalkPoint(const APawn& Guest, FVector& Point) const;
    void SetLocalConversation(APlayerController* Player);

protected:
    virtual void BeginPlay() override;

private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Body;
    FResidentConversationFacing Facing;

    void ApplyAppearance();
};
