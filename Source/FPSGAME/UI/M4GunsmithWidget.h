#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateBrush.h"
#include "Styling/SlateTypes.h"
#include "PreviewScene.h"
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
    void SetAimPreview(bool bAim);
    void SetSidePreview(bool bSide);
    void SelectCategory(const FString& SlotKey);
    void SetCompareFactory(bool bFactory);
    void RefreshPresentation();
    void RotatePreview(FVector2D Delta);
    FVector2D GetPreviewOrbit() const {return PreviewOrbit;}
    TSharedPtr<class SWidget> GetPreviewSurface() const {return PreviewSurface;}
    const TArray<FGunsmithOverviewRow>& GetOverviewRows() const {return Overview;}
    bool HasWorkbenchCapture() const {return Capture!=nullptr&&PreviewTarget!=nullptr;}
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual FReply NativeOnKeyDown(const FGeometry&,const FKeyEvent&) override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry&,float Delta) override;
private:
    friend class AFPSGAMEPlayerController;
    class UGunsmithSystem* Model() const;
    TSharedRef<SWidget> BuildWorkbench();
    TSharedRef<SWidget> BuildOption(const FString& SlotKey,const FString& Id);
    void InitializePreview();
    void ReleasePreview();
    void SyncStudioPreview();
    TUniquePtr<FPreviewScene> Studio;
    TMap<TWeakObjectPtr<class UPrimitiveComponent>,class UMeshComponent*> StudioCopies;
    class UDirectionalLightComponent* StudioFill=nullptr;
    TSharedPtr<class SVerticalBox> ModificationList,OverviewList;
    TSharedPtr<class SScrollBox> OptionScroll;
    TMap<FString,TSharedPtr<class SWidget>> OptionCards;
    FString OptionsSignature,OptionsCategory;
    TSharedPtr<class SWidget> PreviewSurface;
    FVector2D PreviewOrbit=FVector2D::ZeroVector;
    TArray<FGunsmithOverviewRow> Overview;
    FString SelectedCategory=TEXT("magazine");
    FString StatusText;
    bool bCompareFactory=false;
    FDelegateHandle GunsmithHandle,ProfileHandle;
    FSlateBrush BackgroundBrush,PreviewBrush,PanelBrush,RowBrush;
    FButtonStyle NormalButton,SelectedButton,PrimaryButton;
    UPROPERTY() TObjectPtr<class UTexture2D> BackgroundTexture;
    UPROPERTY() TObjectPtr<class UTextureRenderTarget2D> PreviewTarget;
    UPROPERTY() TObjectPtr<class UMaterialInstanceDynamic> PreviewMaterial;
    UPROPERTY() TObjectPtr<class USceneCaptureComponent2D> Capture;
    float CaptureAccumulator=0;
    float PreviewMotion=1.f;
    bool bAimPreview=false;
    bool bSidePreview=false;
};
