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
class UColdSteelHUDWidget;

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
    TSoftClassPtr<AActor> IconActorClass;
    FVector IconPivotOffsetCm=FVector::ZeroVector;
    /** Tooltip card, same layout as the equipment tooltip: subtitle, rows, section headings. */
    FString Subtitle;
    TArray<TPair<FString,FString>> Rows;
    /** Only measurement rows use the numeric font; descriptions keep the UI font. */
    TSet<FString> NumericRows;
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
    /** 与背包装备同一让位规则：抽屉出现期间右侧入口列、世界时钟与右下武器详情收起。 */
    void SetHudYielded(bool bYielded);
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeDestruct() override;
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
        /** 建卡时的缩略图请求：缓存被回收后按同一份参数重新排队。 */
        FVoxelBuildIconRequest IconRequest;
        TWeakObjectPtr<UButton> Button;
        TWeakObjectPtr<UBorder> Surface;
        TWeakObjectPtr<UImage> Image;
        TWeakObjectPtr<USizeBox> Box;
        TWeakObjectPtr<USizeBox> IconBox;
        /** 网格卡（其他构造卡片）：DPI/视口变化时按网格尺寸重排；材质行等行式条目不吃这套尺寸。 */
        bool bGridCard=false;
        TWeakObjectPtr<UTextBlock> Placeholder;
    };
    UPROPERTY() TObjectPtr<UBorder> Surface;
    /** 全屏 40% 压暗底：与背包装备同一抽屉规格，随进度淡入淡出（2026-09-19 补齐）。 */
    UPROPERTY() TObjectPtr<UBorder> Backdrop;
    UPROPERTY() TObjectPtr<UBackgroundBlur> Blur;
    UPROPERTY() TObjectPtr<UBorder> GlassTintPanel;
    UPROPERTY() TObjectPtr<UBorder> HeaderPanel;
    UPROPERTY() TObjectPtr<USizeBox> HeaderSize;
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
    UPROPERTY() TObjectPtr<UScrollBox> TooltipScroll;
    UPROPERTY() TObjectPtr<UTextBlock> TooltipTitle;
    UPROPERTY() TObjectPtr<UTextBlock> TooltipSubtitle;
    int32 TooltipIndex=INDEX_NONE;
    /** 跟随一小段时间后钉住位置（停止跟随），关闭按钮才够得到；钉住后指针离开浮窗与来源卡片才收起。 */
    bool bTooltipPinned=false;
    /** 当前这张浮窗第一次显示的时间；跟随一小段时间后自动钉住。 */
    float TooltipShownAtSeconds=-1.f;
    /** 页签文字：字重随选中态在 RefreshCategory 里按当前 Scale 设置，不走 Text() 的 DPI 托管。 */
    TWeakObjectPtr<UTextBlock> MaterialTabLabel,ComponentTabLabel;
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
    /** 卡片重建后需要把新的缩略图键集合交给图标子系统（正在显示的键不参与回收）。 */
    bool bIconPinsDirty=true;
    /** HUD 让位是否已置位：打开即置位，收回动画播完或销毁时复位。 */
    bool bHudYielded=false;
    UTextBlock* Text(const FString& Caption,float Pixels,bool Numeric=false,bool Medium=false,bool bTrack=true);
    UButton* Tab(const FString& Caption,bool bComponents);
    class UVoxelBuildComponent* Builder() const;
    class UColdSteelHUDWidget* ResolveHUD() const;
    /** 指针是否落在目标控件几何内（Margin 为附加余量，控件局部单位）。 */
    bool PointerWithin(UWidget* Target,float Margin) const;
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
    /** 把当前卡片的缩略图键交给图标子系统，声明它们是「正在显示、不参与回收」。 */
    void RefreshIconPins();
    void RebuildCards();
    void RefreshSelection();
    void RefreshCategory();
    void RefreshLayout();
    UFUNCTION() void ShowMaterialCategory();
    UFUNCTION() void ShowComponentCategory();
};
