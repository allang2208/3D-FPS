#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateBrush.h"
#include "Styling/SlateTypes.h"
#include "PreviewScene.h"
#include "ColdSteelInventoryTypes.h"
#include "M4GunsmithWidget.generated.h"
struct FGunsmithOverviewRow
{
    FString Label,Current,Final,Delta;
    int32 Benefit=0;
};
UCLASS()
class FPSGAME_API UM4GunsmithWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Choose(bool bHolo);
    void ChooseDrum(bool bDrum);
    void ChooseOption(const FString& SlotKey,const FString& Id);
    bool ApplyDraft();
    void UndoDraft();
    void SetAimPreview(bool bAim);
    void SetSidePreview(bool bSide);
    void SelectCategory(const FString& SlotKey);
    void SetCompareFactory(bool bFactory);
    void RefreshPresentation();
    void RotatePreview(FVector2D Delta);
    void ZoomPreview(float WheelDelta);
    FVector2D GetPreviewOrbit() const {return PreviewOrbit;}
    TSharedPtr<class SWidget> GetPreviewSurface() const {return PreviewSurface;}
    const TArray<FGunsmithOverviewRow>& GetOverviewRows() const {return Overview;}
    bool HasWorkbenchCapture() const {return Capture!=nullptr&&PreviewTarget!=nullptr&&(!bStandalone||StandaloneRig!=nullptr||StandaloneMelee!=nullptr);}
    bool CanAimPreview() const {return HasWorkbenchCapture()&&StandaloneMelee==nullptr&&!IsStandaloneWorkbench();}
    void SetStandaloneItem(const FColdSteelItem& Item);
    void TickStandalonePreview(float Delta,TSharedPtr<class SWidget> Surface);
    void CloseStandalonePreview();
    const FSlateBrush* StandaloneBrush()const{return &PreviewBrush;}
    bool IsAimPreview()const{return bAimPreview;}
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual FReply NativeOnKeyDown(const FGeometry&,const FKeyEvent&) override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry&,float Delta) override;
private:
    friend class AFPSGAMEPlayerController;
    friend class AFPSGAMECharacter;
    class UGunsmithSystem* Model() const;
    bool IsMeleeWorkbench() const;
    bool IsBowWorkbench() const;
    bool IsStaffWorkbench() const;
    void AppendStaffOverview(const FColdSteelItem& Item);
    void SetStandaloneStaffItem(const FColdSteelItem& Item);
    void SyncStandaloneStaffPreview();
    void AppendBowOverview(const FColdSteelItem& Item);
    /** 采集工具（伐木斧、矿镐）工作台：数值口径独立，布局沿用近战那套。 */
    bool IsToolWorkbench() const;
    /** 近战与工具都不绑定角色装备栏，统一走独立网格预览。 */
    bool IsStandaloneWorkbench() const;
    bool HasSelectedPreview() const;
    void AppendMeleeOverview(const FColdSteelItem& Item);
    void AppendToolOverview(const FColdSteelItem& Item);
    /** 右侧总览「强化」段：排在「采集」「自卫」之后，全部为外观行，无数值。 */
    void AppendToolEnhanceOverview(const FColdSteelItem& Item);
    TSharedRef<SWidget> BuildWorkbench();
    TSharedRef<SWidget> BuildOption(const FString& SlotKey,const FString& Id);
    /** 底部选项区标题：「强化」不是改造槽、不在 Slots() 里，不能靠 IndexOfByKey 反查，必须显式给。 */
    FString OptionsTitle() const;
    int32 OptionsCount() const;
    /** 强化档位卡：等级序号＋材质名＋一句外观说明＋角标（已装备／可强化／需先强化到 Lv.N）。 */
    TSharedRef<SWidget> BuildEnhanceCard(int32 Level);
    /** 重建底部档位卡列表；仅在选中「强化」栏目时由 RefreshEnhanceOptions 调用。 */
    void RefreshEnhanceOptions();
    /** 选中某个档位（只有当前+1 会被模型接受，其余在卡片上已禁用）。 */
    void ChooseEnhanceLevel(int32 Level);
    /** 中央预览按草稿等级即时换金属材质；草稿为 0 时用实例等级。 */
    void SyncEnhancePreview();
    /** 右侧详情区：所选档位名、外观说明、「消耗 待定」「数值 本次不影响」。 */
    void AppendEnhanceDetails(int32 Level);
    /** 档位卡列表的草稿／预览是否需要重建（等级或草稿变化才为真）。 */
    bool EnhanceOptionsDirty() const;
    bool IsCategoryAvailable(const FString& SlotKey) const;
    void RefreshSelectedOption();
    float SelectedDetailsWidth() const;
    float OverviewSectionHeight() const;
    void UpdateResponsiveLayout();
    TSharedRef<SWidget> GlassPanel(TSharedRef<SWidget> Content,FMargin Padding=FMargin(14));
    void LoadCategoryIcons();
    FString CategoryPartName(const FString& SlotKey) const;
    void InitializePreview();
    void ReleasePreview();
    void SyncStudioPreview();
    void UpdatePreviewStreaming(float Delta);
    void CapturePreview();
    void TickCapture(float Delta);
    void PoseStandalone();
    void SetStandaloneMeleeItem(const FColdSteelItem& Item);
    void SetStandaloneBowItem(const FColdSteelItem& Item);
    void SyncStandaloneBowPreview();
    TSharedPtr<struct FStreamableHandle> BowPreviewLoad;
    FString BowPreviewInputKey;
    /** LevelOverride>0 时按草稿等级预览金属材质（阶段 1-C）；默认 0＝用实例等级。 */
    void SetStandaloneToolItem(const FColdSteelItem& Item,int32 LevelOverride=0);
    void SyncStandaloneMeleePreview();
    bool bStandalone=false;
    FString StandaloneKey;
    TMap<FString,FString> StandaloneParts;
    UPROPERTY(Transient) TObjectPtr<class AFPSGAMECharacter> StandaloneRig;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> StandaloneMelee;
    TUniquePtr<FPreviewScene> Studio;
    TMap<TWeakObjectPtr<class UPrimitiveComponent>,class UMeshComponent*> StudioCopies;
    struct FPreviewBoundsCache { uint32 Signature=0; FBox Box=FBox(ForceInit); };
    TMap<TWeakObjectPtr<class UPrimitiveComponent>,FPreviewBoundsCache> PreviewBoundsCache;
    FBox PreviewFramingBounds=FBox(ForceInit);
    class UDirectionalLightComponent* StudioFill=nullptr;
    TSharedPtr<class SVerticalBox> ModificationList,OverviewList;
    TSharedPtr<class SBox> BodyHost;
    TSharedPtr<class SWidget> RailContent,CenterContent,InspectorContent,FooterContent;
    TSharedPtr<class SScrollBox> CategoryScroll,OverviewScroll,BodyScroll,InspectorScroll;
    TMap<FString,TSharedPtr<class SWidget>> CategoryButtons;
    TMap<FString,TSharedPtr<FSlateBrush>> CategoryBrushes;
    TMap<FString,TSharedPtr<FSlateBrush>> AttachmentBrushes;
    UPROPERTY(Transient) TArray<TObjectPtr<class UTexture2D>> AttachmentTextures;
    UPROPERTY(Transient) TArray<TObjectPtr<class UTexture2D>> CategoryTextures;
    UPROPERTY(Transient) TArray<TObjectPtr<class UMaterialInstanceDynamic>> CategoryMaterials;
    int32 LayoutMode=-1;
    float RailWidth=208.f,InspectorWidth=560.f;
    TArray<TSharedPtr<class SBackgroundBlur>> GlassLayers;
    FSlateBrush GlassFallback,CategoryButtonBrush,OptionFrameBrush;
    TSharedPtr<class SScrollBox> OptionScroll;
    TMap<FString,TSharedPtr<class SWidget>> OptionCards;
    FString OptionsSignature,OptionsCategory;
    FString InspectedOptionKey;
    /** 底部档位卡的内存键（含草稿等级）与上一次中央预览用的草稿等级。 */
    FString EnhanceSignature;
    int32 PreviewEnhanceLevel=-1;
    TSharedPtr<class SWidget> PreviewSurface;
    FVector2D PreviewOrbit=FVector2D::ZeroVector;
    float PreviewZoom=1.f;
    TArray<FGunsmithOverviewRow> Overview;
    FString SelectedCategory=TEXT("magazine");
    FString StatusText;
    bool bCompareFactory=false;
    FDelegateHandle GunsmithHandle,ProfileHandle;
    FSlateBrush BackgroundBrush,PreviewBrush,PanelBrush,RowBrush;
    FButtonStyle NormalButton,SelectedButton,PrimaryButton,ExclusiveButton;
    UPROPERTY() TObjectPtr<class UTexture2D> BackgroundTexture;
    UPROPERTY() TObjectPtr<class UTextureRenderTarget2D> PreviewTarget;
    UPROPERTY() TObjectPtr<class UTextureRenderTarget2D> PreviewCoverageTarget;
    UPROPERTY() TObjectPtr<class UMaterialInstanceDynamic> PreviewMaterial;
    UPROPERTY() TObjectPtr<class USceneCaptureComponent2D> Capture;
    UPROPERTY() TObjectPtr<class USceneCaptureComponent2D> PreviewCoverageCapture;
    TArray<TWeakObjectPtr<class UTexture2D>> PreviewStreamedTextures;
    float PreviewStreamingAccumulator=1.f;
    bool bPreviewStreamingDirty=true;
    bool bPreviewStreamingPending=false;
    float CaptureAccumulator=0;
    float PreviewMotion=1.f;
    bool bAimPreview=false;
    bool bSidePreview=false;
};
