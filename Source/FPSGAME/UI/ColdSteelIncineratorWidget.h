#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelIncineratorWidget.generated.h"
class UColdSteelHUDWidget;
class UColdSteelStatusModel;
class UColdSteelInventoryWidget;
class SColdSteelIncineratorPanel;
UCLASS()
class FPSGAME_API UColdSteelIncineratorWidget : public UUserWidget
{
    GENERATED_BODY()
    friend void RunIncineratorUIAudit(class AFPSGAMEPlayerController*);
public:
    void Configure(UColdSteelHUDWidget* Owner);
    void OpenStation(AActor* Station);
    void CloseStation();
    void SetInputReady(bool Ready);
    bool StationReady() const;
    bool CancelConfirmation();
    void RequestClose();
    void RequestAmmo(const FString& Ammo,int64 Available,int32 Cell=-1);
    UColdSteelStatusModel* GetModel() const {return Model;}
    UColdSteelInventoryWidget* InputBoard() const {return Board;}
    const FString& ContainerKey() const {return Container;}
    bool IsInputReady() const {return bInputReady;}
    bool AuditReview();
    bool AuditConfirm();
    bool AuditRetrieve();
    bool AuditDepositAmmo(const FString& Id,int64 Count);
    bool AuditGeometry(FString& Reason) const;
    FString AuditPreview() const;
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry&,float) override;
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool) override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry&,const FKeyEvent&) override;
private:
    void OnInventoryChanged();
    TSharedPtr<SColdSteelIncineratorPanel> Panel;
    FDelegateHandle ChangedHandle;
    TWeakObjectPtr<AActor> Station;
    FString Container;
    bool bStationOpen=false,bInputReady=false;
    float LastScale=0;
    UPROPERTY(Transient) TObjectPtr<UColdSteelHUDWidget> HUD;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TObjectPtr<UColdSteelInventoryWidget> Board;
};
