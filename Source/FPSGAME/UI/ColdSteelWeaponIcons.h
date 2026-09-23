#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "PreviewScene.h"
#include "ColdSteelInventoryTypes.h"
#include "FPSPerformanceMetrics.h"
#include "Styling/SlateBrush.h"
#include "ColdSteelWeaponIcons.generated.h"

DECLARE_MULTICAST_DELEGATE_OneParam(FColdSteelWeaponIconReady, const FString&);
struct FFPSIconTaskState;
struct FColdSteelIconReadback;
struct FStreamableHandle;
/** Presentation-only studio. Never equips a player or changes a profile to render an item. */
UCLASS()
class FPSGAME_API UColdSteelWeaponIcons : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual bool IsTickable() const override {return !IsTemplate()&&!Queue.IsEmpty();}
    virtual TStatId GetStatId() const override {RETURN_QUICK_DECLARE_CYCLE_STAT(UColdSteelWeaponIcons,STATGROUP_Tickables);}
    virtual UWorld* GetTickableGameObjectWorld() const override {return GetWorld();}
    bool Supports(const FColdSteelItem& Item) const;
    FString Key(const FColdSteelItem& Item) const;
    void Request(const FColdSteelItem& Item);
    const FSlateBrush* Find(const FColdSteelItem& Item) const;
    FColdSteelWeaponIconReady OnReady;
    int32 RenderCount() const {return Completed;}
    bool IsIdle() const {return Queue.IsEmpty();}
    FFPSIconTaskState GetPerformanceState() const;
#if WITH_EDITOR
    /** Author a base catalog PNG with the same assembly and materials as live inventory icons. */
    bool ExportCatalogIcon(const FString& Definition,const FString& Filename);
#endif
private:
    struct FJob {FColdSteelItem Item;FString Key;double RequestedSeconds=0.0;int32 DeferredAttempts=0;double RetryAfterSeconds=0.0;};
    struct FEntry {FSlateBrush Brush;uint64 Use=0;};
    struct FPreparedBounds {FBox Icon{ForceInit};FBox Pickup{ForceInit};};
    TMap<FString,FPreparedBounds> PreparedBoundsCache;
    TArray<FJob> Queue;
    TSet<FString> Pending,Failed;
    TArray<FFPSIconFailure> RecentFailures;
    FString FailureReason, FailureResource;
    FName FailureStage;
    static constexpr int32 MaxFailureDetails = 32;
    mutable TMap<FString,FEntry> Cache;
    mutable uint64 Serial=0;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<class UTexture2D>> Textures;
    UPROPERTY(Transient) TObjectPtr<class AFPSGAMECharacter> Rig;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> MeleeMesh;
    UPROPERTY(Transient) TObjectPtr<class USceneCaptureComponent2D> Capture;
    UPROPERTY(Transient) TObjectPtr<class UTextureRenderTarget2D> Target;
    UPROPERTY(Transient) TArray<TObjectPtr<class UMeshComponent>> CaptureMeshes;
    UPROPERTY(Transient) TArray<TObjectPtr<class UMaterialInterface>> CaptureMaterials;
    UPROPERTY(Transient) TArray<TObjectPtr<class UTexture>> CaptureTextures;
    TUniquePtr<FPreviewScene> Studio;
    TSharedPtr<FStreamableHandle> ResourceLoad;
    TArray<FSoftObjectPath> RequiredResources;
    int32 PrepareStep=0, AttachmentStep=0, BoundsSection=0;
    uint32 BoundsVertex=0;
    bool bBoundsStarted=false;
    FPreparedBounds WorkingBounds;
    FTransform BoundsIconPose, BoundsPickupPose;
    TArray<FMatrix44f> BoundsBoneMatrices;
    FString RigDefinition;
    // -2: render command pending; -1: ready; >=0: first unready material index.
    TSharedPtr<TAtomic<int32>,ESPMode::ThreadSafe> CaptureMaterialStatus;
    TSharedPtr<FColdSteelIconReadback,ESPMode::ThreadSafe> PendingReadback;
    FName WaitReason;
    FString WaitResource;
    double WaitStartSeconds=0.0;
    int32 ReadinessPolls=0,CaptureSubmissions=0;
    bool bBoundsCacheHit=false;
    float Warmup=0;
    double AttemptStartSeconds=0.0;
    int32 Stage=0,Completed=0;
    bool bCatalogExport=false;
    bool Prepare(const FColdSteelItem& Item);
    void BeginResourceLoad(const FColdSteelItem& Item);
    void ResetPreparation();
    bool PrepareMelee(const FColdSteelItem& Item);
    void BeginReadback(const FString& Key);
    void PollReadback();
    void CancelReadback();
    void ReadbackPerformanceState(FFPSIconTaskState& State) const;
    bool PublishReadback(const FString& Key, const TArray<FColor>& Pixels, int32 Width, int32 Height, int32 Visible);
    void DeferCurrentJob(double Now);
    void FinishJob(bool bSuccess);
    bool SubmitMaterialReadiness();
    void SetWaitState(FName Reason, const FString& Resource = FString());
};
