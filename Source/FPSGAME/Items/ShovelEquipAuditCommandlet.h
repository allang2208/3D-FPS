#pragma once
#include "Commandlets/Commandlet.h"
#include "ShovelEquipAuditCommandlet.generated.h"

/** Offline shovel equip chain audit (no PIE/rendering). See the .cpp. */
UCLASS()
class UShovelEquipAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
private:
    static void WriteReport(const TArray<FString>& Report, const FString& Profile);
};
