#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "IlluminationArrowTypes.h"
#include "IlluminationMarkComponent.generated.h"
class UFPSIlluminationArrowComponent;
class UPrimitiveComponent;
class UMaterialInterface;
struct FStreamableHandle;

/** Target-owned scan mark; authority owns duration, damage and kill attribution. */
UCLASS(ClassGroup=(Skills))
class FPSGAME_API UIlluminationMarkComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UIlluminationMarkComponent();
    static bool Apply(AActor* Target,APawn* Shooter,const FIlluminationArrowCast& Cast);
    /** Show the shared silhouette without applying an arrow debuff or awarding skill XP. */
    static void SetVillageThreat(AActor* Target,bool Active);
    static float DamageBonus(const AActor* Target);
    static bool IsMarked(const AActor* Target);
    static bool HasPresentation(const UWorld* World);
    float Remaining() const;
    void Clear();
    void ObserveKill(const APawn* Killer);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    struct FMark {TWeakObjectPtr<UFPSIlluminationArrowComponent> Source;FGuid CastId;double EndsAt=0;float Bonus=0;};
    TArray<FMark> Marks;
    UPROPERTY(ReplicatedUsing=OnRep_Mark) double MarkEndsAt=0;
    UPROPERTY(Replicated) float MarkBonus=0;
    UPROPERTY(ReplicatedUsing=UpdateOutline) bool bVillageThreat=false;
    UPROPERTY(Transient) TArray<TObjectPtr<UPrimitiveComponent>> Proxies;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> DepthMaterial;
    TSharedPtr<FStreamableHandle> Load;
    bool bLoadRequested=false,bDeathObserved=false,bTracked=false;
    void TrackPresentation(bool Active);
    static UIlluminationMarkComponent* FindOrCreate(AActor* Target);
    UFUNCTION() void OnRep_Mark();
    UFUNCTION() void UpdateOutline();
    void Refresh();
    void Present();
    void RemovePresentation();
    double Clock() const;
};
