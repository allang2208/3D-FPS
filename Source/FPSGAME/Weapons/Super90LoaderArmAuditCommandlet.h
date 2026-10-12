#pragma once
#include "Commandlets/Commandlet.h"
#include "Super90LoaderArmAuditCommandlet.generated.h"

// Read-only offline capture of the production pose graph, including support IK.
UCLASS()
class USuper90LoaderArmAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
    UFUNCTION(BlueprintCallable, Category="Super90|Audit")
    static bool Capture(const FString& Directory);
};
