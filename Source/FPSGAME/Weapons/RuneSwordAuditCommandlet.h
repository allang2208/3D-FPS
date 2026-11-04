#pragma once
#include "Commandlets/Commandlet.h"
#include "RuneSwordAuditCommandlet.generated.h"

UCLASS()
class URuneSwordAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
private:
    int32 AuditStarMarrowMotion(const FString& Params);
    int32 AuditStarMarrowSurface(const FString& Params);
    int32 CaptureStarMarrowFire(const FString& Params);
    int32 AuditXuanChiRunes();
};
