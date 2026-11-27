#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelAmmoReadout.generated.h"

class UTextBlock;
class UBorder;
class UVerticalBox;
class AFPSGAMECharacter;
class UColdSteelStatusModel;
class UTexture2D;
struct FStreamableHandle;
struct FColdSteelItem;

/** Passive weapon resource display: ammunition, stamina, staff mana and spellbook focus. */
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
    virtual void NativeDestruct() override;
private:
    void BuildWeaponSection(UVerticalBox* Parent,bool bOffhand);
    void BuildStaffDetails(UVerticalBox* Parent);
    void BuildStaffMagicReadout(UVerticalBox* Parent);
    void UpdateStaffMagicLayout(float Scale);
    void UpdateStaffMagicIcon(FName Skill,const FString& RelativeIcon);
    void SetStaffVisible(bool Visible);
    void SetDualVisible(bool Visible);
    void PresentDual(const class UPistolDualWieldComponent& Dual,const UColdSteelStatusModel& Model,bool InfiniteReserve);
    void PresentStaffPistol(const FColdSteelItem& Staff,const class UPistolDualWieldComponent& Dual,const UColdSteelStatusModel& Model);
    void PresentOffhandPistol(const class UPistolDualWieldComponent& Dual,const UColdSteelStatusModel& Model);
    void PresentStaff(const FColdSteelItem& Staff,const UColdSteelStatusModel& Model,const AFPSGAMECharacter* Character,bool bHasOffhand);
    void PresentSpellbook(const FColdSteelItem& Book,const UColdSteelStatusModel& Model,const AFPSGAMECharacter* Character);
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
    UPROPERTY(Transient) TObjectPtr<class UHorizontalBox> StaffDetails;
    UPROPERTY(Transient) TObjectPtr<class UHorizontalBox> StaffMagicRow;
    UPROPERTY(Transient) TObjectPtr<class UImage> StaffMagicIcon;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StaffMagicName;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StaffMagicStatus;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StaffMagicCooldownLabel;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StaffMagicCooldown;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UTexture2D>> StaffMagicIcons;
    FName StaffMagicIconSkill;
    TSharedPtr<FStreamableHandle> StaffMagicIconLoad;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> CooldownLabel;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> CooldownValue;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> RecoveryLabel;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> RecoveryValue;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FocusEffects;
    float LayoutWidth=0.f;
    float LayoutScale=0.f;
    bool bPreview=false;
    bool bReserveStatusText=false;
    bool bRecoveryStatusText=false;
    int32 LastCapture=-1;
    int32 PreviewFailures=0;
    TWeakObjectPtr<const AFPSGAMECharacter> CachedPawn;
    int32 CachedPawnComponents=INDEX_NONE;
    TWeakObjectPtr<const class UBowWeaponComponent> CachedBow;
    TWeakObjectPtr<const class UWoodenTorchComponent> CachedTorch;
    TMap<const UTextBlock*,FLinearColor> CachedTextColors;
    FVector2D LastSlotPosition=FVector2D(MAX_flt,MAX_flt);
    bool bSlotAutoSizeSet=false;
    TOptional<bool> LastDualVisible;
    TOptional<bool> LastStaffVisible;

    void SetTextIfChanged(UTextBlock* Block,const FString& Value);
    void SetColorIfChanged(UTextBlock* Block,const FLinearColor& Color);
};
