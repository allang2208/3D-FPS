#pragma once

#include "CoreMinimal.h"
#include "UObject/SoftObjectPath.h"

class UColdSteelStatusModel;
class AActor;
class FPlayerSkillRenderPreparation;
struct FColdSteelProfile;
struct FStreamableHandle;

namespace PlayerSkillAssets
{
    void Gather(FName Skill, const FColdSteelProfile& Profile, TArray<FSoftObjectPath>& Out);
    /** Local player binds through the ordered post-entry queue; other pawns load asynchronously. */
    void Defer(AActor* Owner,FName Skill,FSimpleDelegate Ready,const TArray<FSoftObjectPath>& ExtraPaths={});
    template<class T> T* Resolve(const TCHAR* Path) { return Cast<T>(FSoftObjectPath(Path).ResolveObject()); }
}

/** Ordered background loading after entry. Never a condition for releasing gameplay. */
class FPlayerSkillPreparation
{
public:
    ~FPlayerSkillPreparation();
    void Begin(UColdSteelStatusModel& Model);
    void RegisterConsumer(AActor* Owner,FName Skill,FSimpleDelegate Ready,const TArray<FSoftObjectPath>& ExtraPaths);
    void Tick();
    void Cancel();
    bool IsReady() const { return bStarted && !bRefreshRequested && !bEquipmentCheckPending && Cursor == Jobs.Num()
        && DeferredRenderPaths.IsEmpty() && !bWarhammerPreparationPending; }
    bool HasFailed() const { return bFailed; }
    FText Status;
    float Progress = 0.f;

private:
    friend class UBowSkillTrainingAuditCommandlet;
    struct FJob
    {
        FName Skill;
        FString Name;
        bool bMagic = false;
        bool bGathered = false,bHadFailures = false;
        TArray<FSoftObjectPath> Paths;
    };
    void Fail(const FString& Reason);
    void RefreshLearnedSkills();
    void BindConsumers(FName Skill);
    void ReleaseUnusedResidents();
    void RecordResourceState(const UObject* Context, const TCHAR* Phase) const;
    bool CanPrepareRender();
    void TickDeferredRender();
    void CheckEquipmentChanges();
    struct FConsumer
    {
        TWeakObjectPtr<AActor> Owner;
        FName Skill;
        FSimpleDelegate Ready;
        TArray<FSoftObjectPath> ExtraPaths;
    };
    TArray<FConsumer> Consumers;
    TWeakObjectPtr<UColdSteelStatusModel> Model;
    FDelegateHandle ChangedHandle;
    TSet<FName> KnownSkills,ReadySkills;
    TSet<FSoftObjectPath> RenderPrepared;
    TSharedPtr<FPlayerSkillRenderPreparation> RenderPreparation;
    bool bRefreshRequested=false,bBindingsDelivered=false;
    double BindingsStartedAt=0;
    TArray<FJob> Jobs;
    // One handle per loaded resource, deduplicated across skills and map travel.
    TMap<FSoftObjectPath,TSharedPtr<FStreamableHandle>> Residents;
    TSet<FSoftObjectPath> Prepared;
    TSharedPtr<FStreamableHandle> Pending;
    int32 Cursor = 0, AssetCursor = 0;
    double JobStartedAt = 0.;
    bool bStarted = false, bFailed = false, bAssetPreparationStarted = false, bPSORequested = false;
    bool bResidentCleanupPending = false;
    TArray<FSoftObjectPath> DeferredRenderPaths;
    bool bWarhammerPreparationPending=false,bRenderAdmissionPaused=false;
    double NextRenderAdmissionSeconds=0.,DeferredRenderStartedAt=0.;
    TArray<FString> CarriedEquipmentSignature;
    bool bEquipmentCheckPending=false;
    double NextEquipmentCheckSeconds=0.;
};
