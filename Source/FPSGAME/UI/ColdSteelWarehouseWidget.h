#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelWarehouseWidget.generated.h"
class UColdSteelStatusModel;
class UColdSteelHUDWidget;
class UColdSteelInventoryWidget;
class UTextBlock;
class UButton;
class UComboBoxString;
class UScrollBox;
UCLASS()
class FPSGAME_API UColdSteelWarehouseWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelHUDWidget* Owner);
    void ResetPage();
    void Refresh();
    void CancelInteraction();
    /** 面板标题跟随当前储物容器："仓库"或某个储物箱的档位名。 */
    void SetTitle(const FString& Caption);
    /** 战利品/宝箱会话打开时调用：隐藏批量操作行、关闭按钮改用 ×，仓库会话保持原样。 */
    void SetLootSession(bool bLoot);
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeTick(const FGeometry&,float) override;
    virtual void NativeDestruct() override;
    virtual FReply NativeOnMouseWheel(const FGeometry&,const FPointerEvent&) override;
private:
    friend class UColdSteelHUDWidget;
    int32 ShownPage=-1;
    UPROPERTY() TObjectPtr<UColdSteelHUDWidget> HUD;
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY() TObjectPtr<UColdSteelInventoryWidget> Board;
    UPROPERTY() TObjectPtr<UTextBlock> Capacity;
    UPROPERTY() TObjectPtr<UTextBlock> Page;
    UPROPERTY() TObjectPtr<UTextBlock> Title;
    UPROPERTY() TObjectPtr<UButton> Previous;
    UPROPERTY() TObjectPtr<UButton> Next;
    UPROPERTY() TObjectPtr<UButton> CloseButton;
    UPROPERTY() TObjectPtr<UComboBoxString> SortMenu;
    UPROPERTY() TObjectPtr<UScrollBox> Scroll;
    UPROPERTY() TObjectPtr<class UBackgroundBlur> Blur;
    UPROPERTY() TObjectPtr<class UBorder> Header;
    UPROPERTY() TObjectPtr<class USizeBox> HeaderSize;
    UPROPERTY() TObjectPtr<class USizeBox> ActionSize;
    UPROPERTY() TObjectPtr<class UVerticalBoxSlot> ActionSlot;
    UPROPERTY() TObjectPtr<class UVerticalBoxSlot> FooterSlot;
    struct FLabel {TWeakObjectPtr<UTextBlock> Widget;float Pixels;bool Numeric,Medium;};
    TArray<FLabel> Labels;
    TArray<TWeakObjectPtr<UButton>> Buttons;
    TArray<TWeakObjectPtr<class UHorizontalBoxSlot>> ActionSlots;
    bool bLootSession=false;
    float Scale=1;
    FDelegateHandle ChangedHandle;
    UTextBlock* Text(const FString& Caption,float Pixels,bool Numeric=false,bool Medium=false);
    UButton* Button(const FString& Caption);
    void UpdateScale();
    UFUNCTION() void Close();
    UFUNCTION() void StoreAll();
    UFUNCTION() void Matching();
    UFUNCTION() void StoreMatching();
    UFUNCTION() void PreviousPage();
    UFUNCTION() void NextPage();
    UFUNCTION() void SortChanged(FString Selection,ESelectInfo::Type Type);
    UFUNCTION() UWidget* SortOption(FString Item);
};
