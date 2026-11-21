// Source/FPSGAME/UI/ColdSteelProgressNotification.h
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 12-12 | class STextBlock;
class STextBlock;

// Lines 27-27 | class FPSGAME_API UColdSteelProgressNotification : public UUserWidget
    UPROPERTY(Transient) TObjectPtr<UTexture2D> InteractionIcon;

// Lines 30-32 | class FPSGAME_API UColdSteelProgressNotification : public UUserWidget
    TSharedPtr<SBox> Root,Card,InteractionRow;
    TSharedPtr<STextBlock> InteractionTitle,InteractionDetail;
    FSlateBrush IconBrush,InteractionBrush;

// Lines 38-41 | class FPSGAME_API UColdSteelProgressNotification : public UUserWidget
    uint64 IconRequest=0,InteractionIconRequest=0;
    FColdSteelProgressNotice Active,Interaction;
    double InteractionVisibleUntil=0.;
    float InteractionRemaining=0.f;

// Lines 44-45 | class FPSGAME_API UColdSteelProgressNotification : public UUserWidget
    void PrepareNoticeIcon(bool bInteraction=false);
    void UpdateInteraction();
