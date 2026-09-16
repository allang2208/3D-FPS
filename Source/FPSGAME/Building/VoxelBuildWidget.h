#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "VoxelBuildIcons.h"
#include "VoxelBuildWidget.generated.h"

class UBackgroundBlur;
class UBorder;
class UButton;
class UCanvasPanelSlot;
class UImage;
class UScrollBox;
class USizeBox;
class UStaticMesh;
class UTextBlock;
class UVerticalBox;
class UVoxelBuildWidget;
class UMaterialInterface;
class UWrapBox;

/** One selectable entry in the building drawer: a material row, a voxel construction or a component. */
struct FVoxelBuildPanelCard
{
    FName Id;
    FString Caption;
    FString Detail;
    bool bComponent=false;
    /** >= 0: a voxel construction shape listed under a material's 其他构造 submenu. */
    int32 ShapeMode=INDEX_NONE;
    /** Material row that opens the 其他构造 submenu (shapes plus same-material components). */
    bool bExpandable=false;
    /** Palette material a component is grouped under; None keeps it in the 其他 category only. */
    FName MaterialId;
    /** Thumbnail source: shapes list their cells, components carry their mesh and pivot offset. */
    TArray<FIntVector> IconCells;
    TSoftObjectPtr<UStaticMesh> IconMesh;
    TSoftObjectPtr<UMaterialInterface> IconSurface;
    FVector IconPivotOffsetCm=FVector::ZeroVector;
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
    /** >= 0: the row is a voxel construction shape belonging to CardId's material. */
    int32 ShapeMode=INDEX_NONE;
    /** Disclosure row: clicking expands or collapses a material's 其他构造 submenu. */
    bool bToggleCard=false;
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
    /** StructureRisk 是最弱接缝占比（1.0 = 断裂）；≥0.85 时状态区显示分级预警。 */
    void ShowState(const FString& Headline,const FString& Brush,const FString& Message,bool bValid,bool bSnapEnabled,
        float StructureRisk=0.f,const FString& StructureSummary=FString());
    void SetContent(const TArray<FVoxelBuildPanelCard>& Materials,const TArray<FVoxelBuildPanelCard>& Shapes,
        const TArray<FVoxelBuildPanelCard>& Components);
    void SetSelection(FName Material,FName Component,int32 ShapeMode);
    void SetDrawerOpen(bool Open);
    void Pick(FName Id,bool bComponent,int32 ShapeMode=INDEX_NONE);
    /** Expands or collapses one material row's 其他构造 submenu. */
    void ToggleMaterial(FName MaterialId);
    void ShowTooltip(int32 CardIndex);
    void HideTooltip(bool bForce=false);
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry& Geometry,float Delta) override;
    virtual FReply NativeOnKeyDown(const FGeometry& Geometry,const FKeyEvent& Event) override;
private:
    struct FLabel {TWeakObjectPtr<UTextBlock> Widget;float Pixels=12;bool Numeric=false,Medium=false;};
    struct FCard
    {
        FName Id;
        bool bComponent=false;
        int32 ShapeMode=INDEX_NONE;
        /** Submenu row of a material: darker surface and smaller radius. */
        bool bChild=false;
        /** Cached drawer thumbnail for this card; empty when the entry has no preview. */
        FString IconKey;
        TWeakObjectPtr<UButton> Button;
        TWeakObjectPtr<UBorder> Surface;
        TWeakObjectPtr<UImage> Image;
        TWeakObjectPtr<USizeBox> Box;
        TWeakObjectPtr<USizeBox> IconBox;
    };
    UPROPERTY() TObjectPtr<UBorder> Surface;
    UPROPERTY() TObjectPtr<UBackgroundBlur> Blur;
    UPROPERTY() TObjectPtr<UCanvasPanelSlot> PanelSlot;
    UPROPERTY() TObjectPtr<UTextBlock> Title;
    UPROPERTY() TObjectPtr<UTextBlock> Selection;
    UPROPERTY() TObjectPtr<UTextBlock> Status;
    UPROPERTY() TObjectPtr<UTextBlock> Structure;
    UPROPERTY() TObjectPtr<UTextBlock> Risk;
    UPROPERTY() TObjectPtr<UTextBlock> Controls;
    UPROPERTY() TObjectPtr<UButton> MaterialTab;
    UPROPERTY() TObjectPtr<UButton> ComponentTab;
    UPROPERTY() TObjectPtr<UScrollBox> Scroll;
    UPROPERTY() TObjectPtr<UVerticalBox> CardList;
    UPROPERTY() TArray<TObjectPtr<UVoxelBuildCardProxy>> CardProxies;
    /** Wrap grids of the current rebuild, re-spaced when DPI or viewport changes. */
    TArray<TWeakObjectPtr<UWrapBox>> Grids;
    UPROPERTY() TObjectPtr<UBorder> TooltipCard;
    UPROPERTY() TObjectPtr<UCanvasPanelSlot> TooltipSlot;
    UPROPERTY() TObjectPtr<UVerticalBox> TooltipBox;
    UPROPERTY() TObjectPtr<UTextBlock> TooltipTitle;
    UPROPERTY() TObjectPtr<UTextBlock> TooltipSubtitle;
    int32 TooltipIndex=INDEX_NONE;
    TArray<FLabel> Labels;
    TArray<FCard> Cards;
    /** Visible rows in list order; ShowTooltip reads the same index as Cards. */
    TArray<FVoxelBuildPanelCard> VisibleCards;
    TArray<FVoxelBuildPanelCard> MaterialCards,ShapeCards,ComponentCards;
    /** Expanded material rows; kept across open/close so the drawer returns to the same submenu. */
    TSet<FName> ExpandedMaterials;
    FName SelectedMaterial,SelectedComponent;
    int32 SelectedShape=0;
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
    UButton* DisclosureButton(FName MaterialId,bool bExpanded);
    void AddMaterialRow(const FVoxelBuildPanelCard& Entry);
    /** One thumbnail card: same size, same spacing, image plus name; wraps when a row is full. */
    void AddGridCard(UWrapBox* Grid,const FVoxelBuildPanelCard& Entry,FName MaterialId,bool bChild,
        const FVoxelBuildPanelCard* MaterialRow);
    class UVoxelBuildIcons* IconsFor() const;
    void RefreshIcons();
    void RebuildCards();
    void RefreshSelection();
    void RefreshCategory();
    void RefreshLayout();
    UFUNCTION() void ShowMaterialCategory();
    UFUNCTION() void ShowComponentCategory();
};
