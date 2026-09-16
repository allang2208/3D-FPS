#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "VoxelBuildWidget.generated.h"

class UBackgroundBlur;
class UBorder;
class UButton;
class UCanvasPanelSlot;
class UScrollBox;
class UTextBlock;
class UVerticalBox;
class UVoxelBuildWidget;

/** One selectable entry in the building drawer: a material or a placeable component. */
struct FVoxelBuildPanelCard
{
    FName Id;
    FString Caption;
    FString Detail;
    bool bComponent=false;
    /** Tooltip card, same layout as the equipment tooltip: subtitle, rows, section headings. */
    FString Subtitle;
    TArray<TPair<FString,FString>> Rows;
    FString Note;
};

/** Carries the clicked card's identity; UButton::OnClicked has no sender argument. */
UCLASS()
class FPSGAME_API UVoxelBuildCardProxy : public UObject
{
    GENERATED_BODY()
public:
    FName CardId;
    bool bComponentCard=false;
    int32 CardIndex=INDEX_NONE;
    TWeakObjectPtr<UVoxelBuildWidget> Panel;
    UFUNCTION() void Clicked();
    UFUNCTION() void Hovered();
    UFUNCTION() void Unhovered();
};

/** Right-hand building drawer: materials, components and the live build state. */
UCLASS()
class FPSGAME_API UVoxelBuildWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void ShowState(const FString& Headline,const FString& Brush,const FString& Message,bool bValid,bool bSnapEnabled);
    void SetContent(const TArray<FVoxelBuildPanelCard>& Materials,const TArray<FVoxelBuildPanelCard>& Components);
    void SetSelection(FName Material,FName Component);
    void SetDrawerOpen(bool Open);
    void Pick(FName Id,bool bComponent);
    void ShowTooltip(int32 CardIndex);
    void HideTooltip(bool bForce=false);
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry& Geometry,float Delta) override;
    virtual FReply NativeOnKeyDown(const FGeometry& Geometry,const FKeyEvent& Event) override;
private:
    struct FLabel {TWeakObjectPtr<UTextBlock> Widget;float Pixels=12;bool Numeric=false,Medium=false;};
    struct FCard {FName Id;bool bComponent=false;TWeakObjectPtr<UButton> Button;TWeakObjectPtr<UBorder> Surface;};
    UPROPERTY() TObjectPtr<UBorder> Surface;
    UPROPERTY() TObjectPtr<UBackgroundBlur> Blur;
    UPROPERTY() TObjectPtr<UCanvasPanelSlot> PanelSlot;
    UPROPERTY() TObjectPtr<UTextBlock> Title;
    UPROPERTY() TObjectPtr<UTextBlock> Selection;
    UPROPERTY() TObjectPtr<UTextBlock> Status;
    UPROPERTY() TObjectPtr<UTextBlock> Structure;
    UPROPERTY() TObjectPtr<UTextBlock> Controls;
    UPROPERTY() TObjectPtr<UButton> MaterialTab;
    UPROPERTY() TObjectPtr<UButton> ComponentTab;
    UPROPERTY() TObjectPtr<UScrollBox> Scroll;
    UPROPERTY() TObjectPtr<UVerticalBox> CardList;
    UPROPERTY() TArray<TObjectPtr<UVoxelBuildCardProxy>> CardProxies;
    UPROPERTY() TObjectPtr<UBorder> TooltipCard;
    UPROPERTY() TObjectPtr<UCanvasPanelSlot> TooltipSlot;
    UPROPERTY() TObjectPtr<UVerticalBox> TooltipBox;
    UPROPERTY() TObjectPtr<UTextBlock> TooltipTitle;
    UPROPERTY() TObjectPtr<UTextBlock> TooltipSubtitle;
    int32 TooltipIndex=INDEX_NONE;
    TArray<FLabel> Labels;
    TArray<FCard> Cards;
    TArray<FVoxelBuildPanelCard> MaterialCards,ComponentCards;
    FName SelectedMaterial,SelectedComponent;
    FString LastState;
    FVector2D LastViewport=FVector2D::ZeroVector;
    float LastScale=0,DrawerProgress=0,DrawerWidth=0;
    bool bDrawerOpen=false,bComponentCategory=false,bCardsDirty=true,bSelectionDirty=true;
    UTextBlock* Text(const FString& Caption,float Pixels,bool Numeric=false,bool Medium=false,bool bTrack=true);
    UButton* Tab(const FString& Caption,bool bComponents);
    class UVoxelBuildComponent* Builder() const;
    void BuildTooltipCard();
    void UpdateTooltipPlacement();
    UFUNCTION() void CloseTooltip();
    void RebuildCards();
    void RefreshSelection();
    void RefreshCategory();
    void RefreshLayout();
    UFUNCTION() void ShowMaterialCategory();
    UFUNCTION() void ShowComponentCategory();
};
