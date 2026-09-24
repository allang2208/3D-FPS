#include "ColdSteelInventoryWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "Rendering/SlateRenderer.h"
#include "Rendering/DrawElements.h"
#include "Serialization/JsonSerializer.h"
#include "Styling/CoreStyle.h"

namespace
{
// The outer arc is concentric with the inset item card; the sweep uses the actual mesh positions.
void DrawProcessingCorner(FSlateWindowElementList& Out,int32 Layer,const FGeometry& G,float Scale,
    FVector2f Corner,FVector2f AxisX,FVector2f AxisY,float Size,float Radius,FLinearColor Color,float Time,float Opacity)
{
    constexpr int32 Steps=10,ArcSteps=8;
    Radius=FMath::Clamp(Radius,0.f,Size);
    TArray<FVector2f,TInlineAllocator<32>> Boundary;
    for(int32 I=0;I<=ArcSteps;++I){
        const float Angle=HALF_PI*float(I)/ArcSteps;
        Boundary.Add(I==0?FVector2f(0,Radius):I==ArcSteps?FVector2f(Radius,0):FVector2f(Radius*(1-FMath::Cos(Angle)),Radius*(1-FMath::Sin(Angle))));
    }
    if(Size>Radius)for(int32 I=1;I<Steps;++I)Boundary.Add(FVector2f(Radius+(Size-Radius)*float(I)/Steps,0));
    const int32 Columns=Boundary.Num();
    TArray<FSlateVertex> Verts;TArray<SlateIndex> Indices;
    Verts.Reserve(Columns*(Steps+1)+1+(Columns+2)*2);Indices.Reserve((Columns-1)*Steps*6+Steps*3+(Columns+2)*6);
    const float Sweep=FMath::Fmod(Time,3.2f)*1.5f-.35f;
    auto Vertex=[&](FVector2f Point,float Coverage=1.f){
        const float U=Point.X/Size,V=Point.Y/Size;
        const float Distance=(U+V*.7f-Sweep)/.13f,Flash=FMath::Exp(-Distance*Distance);
        auto Tint=FMath::Lerp(Color*(.68f+.24f*U+.12f*V),FMath::Lerp(Color,FLinearColor::White,.66f),Flash);
        Tint.A=Opacity*.98f*Coverage;
        const FVector2f Position=(Corner+AxisX*Point.X+AxisY*Point.Y)/Scale;
        const SlateIndex Result=SlateIndex(Verts.Num());
        Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),Position,FVector2f(.5f,.5f),Tint.ToFColor(true)));
        return Result;
    };
    auto Index=[](int32 I,int32 J){return SlateIndex(I*(Steps+1)+J);};
    for(int32 I=0;I<Columns;++I)for(int32 J=0;J<=Steps;++J){
        const auto Start=Boundary[I];
        Vertex(FVector2f(Start.X,FMath::Lerp(Start.Y,Size-Start.X,float(J)/Steps)));
        if(I>0&&J>0)Indices.Append({Index(I-1,J-1),Index(I,J-1),Index(I-1,J),Index(I,J-1),Index(I,J),Index(I-1,J)});
    }
    const SlateIndex Tip=Vertex(FVector2f(Size,0));
    for(int32 J=0;J<Steps;++J)Indices.Append({Index(Columns-1,J),Tip,Index(Columns-1,J+1)});

    // The fringe overlaps the inner stroke; the shared card outline is painted above it.
    Boundary.AddUnique(FVector2f(Size,0));Boundary.AddUnique(FVector2f(0,Size));
    const int32 FringeStart=Verts.Num(),Count=Boundary.Num();
    for(int32 I=0;I<Count;++I){
        const auto Point=Boundary[I];
        const auto Incoming=(Point-Boundary[(I+Count-1)%Count]).GetSafeNormal();
        const auto Outgoing=(Boundary[(I+1)%Count]-Point).GetSafeNormal();
        const FVector2f NormalA(Incoming.Y,-Incoming.X),NormalB(Outgoing.Y,-Outgoing.X);
        const auto Offset=(NormalA+NormalB)*(.5f/(1.f+FVector2f::DotProduct(NormalA,NormalB)));
        Vertex(Point);Vertex(Point+Offset,0);
        const SlateIndex A=SlateIndex(FringeStart+I*2),B=SlateIndex(FringeStart+((I+1)%Count)*2);
        Indices.Append({A,SlateIndex(A+1),B,SlateIndex(A+1),SlateIndex(B+1),B});
    }
    const auto Resource=FSlateApplication::Get().GetRenderer()->GetResourceHandle(*FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")));
    FSlateDrawElement::MakeCustomVerts(Out,Layer,Resource,Verts,Indices,nullptr,0,0);
}
}

using namespace ColdSteelInventory;
void UColdSteelInventoryWidget::RefreshPresentation()
{
    Presentation.Empty();bProcessingAnimated=false;if(!Model)return;
    auto* Guns=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    for(const auto& I:Model->Items()){
        TSharedPtr<FJsonObject> Data;if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data)||!Data)continue;
        auto& P=Presentation.Add(I.InstanceId);Data->TryGetStringField(TEXT("name"),P.Name);Data->TryGetStringField(TEXT("rarity"),P.Rarity);
        double Level=0;Data->TryGetNumberField(TEXT("enhanceLevel"),Level);P.Enhancement=FMath::Max(0,int32(Level));
        const TSharedPtr<FJsonObject>* Craft=nullptr;const TSharedPtr<FJsonObject>* Enchant=nullptr;
        P.Crafted=(Guns&&!Guns->Installed(I).IsEmpty())||(Data->TryGetObjectField(TEXT("_craftData"),Craft)&&!(*Craft)->Values.IsEmpty());
        if(Data->TryGetObjectField(TEXT("_enchantData"),Enchant)){const TSharedPtr<FJsonObject>* Affix=nullptr;P.Enchanted=(*Enchant)->TryGetObjectField(TEXT("prefix"),Affix)||(*Enchant)->TryGetObjectField(TEXT("suffix"),Affix);}
        bProcessingAnimated|=(bWarehouse?(Model->InOpenStorage(I)&&I.Cell>=StorageStart()&&I.Cell<StorageStart()+StorageRows()*18):(I.Place==0||I.Place==1))&&(P.Enhancement>0||P.Crafted||P.Enchanted);
    }
}

int32 UColdSteelInventoryWidget::NativePaint(const FPaintArgs& A,const FGeometry& G,const FSlateRect& C,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& S,bool Enabled)const
{
    Layer=Super::NativePaint(A,G,C,Out,Layer,S,Enabled);if(!Model)return Layer;
    const auto L=Layout(G);const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
    const int32 Container=StoragePlace(),Start=StorageStart(),Rows=StorageRows();
    auto Fade=[](FLinearColor Color,float Alpha){Color.A*=Alpha;return Color;};
    float Opacity=1;
    auto Box=[&](float X,float Y,float W,float H,FLinearColor Fill,FLinearColor Edge=FLinearColor::Transparent,float Radius=2,float Stroke=1,int32 Z=1){
        if(W<=0||H<=0)return;Fill.A*=Opacity;Edge.A*=Opacity;if(Edge.A<=0)Stroke=0;auto B=ColdSteelUI::RoundedBrush(Fill,Radius/Scale,Edge,Stroke/Scale);
        FSlateDrawElement::MakeBox(Out,Layer+Z,G.ToPaintGeometry(FVector2D(W,H)/Scale,FSlateLayoutTransform(FVector2D(X,Y)/Scale)),&B,ESlateDrawEffect::None,Fill);
    };
    auto Label=[&](FString Text,float X,float Y,float Size,FLinearColor Color,float MaxWidth,bool Numeric=false){
        if(MaxWidth<=0)return;const auto Font=Numeric?GunsmithUI::NumberFont(Size/Scale):GunsmithUI::TextFont(Size/Scale,Size>=16);
        if(Measure->Measure(Text,Font).X*Scale>MaxWidth){while(!Text.IsEmpty()&&Measure->Measure(Text+TEXT("…"),Font).X*Scale>MaxWidth)Text.LeftChopInline(1);Text+=TEXT("…");}
        Color.A*=Opacity;FSlateDrawElement::MakeText(Out,Layer+4,G.ToPaintGeometry(FVector2D(MaxWidth,Size+4)/Scale,FSlateLayoutTransform(FVector2D(X,Y)/Scale)),Text,Font,ESlateDrawEffect::None,Color);
    };
    const FString HoverId=IdAt(HoverPlace,PointerCell);
    auto Item=[&](const FColdSteelItem& I,float X,float Y,float W,float H,bool Name,bool Hotbar=false,int32 GearSlot=-1){
        Opacity=I.InstanceId==DraggedItem?.3f:1.f;const auto* P=Presentation.Find(I.InstanceId);
        const bool SelectedItem=I.InstanceId==Selected,Hovered=I.InstanceId==HoverId;
        const FVector2f CardMin(X+1,Y+1),CardMax(X+W-1,Y+H-1);
        const float Stroke=SelectedItem?2.f:1.f;
        const float CardRadius=FMath::Min(ColdSteelUI::InventoryItemRadius,FMath::Min(W-2,H-2)*.5f);
        // Fractional gear columns and custom vertices must use the same unsnapped geometry.
        auto DrawCard=[&](FLinearColor Fill,FLinearColor Edge,int32 Z){
            Fill.A*=Opacity;Edge.A*=Opacity;
            auto Brush=ColdSteelUI::RoundedBrush(Fill,CardRadius/Scale,Edge,Stroke/Scale);
            Brush.OutlineSettings.bUseBrushTransparency=false;
            FSlateDrawElement::MakeBox(Out,Layer+Z,G.ToPaintGeometry((CardMax-CardMin)/Scale,FSlateLayoutTransform(CardMin/Scale)),&Brush,ESlateDrawEffect::NoPixelSnapping,Fill);
        };
        DrawCard(Hovered?GunsmithUI::Gray(80,175):GunsmithUI::Gray(55,128),FLinearColor::Transparent,1);
        Box(X+8,Y+2,W-16,1,GunsmithUI::Gray(255,SelectedItem?90:30),FLinearColor::Transparent,0);
        if(SelectedItem)Box(X+2,Y+9,2,H-18,GunsmithUI::Silver,FLinearColor::Transparent,0,0,3);
        if(Name){for(int32 N=1;N<I.Width;++N)Box(X+N*L.Cell,Y+2,1,H-4,GunsmithUI::Gray(220,10),FLinearColor::Transparent,0);for(int32 N=1;N<I.Height;++N)Box(X+2,Y+N*L.Cell,W-4,1,GunsmithUI::Gray(220,10),FLinearColor::Transparent,0);}
        const float Left=4,Right=4;
        const float CornerInset=Stroke-ColdSteelUI::ProcessingCornerUnderlap;
        const float CornerRadius=FMath::Max(0.f,CardRadius-CornerInset);
        const float CornerSize=FMath::Max(CornerRadius,FMath::Min(FMath::Clamp(H*.28f,7.f,18.f),(W-6)/3));
        if(const auto* Brush=ItemBrush(I)){
            const float ImageX=GearSlot>=0?W*.48f:Left,ImageWidth=W-ImageX-Right,ImageHeight=H-(Name?20:8);
            // A turned bag item draws upright and rotates about its centre, so the fit is transposed.
            const bool Turned=GearSlot<0&&I.bRotated;
            FVector2D Size=Brush->ImageSize;
            const float Fit=Turned?FMath::Min(FMath::Max(1.f,ImageHeight)/FMath::Max(1.f,float(Size.X)),FMath::Max(1.f,ImageWidth)/FMath::Max(1.f,float(Size.Y)))
                                  :FMath::Min(FMath::Max(1.f,ImageWidth)/FMath::Max(1.f,float(Size.X)),FMath::Max(1.f,ImageHeight)/FMath::Max(1.f,float(Size.Y)));
            Size*=Fit;
            // Both orientations centre the box on the card's image area; a turn then keeps the
            // transposed art inside the same card instead of hanging out of the cell.
            const FVector2D ImageCenter(X+ImageX+ImageWidth*.5f,Y+H*.5f+(Name?6:0));
            const auto Geometry=G.ToPaintGeometry(Size/Scale,FSlateLayoutTransform((ImageCenter-Size*.5f)/Scale));
            // The rotation point is local pixels, not normalised: an unset value turns about the box centre,
            // which keeps the transposed art centred inside the item card.
            if(Turned)FSlateDrawElement::MakeRotatedBox(Out,Layer+2,Geometry,Brush,ESlateDrawEffect::None,PI*.5f,TOptional<FVector2f>(),FSlateDrawElement::RelativeToElement,FLinearColor(1,1,1,Opacity));
            else FSlateDrawElement::MakeBox(Out,Layer+2,Geometry,Brush,ESlateDrawEffect::None,FLinearColor(1,1,1,Opacity));
        }else if(GearSlot<0)Label(P?P->Name:I.Definition,X+Left,Y+H/2-6,12,GunsmithUI::Text,W-Left-Right);
        if(GearSlot>=0){
            const float TextWidth=W*.48f-18;const bool Active=Model->Equipped()&&Model->Equipped()->InstanceId==I.InstanceId;
            Label(SlotNames()[GearSlot],X+10,Y+6,12,GunsmithUI::Muted,TextWidth);
            Label(P?P->Name:I.Definition,X+10,Y+23,14,GunsmithUI::Text,TextWidth);
            if(H>=66)Label(Active?TEXT("当前使用"):TEXT("已装备"),X+10,Y+H-20,12,Active?GunsmithUI::Silver:GunsmithUI::Secondary,TextWidth);
        }
        if(Name&&W>=80){
            const float TitleSpace=W-Left-Right-(P&&P->Enhancement>0?CornerSize:0);
            const FString Title=P?P->Name:I.Definition;const auto Font=GunsmithUI::TextFont(12/Scale);const float Width=FMath::Min(float(Measure->Measure(Title,Font).X*Scale)+8,TitleSpace);
            Box(X+Left,Y+3,Width,16,GunsmithUI::Gray(20,190),FLinearColor::Transparent,3,0,3);Label(Title,X+Left+3,Y+3,12,GunsmithUI::Text,TitleSpace-6);
        }
        if(I.Count>1){const FString Count=FString::Printf(TEXT("%lld"),I.Count);const float FontSize=12;const float Width=FMath::Min(W-4-(!Hotbar&&P&&P->Crafted?CornerSize+1:0),float(Measure->Measure(Count,GunsmithUI::NumberFont(FontSize/Scale)).X*Scale)+5);
            const float CountX=Hotbar?X+(W-Width)/2:X+W-Width-2-(P&&P->Crafted?CornerSize+1:0),CountY=Hotbar?Y+2:Y+H-FontSize-4;
            Box(CountX,CountY,Width,FontSize+2,GunsmithUI::Gray(10,220),FLinearColor::Transparent,2,0,3);Label(Count,CountX+2,CountY,FontSize,GunsmithUI::Text,Width-2,true);}
        if(I.Cooldown>0){DrawCard(Fade(ColdSteelUI::GlassTint,.65f),FLinearColor::Transparent,3);Label(FString::Printf(TEXT("%.1f"),I.Cooldown),X+4,Y+H/2-6,12,ColdSteelUI::Warning,W-8,true);}
        if(P&&!Hotbar){
            const float Time=GlintSeconds+float(GetTypeHash(I.InstanceId)%1000)/1000.f;
            if(P->Enhancement>0)DrawProcessingCorner(Out,Layer+4,G,Scale,FVector2f(CardMax.X-CornerInset,CardMin.Y+CornerInset),FVector2f(-1,0),FVector2f(0,1),CornerSize,CornerRadius,ColdSteelUI::Enhanced,Time,Opacity);
            if(P->Crafted)DrawProcessingCorner(Out,Layer+4,G,Scale,FVector2f(CardMax.X-CornerInset,CardMax.Y-CornerInset),FVector2f(-1,0),FVector2f(0,-1),CornerSize,CornerRadius,ColdSteelUI::Crafted,Time+.7f,Opacity);
            if(P->Enchanted)DrawProcessingCorner(Out,Layer+4,G,Scale,FVector2f(CardMin.X+CornerInset,CardMax.Y-CornerInset),FVector2f(1,0),FVector2f(0,-1),CornerSize,CornerRadius,ColdSteelUI::Enchanted,Time+1.4f,Opacity);
        }
        DrawCard(FLinearColor::Transparent,SelectedItem?GunsmithUI::Silver:GunsmithUI::Edge,5);
        Opacity=1;
    };
    // One blurred drawer behind translucent groups; sharp content stays above the glass.
    if(!bWarehouse){
    Box(4,4,L.Width-8,L.BagY-36,GunsmithUI::Gray(120,9),GunsmithUI::Gray(220,22),10);
    Box(16,5,L.Width-32,1,GunsmithUI::Gray(255,32),FLinearColor::Transparent,0);
    Box(12,11,2,16,GunsmithUI::Silver);Label(TEXT("随身装备"),23,9,16,GunsmithUI::Text,100);
    int32 Equipped=0;for(const auto& I:Model->Items())if(I.Place==1)++Equipped;
    Label(FString::Printf(TEXT("%d / 15"),Equipped),L.Width-92,12,12,GunsmithUI::Secondary,80,true);
    for(int32 N=0;N<15;++N){const float X=12+(N%3)*(L.GearWidth+6),Y=L.GearY+(N/3)*L.GearPitch;const int32 Index=Owner(Model->Items(),1,N);
        if(Index>=0)Item(Model->Items()[Index],X,Y,L.GearWidth,L.GearHeight,false,false,N);
        else {const bool Lock=Locked(Model->Items(),N),Hover=HoverPlace==1&&PointerCell==N;
            Box(X,Y,L.GearWidth,L.GearHeight,GunsmithUI::Gray(Hover?65:18,Hover?120:90),Hover?GunsmithUI::Gray(230,95):GunsmithUI::Gray(220,28),ColdSteelUI::InventoryItemRadius);
            Label(SlotNames()[N],X+12,Y+(L.GearHeight>=66?15:9),14,GunsmithUI::Secondary,L.GearWidth-40);
            Label(Lock?TEXT("双手占用"):TEXT("未装备"),X+12,Y+(L.GearHeight>=66?38:30),12,GunsmithUI::Muted,L.GearWidth-40);
            Label(Lock?TEXT("—"):TEXT("+"),X+L.GearWidth-28,Y+(L.GearHeight-16)/2,16,GunsmithUI::Gray(Lock?100:145),18);}
    }
    }
    int32 Cells=0,Count=0;for(const auto& I:Model->Items())if(I.Place==Container&&(!bWarehouse||I.Container==Model->ActiveContainer)&&I.Cell>=Start&&I.Cell<Start+Rows*18){Cells+=I.Width*I.Height;++Count;}
    Box(4,L.BagY-36,L.Width-8,Rows*L.Cell+42,GunsmithUI::Gray(120,8),GunsmithUI::Gray(220,22),10);
    Label(bWarehouse?(Model->ActiveContainer.IsEmpty()?TEXT("仓储空间"):*Model->ActiveStorageCaption):TEXT("空间背包"),12,L.BagY-28,16,GunsmithUI::Text,150);
    Label(FString::Printf(TEXT("%d / %d 格 · %d 件"),Cells,Rows*18,Count),L.Width-246,L.BagY-25,12,Cells>=Rows*18?ColdSteelUI::Warning:GunsmithUI::Secondary,180,true);
    Box(L.Width-60,L.BagY-30,48,24,bSortHovered?GunsmithUI::Gray(75,200):GunsmithUI::Gray(43,160),bSortHovered?GunsmithUI::Silver:GunsmithUI::Edge,4);Label(TEXT("整理"),L.Width-50,L.BagY-25,12,GunsmithUI::Text,38);
    Box(12,L.BagY-5,L.Width-24,2,GunsmithUI::Gray(15,180));Box(12,L.BagY-5,(L.Width-24)*FMath::Clamp(Cells/float(Rows*18),0.f,1.f),2,Cells>=Rows*18?ColdSteelUI::Warning:Fade(GunsmithUI::Silver,.6f));
    Box(12,L.BagY,L.Width-24,L.Cell*Rows,GunsmithUI::Gray(15,95),GunsmithUI::Edge,0);
    for(int32 N=1;N<18;++N)Box(12+N*L.Cell,L.BagY,1,Rows*L.Cell,GunsmithUI::Gray(220,22),FLinearColor::Transparent,0);
    for(int32 N=1;N<Rows;++N)Box(12,L.BagY+N*L.Cell,L.Width-24,1,GunsmithUI::Gray(220,22),FLinearColor::Transparent,0);
    for(const auto& I:Model->Items())if(I.Place==Container&&(!bWarehouse||I.Container==Model->ActiveContainer)&&I.Cell>=Start&&I.Cell<Start+Rows*18)Item(I,12+I.Cell%18*L.Cell,L.BagY+(I.Cell-Start)/18*L.Cell,I.Width*L.Cell,I.Height*L.Cell,true);
    if(HoverPlace==Container&&PointerCell>=Start&&HoverId.IsEmpty())Box(12+PointerCell%18*L.Cell,L.BagY+(PointerCell-Start)/18*L.Cell,L.Cell,L.Cell,Fade(ColdSteelUI::Accent,.04f),Fade(ColdSteelUI::Accent,.65f),2,1,5);
    if(!bWarehouse){
    Label(TEXT("数字快捷栏"),12,L.HotY-21,14,GunsmithUI::Text,100);Label(TEXT("技能 / 消耗品"),L.Width-128,L.HotY-19,12,GunsmithUI::Muted,116);
    for(int32 N=0;N<4;++N){const float X=12+N*54;Box(X,L.HotY,48,46,GunsmithUI::Gray(22,120),GunsmithUI::Edge,7);if(const auto* I=Model->ResolveHotbar(N))Item(*I,X,L.HotY,48,46,false,true);
        else {
            const auto B=Model->QuickBinding(N+ColdSteelQuickBar::ItemOffset);
            const FString Key=B.Skill.IsNone()?B.ItemDefinition:TEXT("@skill:")+B.Skill.ToString();
            if(const auto* Brush=IconBrushes.Find(Key))FSlateDrawElement::MakeBox(Out,Layer+2,G.ToPaintGeometry(FVector2D(40,40)/Scale,FSlateLayoutTransform(FVector2D(X+4,L.HotY+3)/Scale)),Brush,ESlateDrawEffect::None,FLinearColor::White);
            if(!B.ItemDefinition.IsEmpty())Label(TEXT("0"),X+4,L.HotY+2,12,ColdSteelUI::Danger,20,true);
        }
        Box(X+31,L.HotY+28,15,16,GunsmithUI::Gray(15,230),FLinearColor::Transparent,3,0,3);Label(FString::FromInt(N+1),X+35,L.HotY+29,12,GunsmithUI::Text,12,true);}
    }
    if(PreviewPlace==Container&&bPreviewValid)for(const auto& R:SwapDestinations)Box(12+R.Min.X*L.Cell,L.BagY+R.Min.Y*L.Cell,R.Width()*L.Cell,R.Height()*L.Cell,Fade(ColdSteelUI::Accent,.1f),ColdSteelUI::Accent,2,1,5);
    if(PreviewPlace>=0&&PreviewCell>=0){const auto* I=Model->FindItem(HoverPreview);float X=12,Y=0,W=48,H=L.GearHeight;
        if(PreviewPlace==Container){
            // A drag supplies the pending footprint; external preview setters keep the instance shape.
            FIntPoint PreviewSpan=PreviewCells;
            if(PreviewSpan.X*PreviewSpan.Y<=1&&I&&I->Width*I->Height>1)PreviewSpan=FIntPoint(I->Width,I->Height);
            X+=PreviewCell%18*L.Cell;Y=L.BagY+(PreviewCell-Start)/18*L.Cell;W=FMath::Min(PreviewSpan.X*L.Cell,L.Width-X-12);H=FMath::Min(PreviewSpan.Y*L.Cell,L.BagY+Rows*L.Cell-Y);}
        else if(PreviewPlace==1){X+=PreviewCell%3*(L.GearWidth+6);Y=L.GearY+PreviewCell/3*L.GearPitch;W=L.GearWidth;}else{X+=PreviewCell*54;Y=L.HotY;H=46;}
        const auto Color=I?(bPreviewValid?ColdSteelUI::Success:ColdSteelUI::Danger):ColdSteelUI::Accent;Box(X,Y,W,H,Fade(Color,.12f),Color,2,2,5);
    }
    FString Message=TEXT("拖动放置 / 交换物品");
    if(bPreviewRotatable)Message+=TEXT(" · F 调整摆放方向");
    FLinearColor Tone=GunsmithUI::Secondary;
    if(PreviewPlace>=0&&!PreviewReason.IsEmpty()){Message=PreviewReason;Tone=bPreviewValid?ColdSteelUI::Success:ColdSteelUI::Danger;}
    else if(!InteractionMessage.IsEmpty()){Message=InteractionMessage;Tone=ColdSteelUI::Accent;}
    else if(const auto* P=Presentation.Find(Selected)){Message=TEXT("已选中 · ")+P->Name;Tone=ColdSteelUI::TextPrimary;}
    Label(Message,12,L.HotY+(bWarehouse?14:54),12,Tone,L.Width-24);
    const auto* Selection=Model->FindItem(Selected);
    const bool Gun=Selection&&GetGameInstance()->GetSubsystem<UGunsmithSystem>()->ModifiableWeapon(Selection->Definition);
    Label(bWarehouse?TEXT("单击查看 · 右键取出 · Shift+单击拆分"):Gun?TEXT("单击查看 · 右键装备 · J 改造"):TEXT("单击查看 · 右键使用 · Shift+单击拆分"),12,L.HotY+(bWarehouse?33:73),12,ColdSteelUI::TextTertiary,L.Width-24);
    return Layer+6;
}
