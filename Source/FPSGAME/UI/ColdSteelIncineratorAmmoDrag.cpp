#include "ColdSteelIncineratorAmmoDrag.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelIncineratorWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Components/TextBlock.h"
#include "Engine/GameInstance.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/SNullWidget.h"
void UColdSteelIncineratorAmmoSource::Configure(UColdSteelHUDWidget* Owner,const FString& Id,TSharedRef<SWidget> Content)
{HUD=Owner;Ammo=Id;Contents=Content;Contents->SetVisibility(EVisibility::HitTestInvisible);SetIsFocusable(true);}
TSharedRef<SWidget> UColdSteelIncineratorAmmoSource::RebuildWidget()
{
    const float Scale=FMath::Max(.01f,ColdSteelUI::PixelScale(this));
    Background=ColdSteelUI::RoundedBrush(ColdSteelUI::Content,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale);
    return SNew(SBorder).BorderImage(&Background).Padding(FMargin(14/Scale,10/Scale))[Contents.IsValid()?Contents.ToSharedRef():SNullWidget::NullWidget];
}
void UColdSteelIncineratorAmmoSource::ReleaseSlateResources(bool Children){Super::ReleaseSlateResources(Children);Contents.Reset();}
FReply UColdSteelIncineratorAmmoSource::NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent& Event)
{
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!HUD||!M||!M->bIncineratorOpen||M->PouchCount(Ammo)<=0)return FReply::Handled();
    if(Event.GetEffectingButton()==EKeys::RightMouseButton)
    {if(auto* Panel=HUD->IncineratorPanel())Panel->RequestAmmo(Ammo,M->PouchCount(Ammo));return FReply::Handled();}
    if(Event.GetEffectingButton()==EKeys::LeftMouseButton)return FReply::Handled().DetectDrag(TakeWidget(),EKeys::LeftMouseButton);
    return FReply::Handled();
}
void UColdSteelIncineratorAmmoSource::NativeOnDragDetected(const FGeometry&,const FPointerEvent&,UDragDropOperation*& Out)
{
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!M||!M->bIncineratorOpen||M->PouchCount(Ammo)<=0)return;
    auto* Drag=NewObject<UColdSteelIncineratorAmmoDrag>(this);Drag->Ammo=Ammo;Drag->Available=M->PouchCount(Ammo);Drag->Generation=M->Snapshot().Generation;
    auto* Text=NewObject<UTextBlock>(Drag);Text->SetText(FText::FromString(M->AmmoLabel(Ammo)));Text->SetFont(ColdSteelUI::TextFont(14/ColdSteelUI::PixelScale(this)));
    Text->SetColorAndOpacity(ColdSteelUI::TextPrimary);Drag->DefaultDragVisual=Text;Drag->Pivot=EDragPivot::MouseDown;Out=Drag;
}
