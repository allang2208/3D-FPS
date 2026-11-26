#pragma once

#include "Widgets/SCompoundWidget.h"
#include "Styling/SlateBrush.h"
#include "UObject/StrongObjectPtr.h"

class SHorseMarketPlate;
class STextBlock;
class SButton;
class SBox;
class SScrollBox;
class UChapelDialogueComponent;
class UTexture2D;

class SSiegeWorkshopMarket final : public SCompoundWidget
{
public:
SLATE_BEGIN_ARGS(SSiegeWorkshopMarket) : _Conversation(nullptr) {}
        SLATE_ARGUMENT(UChapelDialogueComponent*, Conversation)
        SLATE_EVENT(FSimpleDelegate, OnBack)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args);
    void Refresh();
    void RequestClose();
    TSharedPtr<SWidget> FocusTarget() const;
private:
    friend struct FSiegeDrawerReview;
    struct FOffer
    {
        int32 Rank=0;
        TSharedPtr<STextBlock> Title,Tier,Current,Next,Arrow,Cost,Full;
        TSharedPtr<SButton> Buy;
    };
    TWeakObjectPtr<UChapelDialogueComponent> Conversation;
    TStrongObjectPtr<UTexture2D> Portraits[2];
    FSlateBrush Images[2];
    TSharedPtr<SHorseMarketPlate> Plates[2];
    TSharedPtr<SBox> Captions[2];
    TSharedPtr<SButton> Tabs[2];
    TSharedPtr<STextBlock> Balance,Feedback;
    FSimpleDelegate OnBack;
    TSharedPtr<SBox> Drawer;
    TSharedPtr<SScrollBox> OffersScroll;
    FOffer Offers[4];
    float DrawerWidth=460.f;
    float PhotoHeight=100.f;
    bool bCompactHeader=false;
    float OpenFraction=0.f;
    bool bClosing=false;
    bool bReturnQueued=false;
    int32 Selected=0;
    float Reveal[2]={0,0};
    TSharedRef<SWidget> MakeTab(int32 Index);
    void SetTabReveal(int32 Index,float Fraction);
    TSharedRef<SWidget> MakeOffer(int32 Stat);
    virtual void Tick(const FGeometry& Geometry,double Time,float Delta) override;
};
