#pragma once
#include "Commandlets/Commandlet.h"
#include "GameFramework/PlayerController.h"
#include "BowSkillTrainingAuditCommandlet.generated.h"

// Authority-side remote owner without opening a socket or starting a game map.
UCLASS()
class ABowSkillAuditRemoteController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual bool IsLocalController() const override { return false; }
};

UCLASS()
class UBowSkillTrainingAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
    int32 RunSparrowPresentation(const FString& Params);
    int32 RunQuiverBelt(const FString& Params);
    int32 RunMagicArrowRain(const FString& Params);
    int32 RunBowNetworkReview(const FString& Params);
    int32 RunElementalHoldReview(const FString& Params);
    int32 RunBowResonanceReview(const FString& Params);
    int32 RunBowPresentationReview(const FString& Params);
    int32 RunCompoundStringReview(const FString& Params);
};
