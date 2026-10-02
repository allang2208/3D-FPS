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
    OpenShelf // Legacy serialized value; new shelves use Drawer with a real moving part.
};

/** Searchable scenery. Door and searched state last for this level visit;
 *  the existing chest loot drawer owns the independent item storage session. */
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

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Container") TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Container") TObjectPtr<USceneComponent> DoorHinge;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Container") TObjectPtr<UStaticMeshComponent> Door;
    /** Stable authored identity within the level, independent of actor display labels. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Container") FString ContainerId;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Container") FString Caption=TEXT("储物柜");
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Container", meta=(ClampMin="1",ClampMax="8")) int32 StoragePages=1;
    UPROPERTY(EditAnywhere, Category="Container", meta=(ClampMin="0.1",ClampMax="3")) float OpeningDuration=.55f;
    UPROPERTY(EditAnywhere, Category="Container") float OpenedYaw=100.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Container") bool bSearched=false;

private:
    void ApplyOutline();
    void OpenLootPanel(APlayerController* Controller);
    bool IsWithinPanelReach(const APlayerController* Controller) const;
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
};
