#pragma once
#include "Commandlets/Commandlet.h"
#include "ShotgunAttachmentAuditCommandlet.generated.h"

UCLASS()
class UShotgunAttachmentAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
    int32 RunM870PresentationAudit(const FString& Params);
    int32 RunSaiga12KPresentationAudit(const FString& Params);
    int32 RunSaiga12KNetworkAudit(const FString& Params);
    int32 RunSVCHReview(const FString& Params);
    int32 RunPistolBodyReview(const FString& Params);
    int32 RunAnimationHandoffAudit(const FString& Params);
    int32 RunPistolAmmoAudit(const FString& Params);
};
