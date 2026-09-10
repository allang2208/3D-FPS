#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelAmmoReadout.generated.h"

class UTextBlock;
class UBorder;
class AFPSGAMECharacter;
class UColdSteelStatusModel;

/** Passive ammunition display. Reads gameplay state without owning input or changing inventory. */
UCLASS()
class FPSGAME_API UColdSteelAmmoReadout : public UUserWidget
{
    GENERATED_BODY()
public:
    void Refresh(const AFPSGAMECharacter* Character,const UColdSteelStatusModel* Model,bool MenuOpen);
protected:
    virtual void NativeOnInitialized() override;
private:
    void Present(const FString& Name,const FString& Ammo,int32 Magazine,int32 Reserve,int32 Capacity,bool Reloading,bool Equipped);
    void Preview(const AFPSGAMECharacter* Character,const UColdSteelStatusModel* Model);
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Weapon;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Calibre;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Current;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Spare;
    bool bPreview=false;
    int32 LastCapture=-1;
    int32 PreviewFailures=0;
};
