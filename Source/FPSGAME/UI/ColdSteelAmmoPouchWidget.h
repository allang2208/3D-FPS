#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateTypes.h"
#include "ColdSteelAmmoPouchWidget.generated.h"

// 视图模型定义在 .cpp：采集显示数据、生成内容键、再构建控件树。
struct FColdSteelAmmoPouchView;

UCLASS()
class FPSGAME_API UColdSteelAmmoPouchWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetHUD(class UColdSteelHUDWidget* Owner);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool ReleaseChildren) override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry&,float) override;
private:
    UPROPERTY(Transient) TObjectPtr<class UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelHUDWidget> HUD;
    TSharedPtr<class SVerticalBox> Surface;
    TSharedPtr<class SScrollBox> List;
    FDelegateHandle ChangedHandle;
    TSet<FString> Expanded;
    FString Selected,WeaponInstance,LastWeapon;
    float LastScale=0;
    // 上次构建所依据的内容键（哈希）。用 POD 而不是 FString：热补丁复用旧实例时新成员是
    // 未初始化内存，读一个野 FString 会崩，读一个野整数最多多重建一次。
    uint32 ContentKey=0;
    FButtonStyle Buttons;
    TMap<FString,TSharedPtr<FButtonStyle>> AmmoButtons;
    void CollectPouchView(FString& Key,FColdSteelAmmoPouchView& View) const;
    void BuildPage(const FColdSteelAmmoPouchView& View,float U);
    void Refresh();
};
