#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateBrush.h"
#include "WoodworkingEntryFlow.h"
#include "ColdSteelWoodworkingWidget.generated.h"

class UWoodworkingSystem;
class UColdSteelWoodworkingManagementWidget;
class AWoodworkingWorldView;
class UWoodworkingSawVisualComponent;
class SWoodworkingPanel;
class SWoodworkingCanvas;
class UTexture2D;
class USoundBase;
class UAudioComponent;
class USoundWaveProcedural;
struct FStreamableHandle;

UCLASS(Config=Game)
class FPSGAME_API UColdSteelWoodworkingWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    bool Configure(AActor* Station,bool PracticeOnly);
    bool IsWorldMode() const {return EntryFlow.InWorkshop()&&!bCanvasFallback;}
    bool IsProjectMenu() const {return EntryFlow.Selecting()||EntryFlow.Preparing();}
    bool IsPreparingProject() const {return EntryFlow.Preparing();}
    bool CanConfirmProject() const;
    void SelectProject(FName Id);
    void ConfirmProject();
    void RequestReturnToSelection();
    void ReturnToSelection();
    void EndSession();
    bool PresentationReady() const;
    bool CursorToWorldWork(FVector2D Screen,FVector2D& Work) const;
    void ZoomWorld(float Steps);
    void ResetWorldCamera();
    void BoardChanged();
    FString PresentationStatus() const;
    void RequestClose();
    void CloseConfirmed();
    void CancelInput();
    bool EnsureStation();
    UWoodworkingSystem* System() const {return Woodworking;}
    const FSlateBrush& BoardBrush() const {return WoodBrush;}
    const FSlateBrush& TargetBrush() const {return OutlineBrush;}
    const FSlateBrush& DamageBrush() const {return DamageOverlayBrush;}
    const TArray<TArray<FVector2D>>& Contours() const {return CachedContours;}
    void PlayCutSound();
    bool RestartProject();
    void SetWorkshopInsets(FMargin Insets);
    void SetReviewOverlay(bool Enabled);
    void NotifyCutContact();
    void ShowManagementInventory(bool Open);
    TSharedRef<SWidget> ManagementContent();
    bool ManagementInputReady() const;
    bool BeginAnimatedClose();
    FVector2D ManagementSlide(float Width,float Scale,bool Outer) const;
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry&,float) override;
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool) override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry&,const FKeyEvent&) override;
private:
    void ApplicationActive(bool Active);
    void ReleaseWorldView();
    void UpdateImages(bool Force=false);
    void UpdateMotorAudio();
    void StopMotorAudio();
    void UseCanvasFallback();
    float DrawerProgress() const;
    TSharedPtr<SWoodworkingPanel> Panel;
    TWeakObjectPtr<AActor> Workbench;
    FDelegateHandle ActivationHandle;
    FSlateBrush WoodBrush,OutlineBrush;
    TArray<FColor> WoodColors;
    FName ImagePattern;
    int32 LastRevision=-1;
    double NextUpload=0,NextStationCheck=0;
    float LastScale=0,LastWidth=0,LastHeight=0;
    UPROPERTY(Transient) TObjectPtr<UWoodworkingSystem> Woodworking;
    UPROPERTY(Transient) TObjectPtr<UColdSteelWoodworkingManagementWidget> ManagementWidget;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> WoodTexture;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> OutlineTexture;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> DamageTexture;
    /** Optional licensed wood-cutting one-shot. Loaded asynchronously; empty means silent. */
    UPROPERTY(Config,EditDefaultsOnly,Category="Woodworking|Presentation") TSoftObjectPtr<USoundBase> CuttingSound;
    FSlateBrush DamageOverlayBrush;
    TArray<TArray<FVector2D>> CachedContours;
    TSharedPtr<FStreamableHandle> SoundLoad;
    double NextCutSound=0;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> CutAudio;
    UPROPERTY(Transient) TObjectPtr<USoundWaveProcedural> MotorWave;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> MotorAudio;
    double LastContactTime=-1,AudioPhase=0;
    uint32 AudioNoise=0x54AC1389;
    TWeakObjectPtr<UWoodworkingSawVisualComponent> SawVisual;
    UPROPERTY(Transient) TObjectPtr<AWoodworkingWorldView> WorldView;
    WoodworkingEntry::FFlow EntryFlow;
    FString EntryNotice;
    bool bStartRequested=false;
    bool bCanvasFallback=false,bDrawerClosing=false,bCloseRequested=false,bCloseAnimationDone=false;
    float ManagementMotion=0;
    TWeakObjectPtr<APawn> EntryPawn;
};
