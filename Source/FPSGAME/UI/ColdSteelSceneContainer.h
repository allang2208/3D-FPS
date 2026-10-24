#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ColdSteelSceneContainer.generated.h"

class APlayerController;
class USceneComponent;
class UStaticMeshComponent;

UENUM(BlueprintType)
enum class EColdSteelContainerMotion : uint8
{
    Swing,
    Drawer,
    OpenShelf, // Legacy serialized value; new shelves use Drawer with a real moving part.
    Lid
};

USTRUCT()
struct FColdSteelContainerDoorState
{
    GENERATED_BODY()
    UPROPERTY() bool bValid=false;
    UPROPERTY() float From=0.f;
    UPROPERTY() float To=0.f;
    UPROPERTY() float Started=0.f;
    UPROPERTY() float Duration=.55f;
};

/** Searchable scenery. The searched state lasts for this level visit; tagged
 * apartment doors can close independently of the existing storage session. */
UCLASS(Blueprintable)
class FPSGAME_API AColdSteelSceneContainer : public AActor
{
    GENERATED_BODY()
public:
    AColdSteelSceneContainer();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

    bool TrySearch(APlayerController* Controller);
    void SetViewHighlighted(bool bHighlighted);
    FString GetPromptLabel() const;
    bool IsOpening() const { return bOpening; }
    FString StorageKey() const;
    const FString& LegacyStorageKey() const {return RuntimeStorageKey;}
    bool IsWithinPanelReach(const APlayerController* Controller) const;
    void OpenSharedVisual(bool bInstant=false);
    // Apartment fixtures close when their existing storage panel is dismissed.
    void CloseLootVisual();
    float GetDoorOpenFraction() const;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Container") TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Container") TObjectPtr<USceneComponent> DoorHinge;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Container") TObjectPtr<UStaticMeshComponent> Door;
    /** Stable authored identity within the level, independent of actor display labels. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Container") FString ContainerId;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Container") FString Caption=TEXT("储物柜");
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Container", meta=(ClampMin="1",ClampMax="8")) int32 StoragePages=1;
    UPROPERTY(EditAnywhere, Category="Container", meta=(ClampMin="0.1",ClampMax="3")) float OpeningDuration=.55f;
    UPROPERTY(EditAnywhere, Category="Container") float OpenedYaw=100.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, ReplicatedUsing=OnRep_Searched, Category="Container") bool bSearched=false;

private:
    void ApplyOutline();
    void OpenLootPanel(APlayerController* Controller);
    bool UsesReusableDoor() const;
    void StartReusableDoor(bool bClose);
    UFUNCTION() void OnRep_Searched();
    bool bVisualInitialized=false;
    bool bOpening=false;
    float OpeningElapsed=0.f;
    FRotator ClosedDoorRotation=FRotator::ZeroRotator;
    FString RuntimeStorageKey;
    TWeakObjectPtr<APlayerController> OpeningController;
    FVector ClosedMovingPartLocation=FVector::ZeroVector;

public:
    // Appended to preserve the layout of existing reflected/runtime members.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Container") EColdSteelContainerMotion OpeningMotion=EColdSteelContainerMotion::Swing;
    UPROPERTY(EditAnywhere, Category="Container") FVector DrawerTravel=FVector(0,29,0);
    UPROPERTY(EditAnywhere, Category="Container") float OpenedRoll=105.f;
    /** Authored seeded ajar pose; the container remains unsearched. */
    UPROPERTY(EditAnywhere, Category="Container", meta=(ClampMin="0",ClampMax="1")) float InitialOpenFraction=0.f;

private:
    bool bClosingReusableDoor=false;
    float ReusableDoorFraction=0.f;
    float ReusableDoorStart=0.f;
    UPROPERTY(ReplicatedUsing=OnRep_DoorState) FColdSteelContainerDoorState DoorState;
    UFUNCTION() void OnRep_DoorState();
    float DoorClock() const;
    void ApplyReusableDoor();
};
