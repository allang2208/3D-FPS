#include "ColdSteelInventoryWidget.h"
#include "ColdSteelEquipmentLayout.h"
#include "ColdSteelStaffIcon.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "../Production/ProductionToolEnhance.h"
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
        // 口径与 ColdSteelInventory::IsMeleeWeapon 一致（符文剑、斧／镐、weapon_melee 类别），
        // 但 category 直接从这份已解析的 Data 取，不在每帧绘制里重读 Item.Data。
        FString Category;Data->TryGetStringField(TEXT("category"),Category);
        P.MeleeArt=I.Definition==TEXT("ue_rune_sword")||IsEquippedProductionTool(I)||Category==TEXT("weapon_melee");
        FString WeaponType;Data->TryGetStringField(TEXT("weaponType"),WeaponType);P.StaffArt=WeaponType==TEXT("staff");
        double Level=0;Data->TryGetNumberField(TEXT("enhanceLevel"),Level);P.Enhancement=FMath::Max(0,int32(Level));
        // 工具强化是独立字段与独立语义：只对斧／镐读取，其他物品保持 0，
        // 避免把武器强度等级写进工具档位（也避免工具档位点亮武器「已强化」光晕）。
        if(IsEquippedProductionTool(I))P.ToolEnhanceLevel=ColdSteelToolEnhance::Level(I);
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
            // 装备栏卡片左边 48% 是槽名与物品名，图区只剩右边那条横长条；近战与工具的
            // 竖直立绘按等比 fit 会被压成一条窄影。这里让它们横放，与枪械图同一口径
            // （刃尖／枪口都朝左），复用下面已有的转置 fit 与旋转贴法。
            const bool Lay=GearSlot>=0&&P&&P->MeleeArt&&Brush->ImageSize.Y>Brush->ImageSize.X;
            FVector2D Size=Brush->ImageSize;
            const float Fit=Turned||Lay?FMath::Min(FMath::Max(1.f,ImageHeight)/FMath::Max(1.f,float(Size.X)),FMath::Max(1.f,ImageWidth)/FMath::Max(1.f,float(Size.Y)))
                                  :FMath::Min(FMath::Max(1.f,ImageWidth)/FMath::Max(1.f,float(Size.X)),FMath::Max(1.f,ImageHeight)/FMath::Max(1.f,float(Size.Y)));
            Size*=Fit;
            if(Name&&P&&P->StaffArt)Size=ColdSteelStaffIcon::InventorySize(Brush->ImageSize,FVector2D(W,H),Turned);
            // Both orientations centre the box on the card's image area; a turn then keeps the
            // transposed art inside the same card instead of hanging out of the cell.
            const FVector2D ImageCenter(X+ImageX+ImageWidth*.5f,Y+H*.5f+(Name?6:0));
            const auto Geometry=G.ToPaintGeometry(Size/Scale,FSlateLayoutTransform((ImageCenter-Size*.5f)/Scale));
            // The rotation point is local pixels, not normalised: an unset value turns about the box centre,
            // which keeps the transposed art centred inside the item card.
            // 屏幕坐标 Y 向下，正角是顺时针：背包转放项用 +90° 还原，装备栏横放用 −90°
            // 把朝上的刃尖转到朝左。
            if(Turned||Lay)FSlateDrawElement::MakeRotatedBox(Out,Layer+2,Geometry,Brush,ESlateDrawEffect::None,Turned?PI*.5f:-PI*.5f,TOptional<FVector2f>(),FSlateDrawElement::RelativeToElement,FLinearColor(1,1,1,Opacity));
            else FSlateDrawElement::MakeBox(Out,Layer+2,Geometry,Brush,ESlateDrawEffect::None,FLinearColor(1,1,1,Opacity));
        }else if(GearSlot<0)Label(P?P->Name:I.Definition,X+Left,Y+H/2-6,12,GunsmithUI::Text,W-Left-Right);
        if(GearSlot>=0){
            const float TextWidth=W*.48f-18;const bool Active=Model->Equipped()&&Model->Equipped()->InstanceId==I.InstanceId;
            Label(SlotNames()[GearSlot],X+10,Y+6,12,GunsmithUI::Muted,TextWidth);
            Label(P?P->Name:I.Definition,X+10,Y+23,14,GunsmithUI::Text,TextWidth);
            if(H>=66)Label(Active?TEXT("当前使用"):TEXT("已装备"),X+10,Y+H-20,12,Active?GunsmithUI::Silver:GunsmithUI::Secondary,TextWidth);
        }
        // Names show in the item's top-left cell at any width; narrow cells truncate with an ellipsis.
        if(Name){
            const float TitleSpace=W-Left-Right-(P&&P->Enhancement>0?CornerSize:0);
            const FString Title=P?P->Name:I.Definition;const auto Font=GunsmithUI::TextFont(12/Scale);const float Width=FMath::Min(float(Measure->Measure(Title,Font).X*Scale)+8,TitleSpace);
            Box(X+Left,Y+3,Width,16,GunsmithUI::Gray(20,190),FLinearColor::Transparent,3,0,3);Label(Title,X+Left+3,Y+3,12,GunsmithUI::Text,TitleSpace-6);
        }
        if(I.Count>1||I.Definition==TEXT("mineral_water")){const FString Count=I.Definition==TEXT("mineral_water")?FString::Printf(TEXT("%d/2"),FMath::Clamp(int32(Number(I,TEXT("remainingUses"),2)),1,2)):FString::Printf(TEXT("%lld"),I.Count);const float FontSize=12;const float Width=FMath::Min(W-4-(!Hotbar&&P&&P->Crafted?CornerSize+1:0),float(Measure->Measure(Count,GunsmithUI::NumberFont(FontSize/Scale)).X*Scale)+5);
            const float CountX=Hotbar?X+(W-Width)/2:X+W-Width-2-(P&&P->Crafted?CornerSize+1:0),CountY=Hotbar?Y+2:Y+H-FontSize-4;
            Box(CountX,CountY,Width,FontSize+2,GunsmithUI::Gray(10,220),FLinearColor::Transparent,2,0,3);Label(Count,CountX+2,CountY,FontSize,GunsmithUI::Text,Width-2,true);}
        if(I.Cooldown>0){DrawCard(Fade(ColdSteelUI::GlassTint,.65f),FLinearColor::Transparent,3);Label(FString::Printf(TEXT("%.1f"),I.Cooldown),X+4,Y+H/2-6,12,ColdSteelUI::Warning,W-8,true);}
        if(P&&!Hotbar){
            const float Time=GlintSeconds+float(GetTypeHash(I.InstanceId)%1000)/1000.f;
            // 工具强化复用右上加工光晕：只在 ≥2 级点亮，色统一走 ColdSteelUI::Enhanced。
            // 不按档位分色——稀有度已有 6 档语义色，挪用会混淆两套口径。
            if(P->Enhancement>0||P->ToolEnhanceLevel>=2)DrawProcessingCorner(Out,Layer+4,G,Scale,FVector2f(CardMax.X-CornerInset,CardMin.Y+CornerInset),FVector2f(-1,0),FVector2f(0,1),CornerSize,CornerRadius,ColdSteelUI::Enhanced,Time,Opacity);
            if(P->Crafted)DrawProcessingCorner(Out,Layer+4,G,Scale,FVector2f(CardMax.X-CornerInset,CardMax.Y-CornerInset),FVector2f(-1,0),FVector2f(0,-1),CornerSize,CornerRadius,ColdSteelUI::Crafted,Time+.7f,Opacity);
            if(P->Enchanted)DrawProcessingCorner(Out,Layer+4,G,Scale,FVector2f(CardMin.X+CornerInset,CardMax.Y-CornerInset),FVector2f(1,0),FVector2f(0,-1),CornerSize,CornerRadius,ColdSteelUI::Enchanted,Time+1.4f,Opacity);
            // 左下角等级芯片：出厂 1 级也显示 Lv.1（石头与青铜外观差别大，背包里要能分辨）。
            // 工具不可堆叠（Count 恒 1），与右下数量芯片不会重叠。
            if(P->ToolEnhanceLevel>0){
                const FString LevelText=FString::Printf(TEXT("Lv.%d"),P->ToolEnhanceLevel);const float FontSize=12;
                const float Width=FMath::Min(W-4,float(Measure->Measure(LevelText,GunsmithUI::NumberFont(FontSize/Scale)).X*Scale)+5);
                Box(X+2,Y+H-FontSize-4,Width,FontSize+2,GunsmithUI::Gray(10,220),FLinearColor::Transparent,2,0,3);
                Label(LevelText,X+4,Y+H-FontSize-4,FontSize,GunsmithUI::Text,Width-2,true);
            }
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
    Label(FString::Printf(TEXT("%d / %d"),Equipped,SlotNames().Num()),L.Width-92,12,12,GunsmithUI::Secondary,80,true);
    for(int32 N=0;N<SlotNames().Num();++N){const int32 DisplayCell=ColdSteelEquipmentLayout::CellForSlot(N);const float X=12+(DisplayCell%3)*(L.GearWidth+6),Y=L.GearY+(DisplayCell/3)*L.GearPitch;const int32 Index=Owner(Model->Items(),1,N);
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
    // 容量横线走设计系统 2.22 暗金身份层：轨道 ItemTooltipGoldRule、填充 HUDGold（与经验条同源），满仓保留 Warning 语义色。
    Box(12,L.BagY-5,L.Width-24,2,ColdSteelUI::ItemTooltipGoldRule);Box(12,L.BagY-5,(L.Width-24)*FMath::Clamp(Cells/float(Rows*18),0.f,1.f),2,Cells>=Rows*18?ColdSteelUI::Warning:ColdSteelUI::HUDGold);
    Box(12,L.BagY,L.Width-24,L.Cell*Rows,GunsmithUI::Gray(15,95),GunsmithUI::Edge,0);
    for(int32 N=1;N<18;++N)Box(12+N*L.Cell,L.BagY,1,Rows*L.Cell,GunsmithUI::Gray(220,22),FLinearColor::Transparent,0);
    for(int32 N=1;N<Rows;++N)Box(12,L.BagY+N*L.Cell,L.Width-24,1,GunsmithUI::Gray(220,22),FLinearColor::Transparent,0);
    for(const auto& I:Model->Items())if(I.Place==Container&&(!bWarehouse||I.Container==Model->ActiveContainer)&&I.Cell>=Start&&I.Cell<Start+Rows*18)Item(I,12+I.Cell%18*L.Cell,L.BagY+(I.Cell-Start)/18*L.Cell,I.Width*L.Cell,I.Height*L.Cell,true);
    if(HoverPlace==Container&&PointerCell>=Start&&HoverId.IsEmpty())Box(12+PointerCell%18*L.Cell,L.BagY+(PointerCell-Start)/18*L.Cell,L.Cell,L.Cell,Fade(ColdSteelUI::Accent,.04f),Fade(ColdSteelUI::Accent,.65f),2,1,5);
    // 夹层：背包装备（槽14）撑出的独立格空间。标题/计数/分隔线/网格与"空间背包"同款版式，
    // 网格尺寸（长×宽＝列×行）由装备的背包定义，宽度自然随列数伸缩，靠左对齐。
    if(L.CompY>0&&L.CompGrid.X>0)
    {
        const FIntPoint CG=L.CompGrid;const int32 Cap=CG.X*CG.Y;int32 Used=0,CompCount=0;
        for(const auto& I:Model->Items())if(I.Place==ColdSteelCompartment::Place){Used+=I.Width*I.Height;++CompCount;}
        Box(4,L.CompY-36,L.Width-8,CG.Y*L.Cell+42,GunsmithUI::Gray(120,8),GunsmithUI::Gray(220,22),10);
        Label(TEXT("夹层"),12,L.CompY-28,16,GunsmithUI::Text,150);
        Label(FString::Printf(TEXT("%d / %d 格 · %d 件"),Used,Cap,CompCount),L.Width-246,L.CompY-25,12,Used>=Cap?ColdSteelUI::Warning:GunsmithUI::Secondary,180,true);
        Box(L.Width-60,L.CompY-30,48,24,bCompSortHovered?GunsmithUI::Gray(75,200):GunsmithUI::Gray(43,160),bCompSortHovered?GunsmithUI::Silver:GunsmithUI::Edge,4);Label(TEXT("整理"),L.Width-50,L.CompY-25,12,GunsmithUI::Text,38);
        Box(12,L.CompY-5,L.Width-24,2,ColdSteelUI::ItemTooltipGoldRule);Box(12,L.CompY-5,(L.Width-24)*FMath::Clamp(Used/float(Cap),0.f,1.f),2,Used>=Cap?ColdSteelUI::Warning:ColdSteelUI::HUDGold);
        Box(12,L.CompY,CG.X*L.Cell,CG.Y*L.Cell,GunsmithUI::Gray(15,95),GunsmithUI::Edge,0);
        for(int32 N=1;N<CG.X;++N)Box(12+N*L.Cell,L.CompY,1,CG.Y*L.Cell,GunsmithUI::Gray(220,22),FLinearColor::Transparent,0);
        for(int32 N=1;N<CG.Y;++N)Box(12,L.CompY+N*L.Cell,CG.X*L.Cell,1,GunsmithUI::Gray(220,22),FLinearColor::Transparent,0);
        for(const auto& I:Model->Items())if(I.Place==ColdSteelCompartment::Place)Item(I,12+I.Cell%CG.X*L.Cell,L.CompY+I.Cell/CG.X*L.Cell,I.Width*L.Cell,I.Height*L.Cell,true);
        if(HoverPlace==ColdSteelCompartment::Place&&PointerCell>=0&&HoverId.IsEmpty())Box(12+PointerCell%CG.X*L.Cell,L.CompY+PointerCell/CG.X*L.Cell,L.Cell,L.Cell,Fade(ColdSteelUI::Accent,.04f),Fade(ColdSteelUI::Accent,.65f),2,1,5);
    }
    if((PreviewPlace==Container||(PreviewPlace==1&&Container==0))&&bPreviewValid)for(const auto& R:SwapDestinations)Box(12+R.Min.X*L.Cell,L.BagY+R.Min.Y*L.Cell,R.Width()*L.Cell,R.Height()*L.Cell,Fade(ColdSteelUI::Accent,.1f),ColdSteelUI::Accent,2,1,5);
    if(PreviewPlace>=0&&PreviewCell>=0){const auto* I=Model->FindItem(HoverPreview);float X=12,Y=0,W=48,H=L.GearHeight;
        if(PreviewPlace==Container){
            // A drag supplies the pending footprint; external preview setters keep the instance shape.
            FIntPoint PreviewSpan=PreviewCells;
            if(PreviewSpan.X*PreviewSpan.Y<=1&&I&&I->Width*I->Height>1)PreviewSpan=FIntPoint(I->Width,I->Height);
            X+=PreviewCell%18*L.Cell;Y=L.BagY+(PreviewCell-Start)/18*L.Cell;W=FMath::Min(PreviewSpan.X*L.Cell,L.Width-X-12);H=FMath::Min(PreviewSpan.Y*L.Cell,L.BagY+Rows*L.Cell-Y);}
        else if(PreviewPlace==1){const int32 DisplayCell=ColdSteelEquipmentLayout::CellForSlot(PreviewCell);X+=DisplayCell%3*(L.GearWidth+6);Y=L.GearY+DisplayCell/3*L.GearPitch;W=L.GearWidth;}
        else if(PreviewPlace==ColdSteelCompartment::Place){X+=PreviewCell%L.CompGrid.X*L.Cell;Y=L.CompY+PreviewCell/L.CompGrid.X*L.Cell;W=PreviewCells.X*L.Cell;H=PreviewCells.Y*L.Cell;}
        const auto Color=I?(bPreviewValid?ColdSteelUI::Success:ColdSteelUI::Danger):ColdSteelUI::Accent;Box(X,Y,W,H,Fade(Color,.12f),Color,2,2,5);
    }
    FString Message;FLinearColor Tone=GunsmithUI::Secondary;
    if(PreviewPlace>=0&&!PreviewReason.IsEmpty()){Message=PreviewReason;Tone=bPreviewValid?ColdSteelUI::Success:ColdSteelUI::Danger;}
    else if(!InteractionMessage.IsEmpty()){Message=InteractionMessage;Tone=ColdSteelUI::Accent;}
    else if(const auto* P=Presentation.Find(Selected)){Message=TEXT("已选中 · ")+P->Name;Tone=ColdSteelUI::TextPrimary;}
    if(!Message.IsEmpty())Label(Message,12,L.HotY+14,12,Tone,L.Width-24);
    if(bWarehouse)Label(TEXT("单击查看 · 右键取出 · Shift+单击拆分"),12,L.HotY+33,12,ColdSteelUI::TextTertiary,L.Width-24);
    return Layer+6;
}
