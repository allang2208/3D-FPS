#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelAmmoReadout.generated.h"

class UTextBlock;
class UBorder;
class UVerticalBox;
class AFPSGAMECharacter;
class UColdSteelStatusModel;
struct FColdSteelItem;

/** Passive weapon resource display: firearm ammunition or melee stamina estimates. */
UCLASS()
class FPSGAME_API UColdSteelAmmoReadout : public UUserWidget
{
    GENERATED_BODY()
public:
    static constexpr float PreferredWidth = 360.f;
    void Refresh(const AFPSGAMECharacter* Character,const UColdSteelStatusModel* Model,bool MenuOpen);
    void UpdateLayout(float WidthPixels,float BottomPixels);
protected:
    virtual void NativeOnInitialized() override;
private:
    void BuildWeaponSection(UVerticalBox* Parent,bool bOffhand);
    void SetDualVisible(bool Visible);
    void PresentDual(const class UPistolDualWieldComponent& Dual,const UColdSteelStatusModel& Model,bool InfiniteReserve);
    void Present(const FString& Name,const FString& Ammo,int32 Magazine,int32 Reserve,int32 Capacity,bool Reloading,bool Equipped);
    void PresentMelee(const FColdSteelItem& Item,const UColdSteelStatusModel& Model,const AFPSGAMECharacter* Character);
    void SetReserveStatusText(bool Enabled);
    void Preview(const AFPSGAMECharacter* Character,const UColdSteelStatusModel* Model);
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Weapon;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Calibre;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Current;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Spare;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> MagazineLabel;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> ReserveLabel;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> OffhandName;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> OffhandAmmo;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> OffhandCalibre;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> OffhandSpare;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> OffhandMagazineLabel;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> OffhandReserveLabel;
    UPROPERTY(Transient) TObjectPtr<UVerticalBox> OffhandSection;
    UPROPERTY(Transient) TObjectPtr<class USizeBox> HandSeparator;
    UPROPERTY(Transient) TObjectPtr<class USizeBox> OffhandSeparator;
    UPROPERTY(Transient) TObjectPtr<class UHorizontalBox> OffhandNumbers;
    UPROPERTY(Transient) TObjectPtr<class USizeBox> LayoutBox;
    UPROPERTY(Transient) TObjectPtr<UBorder> Surface;
    UPROPERTY(Transient) TObjectPtr<class USizeBox> Separator;
    UPROPERTY(Transient) TObjectPtr<class UHorizontalBox> Numbers;
    float LayoutWidth=0.f;
    float LayoutScale=0.f;
    bool bPreview=false;
    bool bReserveStatusText=false;
    int32 LastCapture=-1;
    int32 PreviewFailures=0;
};
