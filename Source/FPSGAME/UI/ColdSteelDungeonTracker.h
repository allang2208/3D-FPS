#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "../Tasks/TaskTrackingSubsystem.h"
#include "ColdSteelDungeonTracker.generated.h"

class UCanvasPanel;
class UCanvasPanelSlot;
class UTextBlock;
class UVerticalBox;
class USizeBox;
class UScrollBox;

/** One stable objective, with an independent completion stroke. */
UCLASS()
class FPSGAME_API UColdSteelTrackedObjectiveRow : public UUserWidget
{
    GENERATED_BODY()
public:
    void ApplyView(const FTrackedObjectiveView& View, bool bNewInstance);
    FName ObjectiveId() const { return Id; }
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;
    virtual int32 NativePaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& Clip,
        FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle& Style, bool Enabled) const override;
private:
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Label;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Counter;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Hint;
    FName Id;
    ETrackedObjectiveState State = ETrackedObjectiveState::Active;
    bool bInitialized = false;
    float StrikeProgress = 0.f;
};

/** Reconciles objectives by ID; wording and ordering never identify a goal. */
UCLASS()
class FPSGAME_API UColdSteelTrackedTaskCard : public UUserWidget
{
    GENERATED_BODY()
public:
    void ApplyView(const FTrackedTaskView& View);
    FName TaskId() const { return Id; }
protected:
    virtual void NativeOnInitialized() override;
private:
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Title;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Area;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Stage;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Hint;
    UPROPERTY(Transient) TObjectPtr<UVerticalBox> Objectives;
    UPROPERTY(Transient) TArray<TObjectPtr<UColdSteelTrackedObjectiveRow>> Rows;
    FName Id;
    FString InstanceId;
};

/** Historical class name retained; now displays all registered task sources. */
UCLASS()
class FPSGAME_API UColdSteelDungeonTracker : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetBottomBoundaryPixels(float Value){BottomBoundaryPixels=Value;RefreshAge=.2f;}
protected:
    virtual void NativeOnInitialized() override;
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;
private:
    void RefreshTracking();
    void UpdatePlacement();
    UPROPERTY(Transient) TObjectPtr<UCanvasPanel> Root;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> ListSlot;
    UPROPERTY(Transient) TObjectPtr<USizeBox> ListSize;
    UPROPERTY(Transient) TObjectPtr<UScrollBox> Scroll;
    UPROPERTY(Transient) TObjectPtr<UVerticalBox> TaskList;
    UPROPERTY(Transient) TArray<TObjectPtr<UColdSteelTrackedTaskCard>> Cards;
    float RefreshAge = .2f;
    float BottomBoundaryPixels=MAX_flt;
    FVector2D LastPosition = FVector2D(-1, -1);
    FVector2D LastBounds = FVector2D(-1, -1);
};
