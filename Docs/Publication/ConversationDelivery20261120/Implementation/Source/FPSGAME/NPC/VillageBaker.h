#pragma once

#include "GameFramework/Actor.h"
#include "ResidentConversation.h"
#include "VillageBaker.generated.h"

class USkeletalMeshComponent;
struct FStreamableHandle;

UCLASS()
class FPSGAME_API AVillageBaker : public AActor
{
    GENERATED_BODY()

public:
    AVillageBaker();
    static FTransform GetStandingTransform(const FTransform& BakeryFrame);
    bool CanServe(const APawn* Pawn) const;
    bool GetCounterTalkPoint(const APawn& Guest, FVector& Point) const;
    void SetLocalConversation(APlayerController* Player);

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;

private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Body;
    FResidentConversationFacing Facing;
    TSharedPtr<FStreamableHandle> AppearanceLoad;

    void ApplyAppearance();
};
