#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Subsystems/WorldSubsystem.h"
#include "StatusEffectsComponent.h"
#include "StatusEffectsHUD.generated.h"
class UBorder;class UTextBlock;class UImage;class UCanvasPanel;class UCanvasPanelSlot;class UWrapBox;class UScrollBox;class UStatusEffectsHUD;

UCLASS()
class FPSGAME_API UStatusEffectTile : public UUserWidget
{
 GENERATED_BODY()
public:
 void Update(const FStatusEffectView& InView);FStatusEffectView View;
 TWeakObjectPtr<UStatusEffectsHUD> HUD;
protected:
 virtual void NativeOnInitialized() override;
 virtual void NativeOnMouseEnter(const FGeometry& Geometry,const FPointerEvent& Event) override;
 virtual void NativeOnMouseLeave(const FPointerEvent& Event) override;
private:
 UPROPERTY(Transient) TObjectPtr<UBorder> Surface;
 UPROPERTY(Transient) TObjectPtr<UTextBlock> Icon;
 UPROPERTY(Transient) TObjectPtr<UTextBlock> StackText;
 UPROPERTY(Transient) TObjectPtr<UTextBlock> TimeText;
 UPROPERTY(Transient) TObjectPtr<UImage> Progress;
 bool Hover=false;
};

UCLASS()
class FPSGAME_API UStatusEffectsHUD : public UUserWidget
{
 GENERATED_BODY()
public:
 void BindPawn(APawn* Pawn);void Refresh();void ShowTip(UStatusEffectTile* Tile);void HideTip();
 int32 VisibleEffectCount() const {return Tiles.Num();}
 bool IsTipVisible() const;
 FName TooltipType() const;
 FVector2D TooltipPosition() const;
 UStatusEffectTile* TileFor(FName Type) const;
protected:
 virtual void NativeOnInitialized() override;
 virtual TSharedRef<SWidget> RebuildWidget() override;
 virtual void NativeDestruct() override;
 virtual void NativeTick(const FGeometry& Geometry,float Dt) override;
private:
 UPROPERTY(Transient) TObjectPtr<UCanvasPanel> Root;
 UPROPERTY(Transient) TObjectPtr<UWrapBox> Wrap;
 UPROPERTY(Transient) TObjectPtr<UScrollBox> Scroll;
 UPROPERTY(Transient) TObjectPtr<UBorder> Tooltip;
 UPROPERTY(Transient) TObjectPtr<UTextBlock> TipTitle;
 UPROPERTY(Transient) TObjectPtr<UTextBlock> TipDescription;
 UPROPERTY(Transient) TObjectPtr<UTextBlock> TipStacks;
 UPROPERTY(Transient) TObjectPtr<UTextBlock> TipTime;
 UPROPERTY(Transient) TArray<TObjectPtr<UStatusEffectTile>> Tiles;
 TWeakObjectPtr<UStatusEffectsComponent> Source;TWeakObjectPtr<UStatusEffectTile> HoverTile;
 FDelegateHandle Changed;float Clock=0;
};

/** Owns one passive HUD per game world and rebinds after possession/respawn. */
UCLASS()
class FPSGAME_API UStatusEffectsHUDSubsystem : public UWorldSubsystem
{
 GENERATED_BODY()
public:
 virtual void OnWorldBeginPlay(UWorld& World) override;
 virtual void Deinitialize() override;
 UStatusEffectsHUD* GetHUD() const {return HUD;}
private:
 void EnsureHUD();FTimerHandle Timer;TWeakObjectPtr<APawn> BoundPawn;
 UPROPERTY(Transient) TObjectPtr<UStatusEffectsHUD> HUD;
};
