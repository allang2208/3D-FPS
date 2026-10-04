#pragma once
#include "Commandlets/Commandlet.h"
#include "M09HitSurfaceAuditCommandlet.generated.h"
UCLASS()
class UM09HitSurfaceAuditCommandlet : public UCommandlet
{
 GENERATED_BODY()
public:
 virtual int32 Main(const FString& Params) override;
};
