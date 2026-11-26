#pragma once
#include "Commandlets/Commandlet.h"
#include "GameFramework/PlayerController.h"
#include "SkillNetworkAuditCommandlet.generated.h"

UCLASS()
class ASkillAuditRemoteController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual bool IsLocalController() const override {return false;}
};

UCLASS()
class USkillNetworkAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
    int32 RunSessionSkillsAudit(const FString& Params);
    int32 RunPojunChainPoseAudit();
    int32 RunFlameArmorAudit(const FString& Params);
    int32 RunFlameArmorStatsAudit(const FString& Params);
    int32 RunIceArmorAudit(const FString& Params);
    int32 RunZhufengAudit(const FString& Params);
    int32 RunSkillBatchReview(const FString& Params);
    int32 RunLightningHasteAudit(const FString& Params);
    int32 RunConversationCombatReview(const FString& Params);
    int32 CaptureLightningHaste(const FString& Params);
    int32 RunMeteorReadyPreviewAudit(const FString& Params);
    int32 RunMeteorFormulaNetAudit(const FString& Params);
};
