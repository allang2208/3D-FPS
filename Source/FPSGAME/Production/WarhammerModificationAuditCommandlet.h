#pragma once
#include "Commandlets/Commandlet.h"
#include "GameFramework/PlayerController.h"
#include "WarhammerModificationAuditCommandlet.generated.h"

/** An isolated authority fixture; no client connection or user profile is opened. */
UCLASS(Transient,NotBlueprintable)
class AWarhammerAuditRemoteController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual bool IsLocalController() const override { return false; }
};

UCLASS()
class UWarhammerModificationAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
    UFUNCTION(BlueprintCallable, Category="Weapon|AssetBuild")
    static bool RepairSeatTangentBasis(class UStaticMesh* Mesh);
private:
    int32 AuditHeavyFormula(const FString& Params);
    int32 AuditZhenTing(const FString& Params);
};
