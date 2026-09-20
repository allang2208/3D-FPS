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
    bool CanAimPreview() const {return HasWorkbenchCapture()&&StandaloneMelee==nullptr&&!IsMeleeWorkbench();}
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
    bool HasSelectedPreview() const;
    void AppendMeleeOverview(const FColdSteelItem& Item);
    TSharedRef<SWidget> BuildWorkbench();
    TSharedRef<SWidget> BuildOption(const FString& SlotKey,const FString& Id);
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
    TSharedPtr<class SWidget> PreviewSurface;
    FVector2D PreviewOrbit=FVector2D::ZeroVector;
    float PreviewZoom=1.f;
    TArray<FGunsmithOverviewRow> Overview;
    FString SelectedCategory=TEXT("magazine");
    FString StatusText;
    bool bCompareFactory=false;
    FDelegateHandle GunsmithHandle,ProfileHandle;
    FSlateBrush BackgroundBrush,PreviewBrush,PanelBrush,RowBrush;
    FButtonStyle NormalButton,SelectedButton,PrimaryButton;
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
