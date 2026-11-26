#pragma once
#include "Commandlets/Commandlet.h"
#include "SwiftFalconMotionAuditCommandlet.generated.h"

UCLASS()
class USwiftFalconMotionAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
    virtual int32 Main(const FString& Params) override;
};
