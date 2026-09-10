#include "ColdSteelInventoryWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "Rendering/SlateRenderer.h"
#include "Rendering/DrawElements.h"
#include "Serialization/JsonSerializer.h"

using namespace ColdSteelInventory;
void UColdSteelInventoryWidget::RefreshPresentation()
{
    Presentation.Empty();if(!Model)return;
    auto* Guns=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    for(const auto& I:Model->Items()){
        TSharedPtr<FJsonObject> Data;if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data)||!Data)continue;
        auto& P=Presentation.Add(I.InstanceId);Data->TryGetStringField(TEXT("name"),P.Name);Data->TryGetStringField(TEXT("rarity"),P.Rarity);
        double Level=0;Data->TryGetNumberField(TEXT("enhanceLevel"),Level);P.Enhancement=FMath::Max(0,int32(Level));
        const TSharedPtr<FJsonObject>* Craft=nullptr;const TSharedPtr<FJsonObject>* Enchant=nullptr;
        P.Crafted=(Guns&&!Guns->Installed(I).IsEmpty())||(Data->TryGetObjectField(TEXT("_craftData"),Craft)&&!(*Craft)->Values.IsEmpty());
        if(Data->TryGetObjectField(TEXT("_enchantData"),Enchant)){const TSharedPtr<FJsonObject>* Affix=nullptr;P.Enchanted=(*Enchant)->TryGetObjectField(TEXT("prefix"),Affix)||(*Enchant)->TryGetObjectField(TEXT("suffix"),Affix);}
    }
}

int32 UColdSteelInventoryWidget::NativePaint(const FPaintArgs& A,const FGeometry& G,const FSlateRect& C,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& S,bool Enabled)const
{
    Layer=Super::NativePaint(A,G,C,Out,Layer,S,Enabled);if(!Model)return Layer;
    const auto L=Layout(G);const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
    auto Fade=[](FLinearColor Color,float Alpha){Color.A*=Alpha;return Color;};
    float Opacity=1;
    auto Box=[&](float X,float Y,float W,float H,FLinearColor Fill,FLinearColor Edge=FLinearColor::Transparent,float Radius=2,float Stroke=1,int32 Z=1){
        if(W<=0||H<=0)return;Fill.A*=Opacity;Edge.A*=Opacity;if(Edge.A<=0)Stroke=0;auto B=ColdSteelUI::RoundedBrush(Fill,Radius/Scale,Edge,Stroke/Scale);
        FSlateDrawElement::MakeBox(Out,Layer+Z,G.ToPaintGeometry(FVector2D(W,H)/Scale,FSlateLayoutTransform(FVector2D(X,Y)/Scale)),&B,ESlateDrawEffect::None,Fill);
    };
    auto Label=[&](FString Text,float X,float Y,float Size,FLinearColor Color,float MaxWidth,bool Numeric=false){
        if(MaxWidth<=0)return;const auto Font=Numeric?ColdSteelUI::NumberFont(Size*.75f/Scale):ColdSteelUI::TextFont(Size*.75f/Scale);
        if(Measure->Measure(Text,Font).X*Scale>MaxWidth){while(!Text.IsEmpty()&&Measure->Measure(Text+TEXT("…"),Font).X*Scale>MaxWidth)Text.LeftChopInline(1);Text+=TEXT("…");}
        Color.A*=Opacity;FSlateDrawElement::MakeText(Out,Layer+4,G.ToPaintGeometry(FVector2D(MaxWidth,Size+4)/Scale,FSlateLayoutTransform(FVector2D(X,Y)/Scale)),Text,Font,ESlateDrawEffect::None,Color);
    };
    const FString HoverId=IdAt(HoverPlace,PointerCell);
    auto Item=[&](const FColdSteelItem& I,float X,float Y,float W,float H,bool Name,bool Hotbar=false){
        Opacity=I.InstanceId==DraggedItem?.3f:1.f;const auto* P=Presentation.Find(I.InstanceId);
        const bool SelectedItem=I.InstanceId==Selected,Hovered=I.InstanceId==HoverId;
        Box(X+1,Y+1,W-2,H-2,Hovered?ColdSteelUI::ButtonHover:ColdSteelUI::ButtonNormal,SelectedItem?ColdSteelUI::Accent:Fade(ColdSteelUI::Border,.65f),2,SelectedItem?2:1);
        if(Name){for(int32 N=1;N<I.Width;++N)Box(X+N*L.Cell,Y+2,1,H-4,Fade(ColdSteelUI::Border,.22f),FLinearColor::Transparent,0);for(int32 N=1;N<I.Height;++N)Box(X+2,Y+N*L.Cell,W-4,1,Fade(ColdSteelUI::Border,.22f),FLinearColor::Transparent,0);}
        float Left=4,Right=4;
        // Source contract: side badges belong to wide equipment/items, never obscure a 1x1 icon.
        auto Badge=[&](const FString& Text,float BX,FLinearColor Color,float BW){
            Box(BX,Y+5,BW,H-10,Fade(Color,.16f),Fade(Color,.4f),4);
            const float Top=Y+(H-Text.Len()*11)/2;for(int32 N=0;N<Text.Len();++N)Label(Text.Mid(N,1),BX+(BW-10)/2,Top+N*11,10,Color,BW);
        };
        if(P&&!Hotbar&&W>=80&&H>=36){
            const FString Rarity=ColdSteelUI::RarityLabel(P->Rarity);
            if(!Rarity.IsEmpty()){Badge(Rarity,X+5,ColdSteelUI::RarityColor(P->Rarity),12);Left=21;}
            if(P->Enhancement>0){Badge(TEXT("+")+FString::FromInt(P->Enhancement),X+Left,ColdSteelUI::Enhanced,10);Left+=14;}
            if(P->Crafted){Right+=14;Badge(TEXT("改造"),X+W-Right,ColdSteelUI::Crafted,10);}
            if(P->Enchanted){Right+=14;Badge(TEXT("附魔"),X+W-Right,ColdSteelUI::Enchanted,10);}
        }
        if(const auto* Brush=ItemBrush(I)){
            FVector2D Size=Brush->ImageSize;const float Fit=FMath::Min(FMath::Max(1.f,W-Left-Right)/FMath::Max(1.f,float(Size.X)),FMath::Max(1.f,H-8)/FMath::Max(1.f,float(Size.Y)));Size*=Fit;
            FSlateDrawElement::MakeBox(Out,Layer+2,G.ToPaintGeometry(Size/Scale,FSlateLayoutTransform(FVector2D(X+Left+(W-Left-Right-Size.X)/2,Y+(H-Size.Y)/2+(Name?2:0))/Scale)),Brush,ESlateDrawEffect::None,FLinearColor(1,1,1,Opacity));
        }else Label(P?P->Name:I.Definition,X+Left,Y+H/2-6,12,ColdSteelUI::TextPrimary,W-Left-Right);
        if(Name&&W>=80){
            const FString Title=P?P->Name:I.Definition;const auto Font=ColdSteelUI::TextFont(9/Scale);const float Width=FMath::Min(float(Measure->Measure(Title,Font).X*Scale)+6,W-Left-Right);
            Box(X+Left,Y+2,Width,15,ColdSteelUI::ButtonNormal,FLinearColor::Transparent,2,0,3);Label(Title,X+Left+2,Y+2,12,ColdSteelUI::TextPrimary,W-Left-Right-4);
        }
        if(I.Count>1){const FString Count=FString::Printf(TEXT("%lld"),I.Count);const float FontSize=L.Width<480?10:12;const float Width=FMath::Min(W-4,float(Measure->Measure(Count,ColdSteelUI::NumberFont(FontSize*.75f/Scale)).X*Scale)+5);
            const float CountX=Hotbar?X+(W-Width)/2:X+W-Width-2,CountY=Hotbar?Y+2:Y+H-FontSize-4;
            Box(CountX,CountY,Width,FontSize+2,ColdSteelUI::Content,FLinearColor::Transparent,2,0,3);Label(Count,CountX+2,CountY,FontSize,Hotbar?ColdSteelUI::Success:ColdSteelUI::TextPrimary,Width-2,true);}
        if(I.Cooldown>0){Box(X+2,Y+2,W-4,H-4,Fade(ColdSteelUI::GlassTint,.65f),FLinearColor::Transparent,2,0,3);Label(FString::Printf(TEXT("%.1f"),I.Cooldown),X+4,Y+H/2-6,12,ColdSteelUI::Warning,W-8,true);}
        Opacity=1;
    };
    // Quiet group surfaces, single grid lines, restrained silver hierarchy.
    Box(4,4,L.Width-8,L.BagY-36,ColdSteelUI::StatusCard,FLinearColor::Transparent,12);
    Box(12,11,3,16,ColdSteelUI::Accent);Label(TEXT("随身装备"),23,9,16,ColdSteelUI::TextPrimary,100);
    int32 Equipped=0,Cells=0,Count=0;for(const auto& I:Model->Items()){if(I.Place==1)++Equipped;if(I.Place==0){Cells+=I.Width*I.Height;++Count;}}
    Label(FString::Printf(TEXT("%d 件装备"),Equipped),L.Width-96,12,12,ColdSteelUI::TextSecondary,84,true);
    for(int32 N=0;N<15;++N){const float X=12+(N%3)*(L.GearWidth+6),Y=L.GearY+(N/3)*L.GearPitch;const int32 Index=Owner(Model->Items(),1,N);
        if(Index>=0)Item(Model->Items()[Index],X,Y,L.GearWidth,L.GearHeight,false);
        else {const bool Lock=Locked(Model->Items(),N);Box(X,Y,L.GearWidth,L.GearHeight,ColdSteelUI::Content,Fade(ColdSteelUI::Border,HoverPlace==1&&PointerCell==N?1.f:.45f));
            Label(Lock?TEXT("双手占用"):SlotNames()[N],X+10,Y+(L.GearHeight-16)/2,16,Lock?ColdSteelUI::TextTertiary:ColdSteelUI::TextSecondary,L.GearWidth-20);}
    }
    Label(TEXT("空间背包"),12,L.BagY-28,16,ColdSteelUI::TextPrimary,104);
    Label(FString::Printf(TEXT("%d / 72 格 · %d 件"),Cells,Count),L.Width-220,L.BagY-25,12,Cells>=72?ColdSteelUI::Warning:ColdSteelUI::TextSecondary,154,true);
    Box(L.Width-60,L.BagY-30,48,24,bSortHovered?ColdSteelUI::ButtonHover:ColdSteelUI::ButtonNormal,bSortHovered?ColdSteelUI::Accent:ColdSteelUI::Border,4);Label(TEXT("整理"),L.Width-50,L.BagY-25,12,ColdSteelUI::TextPrimary,38);
    Box(12,L.BagY-5,L.Width-24,2,ColdSteelUI::Content);Box(12,L.BagY-5,(L.Width-24)*FMath::Clamp(Cells/72.f,0.f,1.f),2,Cells>=72?ColdSteelUI::Warning:Fade(ColdSteelUI::Accent,.6f));
    Box(12,L.BagY,L.Width-24,L.Cell*4,ColdSteelUI::Content,Fade(ColdSteelUI::Border,.6f),0);
    for(int32 N=1;N<18;++N)Box(12+N*L.Cell,L.BagY,1,4*L.Cell,Fade(ColdSteelUI::Border,.45f),FLinearColor::Transparent,0);
    for(int32 N=1;N<4;++N)Box(12,L.BagY+N*L.Cell,L.Width-24,1,Fade(ColdSteelUI::Border,.45f),FLinearColor::Transparent,0);
    for(const auto& I:Model->Items())if(I.Place==0)Item(I,12+I.Cell%18*L.Cell,L.BagY+I.Cell/18*L.Cell,I.Width*L.Cell,I.Height*L.Cell,true);
    if(HoverPlace==0&&PointerCell>=0&&HoverId.IsEmpty())Box(12+PointerCell%18*L.Cell,L.BagY+PointerCell/18*L.Cell,L.Cell,L.Cell,Fade(ColdSteelUI::Accent,.04f),Fade(ColdSteelUI::Accent,.65f),2,1,5);
    Label(TEXT("快捷物品"),12,L.HotY-21,14,ColdSteelUI::TextSecondary,100);Label(TEXT("拖入消耗品绑定"),L.Width-128,L.HotY-19,12,ColdSteelUI::TextTertiary,116);
    for(int32 N=0;N<4;++N){const float X=12+N*54;Box(X,L.HotY,48,46,ColdSteelUI::Content,Fade(ColdSteelUI::Border,.7f),7);if(const auto* I=Model->ResolveHotbar(N))Item(*I,X,L.HotY,48,46,false,true);
        Box(X+31,L.HotY+28,15,16,ColdSteelUI::ButtonNormal,FLinearColor::Transparent,3,0,3);Label(FString::FromInt(N+1),X+35,L.HotY+29,12,ColdSteelUI::TextPrimary,12,true);}
    if(PreviewPlace==0&&bPreviewValid)for(const auto& R:SwapDestinations)Box(12+R.Min.X*L.Cell,L.BagY+R.Min.Y*L.Cell,R.Width()*L.Cell,R.Height()*L.Cell,Fade(ColdSteelUI::Accent,.1f),ColdSteelUI::Accent,2,1,5);
    if(PreviewPlace>=0&&PreviewCell>=0){const auto* I=Model->FindItem(HoverPreview);float X=12,Y=0,W=48,H=L.GearHeight;
        if(PreviewPlace==0){X+=PreviewCell%18*L.Cell;Y=L.BagY+PreviewCell/18*L.Cell;W=FMath::Min((I?I->Width:1)*L.Cell,L.Width-X-12);H=FMath::Min((I?I->Height:1)*L.Cell,L.BagY+4*L.Cell-Y);}
        else if(PreviewPlace==1){X+=PreviewCell%3*(L.GearWidth+6);Y=L.GearY+PreviewCell/3*L.GearPitch;W=L.GearWidth;}else{X+=PreviewCell*54;Y=L.HotY;H=46;}
        const auto Color=I?(bPreviewValid?ColdSteelUI::Success:ColdSteelUI::Danger):ColdSteelUI::Accent;Box(X,Y,W,H,Fade(Color,.12f),Color,2,2,5);
    }
    FString Message=TEXT("拖动放置 / 交换物品");FLinearColor Tone=ColdSteelUI::TextSecondary;
    if(PreviewPlace>=0&&!PreviewReason.IsEmpty()){Message=PreviewReason;Tone=bPreviewValid?ColdSteelUI::Success:ColdSteelUI::Danger;}
    else if(!InteractionMessage.IsEmpty()){Message=InteractionMessage;Tone=ColdSteelUI::Accent;}
    else if(const auto* P=Presentation.Find(Selected)){Message=TEXT("已选中 · ")+P->Name;Tone=ColdSteelUI::TextPrimary;}
    Label(Message,12,L.HotY+54,12,Tone,L.Width-24);
    const auto* Selection=Model->FindItem(Selected);
    const bool Gun=Selection&&(Selection->Definition==TEXT("ue_m4a1")||Selection->Definition==TEXT("ue_akm"));
    Label(Gun?TEXT("单击查看 · 右键装备 · J 改造"):TEXT("单击查看 · 右键使用 · Shift+单击拆分"),12,L.HotY+73,12,ColdSteelUI::TextTertiary,L.Width-24);
    return Layer+6;
}
