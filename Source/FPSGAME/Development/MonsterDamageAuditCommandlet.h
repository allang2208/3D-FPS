#pragma once
#include "Commandlets/Commandlet.h"
#include "MonsterDamageAuditCommandlet.generated.h"

// Data-only audit: isolated profile, no BeginPlay, world tick, combat or rendering.
UCLASS()
class UMonsterDamageAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
