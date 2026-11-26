#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "ColdSteelProgressNotification.generated.h"
class UColdSteelStatusModel;
class UAudioComponent;
class USoundWaveProcedural;
class UTexture2D;
class SBox;
class SBorder;
class STextBlock;

/** Displays the latest interaction result alongside queued character and skill upgrades. */
UCLASS()
class FPSGAME_API UColdSteelProgressNotification : public UUserWidget
{
    GENERATED_BODY()
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
    virtual void NativeTick(const FGeometry& Geometry,float Delta) override;
    virtual void NativeDestruct() override;
private:
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> IconTexture;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> InteractionIcon;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> Audio;
    UPROPERTY(Transient) TObjectPtr<USoundWaveProcedural> Sound;
    TSharedPtr<SBox> Root,Card,InteractionRow;
    TSharedPtr<STextBlock> InteractionTitle,InteractionDetail;
    FSlateBrush IconBrush,InteractionBrush;
    TArray<uint8> PCM;
    int32 SampleRate=44100,Channels=2;
    float AudioDuration=0,Elapsed=0,Scale=1;
    bool bActive=false;
    bool bNoticeLoading=false,bNoticeReady=false;
    uint64 IconRequest=0,InteractionIconRequest=0;
    FColdSteelProgressNotice Active,Interaction;
    double InteractionVisibleUntil=0.;
    float InteractionRemaining=0.f;
    void LoadAssets();
    void PlayCue();
    void PrepareNoticeIcon(bool bInteraction=false);
    void UpdateInteraction();
    TSharedRef<SWidget> BuildSurface();
};
