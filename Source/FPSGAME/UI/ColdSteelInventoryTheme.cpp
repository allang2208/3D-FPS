#include "ColdSteelHUDWidget.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelDetailRow.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/TextBlock.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/SizeBox.h"
#include "Components/VerticalBoxSlot.h"

UTextBlock* UColdSteelHUDWidget::MakeInventoryText(const FString& Text,float Pixels,const FLinearColor& Color,bool Numeric,bool Medium)
{
    auto* Label=WidgetTree->ConstructWidget<UTextBlock>();Label->SetText(FText::FromString(Text));Label->SetColorAndOpacity(Color);
    const float Size=Pixels/ColdSteelUI::PixelScale(this);
    Label->SetFont(Numeric?GunsmithUI::NumberFont(Size,Medium):GunsmithUI::TextFont(Size,Medium));
    InventoryLabels.Add({Label,Pixels,Numeric,Medium});return Label;
}

void UColdSteelHUDWidget::UpdateInventoryLayout(const FGeometry& Geometry)
{
    if(!InventoryPanelSlot)return;
    const float Scale=ColdSteelUI::PixelScale(this);const FVector2D Pixels=Geometry.GetLocalSize()*Scale;
    if(Pixels.X<100||Pixels.Y<100)return;
    float Width=FMath::Min(float(Pixels.X)-24.f,FMath::Clamp(float(Pixels.X)*.48f,720.f,1040.f));
    // Both drawers share their actual size; keep that layout until the left drawer finishes closing.
    if(bWarehouseOpen||WarehouseMotion>.001f)Width=FMath::Min(Width,(float(Pixels.X)-36.f)*.5f);
    if(!Pixels.Equals(InventoryLayoutSize,.5f)||!FMath::IsNearlyEqual(Scale,InventoryLayoutScale,.001f)||!FMath::IsNearlyEqual(Width,InventoryWidth,.5f))
    {
        InventoryPanelSlot->SetOffsets(FMargin(-12/Scale,12/Scale,Width/Scale,12/Scale));
        InventoryHeaderSurface->SetPadding(FMargin(18/Scale,12/Scale));InventoryHeaderSize->SetHeightOverride(36/Scale);
        for(auto& WeakSize:InventoryTabSizes)if(auto* Size=WeakSize.Get())Size->SetHeightOverride(40/Scale);
        InventoryFooterSlot->SetPadding(FMargin(18/Scale,8/Scale,18/Scale,10/Scale));
        Cast<UButtonSlot>(CloseButton->GetContent()->Slot)->SetPadding(FMargin(12/Scale,8/Scale));
        if(WarehouseSlot){WarehouseSlot->SetAnchors(FAnchors(0,0,0,1));WarehouseSlot->SetAlignment(FVector2D::ZeroVector);WarehouseSlot->SetOffsets(FMargin(12/Scale,12/Scale,Width/Scale,12/Scale));}
        for(const auto& Entry:InventoryLabels)if(auto* Label=Entry.Widget.Get())
            Label->SetFont(Entry.Numeric?GunsmithUI::NumberFont(Entry.Pixels/Scale,Entry.Medium):GunsmithUI::TextFont(Entry.Pixels/Scale,Entry.Medium));
        for(const auto& Pair:CharacterRows)if(Pair.Value)Pair.Value->UpdateScale(Scale);
        InventoryLayoutSize=Pixels;InventoryLayoutScale=Scale;InventoryWidth=Width;
        UE_LOG(LogTemp,Display,TEXT("INVENTORY_GLASS viewport=%.0fx%.0f drawer=%.0f scale=%.3f warehouse=%d"),Pixels.X,Pixels.Y,Width,Scale,bWarehouseOpen);
    }
}
