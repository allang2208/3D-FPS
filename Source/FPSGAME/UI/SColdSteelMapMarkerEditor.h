#pragma once

#include "Widgets/SCompoundWidget.h"
#include "Styling/SlateTypes.h"
#include "ColdSteelMapMarkers.h"

class APlayerController;
class SEditableTextBox;
class SHorizontalBox;
class SBox;
struct FColdSteelWorldMapSession;

DECLARE_DELEGATE_OneParam(FColdSteelMapMarkerPicked,const FColdSteelMapMarker&);

class SColdSteelMapMarkerEditor final : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelMapMarkerEditor) {}
        SLATE_EVENT(FColdSteelMapMarkerPicked,OnSelected)
    SLATE_END_ARGS()
    void Construct(const FArguments&,APlayerController*,TSharedRef<FColdSteelWorldMapSession>);
    virtual ~SColdSteelMapMarkerEditor() override;
    void Begin(const FColdSteelMapMarker& Marker);
    void Cancel();
    void SetMapContent(TSharedRef<SWidget> Content);

private:
    TWeakObjectPtr<APlayerController> Player;
    TSharedPtr<FColdSteelWorldMapSession> Session;
    TSharedPtr<SEditableTextBox> Name;
    TSharedPtr<SHorizontalBox> List;
    TSharedPtr<SBox> MapHost;
    FColdSteelMapMarker Draft;
    FColdSteelMapMarkerPicked OnSelected;
    FButtonStyle Button,PrimaryButton;
    FEditableTextBoxStyle Input;
    FSlateBrush InputNormal,InputFocus,FormBrush,SelectedBrush,SwatchBrush;
    uint32 SeenRevision = MAX_uint32;
    bool bOwnsMoveBlock = false;
    FString Error;
    void RebuildList();
    void Save();
    void FinishEditing(bool bRestoreInput);
    TSharedRef<SWidget> Action(const TCHAR* Text,TFunction<void()> Click,bool bPrimary=false);
    virtual void Tick(const FGeometry&,double,float) override;
    virtual FReply OnPreviewKeyDown(const FGeometry&,const FKeyEvent&) override;
};
