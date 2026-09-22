#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelAmmoTypes.h"
#include "ColdSteelAmmoWheel.generated.h"

/**
 * One wheel disc. A rifle or single pistol opens exactly one disc; akimbo opens
 * one per hand, and both are the same disc the rifle already draws.
 * Hover is per disc so switching discs never commits the other hand's pick.
 */
struct FColdSteelAmmoWheelDisc
{
    TArray<FColdSteelAmmoChoice> Choices;
    FString Instance, Caption, LoadedId;
    int32 Hand=0;          // 0 main, 1 off
    int32 Hover=INDEX_NONE;
};

UCLASS()
class FPSGAME_API UColdSteelAmmoWheel : public UUserWidget
{
    GENERATED_BODY()
public:
    // 单盘：步枪与单持手枪。Hand<0 表示不显示手别后缀。
    void OpenForWeapon(const FString& Id,int32 Hand=-1);
    // 双持手枪：左右两个圆盘同时弹出（左＝副手，右＝主手），共用一根自由指针。
    // 原点在两盘正中的中点，等于单盘的中心取消区；指针在哪个盘里就改哪只手。
    void OpenForDualPistols(const FString& MainId,const FString& OffId);
    // Delta 是屏幕像素的鼠标位移；按 fps.AmmoWheel.PixelsPerRadius 折算成半径比例。
    void MovePointer(FVector2D Delta);
    // 只提交指针所在圆盘上的选择；两盘之间、盘心取消区、当前弹种与零数量都不提交。
    FString SelectedAmmo() const;
    // 指针所在圆盘的武器实例；指针不在任何盘里时取第一个盘，便于调用方报错。
    const FString& WeaponId() const;
    bool HasDiscs() const { return !Discs.IsEmpty(); }
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual int32 NativePaint(const FPaintArgs&,const FGeometry&,const FSlateRect&,FSlateWindowElementList&,int32,const FWidgetStyle&,bool) const override;
private:
    // 半径比例坐标以组中心为原点：单盘时组中心就是盘心，双盘时是两盘中点。
    struct FLayout
    {
        FVector2D Size=FVector2D::ZeroVector,Center=FVector2D::ZeroVector;
        TArray<FVector2D> Offsets;
        float Scale=1.f,R=0.f,Inner=0.f,Gap=0.f;
    };
    UPROPERTY(Transient) TObjectPtr<class UColdSteelStatusModel> Model;
    FDelegateHandle ChangedHandle;
    TArray<FColdSteelAmmoWheelDisc> Discs;
    FVector2D Pointer=FVector2D::ZeroVector;
    int32 ActiveDisc=INDEX_NONE;
    bool bDualDiscs=false;
    FLayout ComputeLayout(const FVector2D& Size) const;
    int32 AddDisc(const FString& Id,int32 Hand);
    void UpdateHover(const FLayout& Layout);
    void RefreshCounts();
    // 轮盘专用的中心裁切图标画刷：复制模型那张共享画刷、只改 UV，不动弹药袋／背包用的原件。
    const FSlateBrush* FramedIcon(const FString& Id) const;
    mutable TMap<FString,TSharedPtr<FSlateBrush>> FramedIcons;
};