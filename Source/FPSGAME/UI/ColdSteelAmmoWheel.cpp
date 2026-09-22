#include "ColdSteelAmmoWheel.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Spacer.h"
#include "Engine/GameInstance.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "HAL/IConsoleManager.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"
#include "Styling/CoreStyle.h"
#include "Styling/SlateBrush.h"

// 预选光标增益：鼠标位移多少屏幕像素等于走满一个半径。数值越小越灵敏。
// 输入层已把 DefaultInput.ini 的轴灵敏度（MouseX/MouseY=0.07）还原成像素，
// 这里只表达手感；旧实现按轴值除以 200，实际要跨屏约 2857 px 才能走满半径。
static TAutoConsoleVariable<float> AmmoWheelPixelsPerRadius(TEXT("fps.AmmoWheel.PixelsPerRadius"),180.f,
    TEXT("Mouse travel in screen pixels that moves the ammo wheel cursor from the centre to the outer ring. Lower is more sensitive; 40 is the floor."),
    ECVF_Default);

// 双持两个圆盘之间的水平间隙（屏幕像素）；盘径按视口宽度收缩以保证 4R+间隙 放得下。
static constexpr float AmmoWheelDualGap=28.f;
// 双盘时盘径低于该值（屏幕像素）就等比缩小扇区文字，避免文字越出盘沿。
static constexpr float AmmoWheelLabelRadius=300.f;
// 冷钢 UI 轮盘材质参数。轮盘是 HUD 覆盖层，不做矩形模糊背板（圆形遮罩成本高且规则只对抽屉要求模糊），
// 改用分层中性玻璃 + 1px 细边表达玻璃厚度；等级色只作标识，银白只作选中与当前状态。
static constexpr float AmmoWheelDeadZone=.30f;    // 盘心死区半径比例（同时是取消区）
static constexpr float AmmoWheelSeam=.0045f;      // 扇区之间的发丝缝（弧度上限）
static constexpr float AmmoWheelHoverLift=1.03f;  // 悬停扇区外沿抬升
static constexpr int32 AmmoWheelRingSegments=96;  // 整圈几何段数
// 图标中心裁切比例。等级图（`ammo_types.json` 的 icon）是整张写实照片：主体（弹药盒与散弹）只占画面
// 中部，四周是照片自带的底板色，7.62 那套甚至是一整块不透明的等级色；而轮盘图标只有 80–96 px，
// 整帧缩下去主体就被色场淹没（用户 2026-09-22 反馈）。这里用同一张纹理、把 UV 收到中间这块，
// 主体放大 1/0.82 ≈ 1.22 倍；弹药袋／背包的格子大，仍用整帧。
static constexpr float AmmoWheelIconFrame=.82f;

const FSlateBrush* UColdSteelAmmoWheel::FramedIcon(const FString& Id) const
{
    if(const auto* Cached=FramedIcons.Find(Id))return Cached->Get();
    // 复制模型那张共享画刷、只改 UV：纹理仍由模型持有，弹药袋／背包／仓库用的原件不受影响。
    const auto* Source=Model?Model->AmmoIcon(Id):nullptr;
    if(!Source){FramedIcons.Add(Id,nullptr);return nullptr;}
    const float Half=AmmoWheelIconFrame*.5f;
    TSharedPtr<FSlateBrush> Brush=MakeShared<FSlateBrush>(*Source);
    Brush->SetUVRegion(FBox2D(FVector2D(.5f-Half,.5f-Half),FVector2D(.5f+Half,.5f+Half)));
    FramedIcons.Add(Id,Brush);return Brush.Get();
}

void UColdSteelAmmoWheel::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    WidgetTree->RootWidget=WidgetTree->ConstructWidget<USpacer>();
    SetVisibility(ESlateVisibility::HitTestInvisible);
}
void UColdSteelAmmoWheel::NativeConstruct()
{Super::NativeConstruct();if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddUObject(this,&ThisClass::RefreshCounts);}
void UColdSteelAmmoWheel::NativeDestruct()
{if(Model)Model->OnChanged.Remove(ChangedHandle);ChangedHandle.Reset();Super::NativeDestruct();}
int32 UColdSteelAmmoWheel::AddDisc(const FString& Id,int32 Hand)
{
    const auto* Gun=Model?Model->FindItem(Id):nullptr;
    if(!Gun)return INDEX_NONE;
    FColdSteelAmmoWheelDisc Disc;
    Disc.Instance=Id;Disc.Hand=Hand;Disc.Choices=Model->CompatibleAmmo(*Gun);
    Disc.LoadedId=Model->AmmoDefinitionFor(*Gun);
    Disc.Caption=ColdSteelInventory::Text(*Gun,TEXT("name"));
    for(const auto& Choice:Disc.Choices)Model->AmmoIcon(Choice.Id);
    if(const auto* Type=Model->AmmoType(Disc.LoadedId))Disc.Caption+=TEXT(" · ")+Type->GroupName;
    if(Hand>=0)Disc.Caption+=(Hand?TEXT(" · 副手"):TEXT(" · 主手"));
    Discs.Add(MoveTemp(Disc));
    return Discs.Num()-1;
}
void UColdSteelAmmoWheel::OpenForWeapon(const FString& Id,int32 Hand)
{
    Discs.Reset();bDualDiscs=false;Pointer=FVector2D::ZeroVector;ActiveDisc=INDEX_NONE;
    AddDisc(Id,Hand);
}
void UColdSteelAmmoWheel::OpenForDualPistols(const FString& MainId,const FString& OffId)
{
    Discs.Reset();Pointer=FVector2D::ZeroVector;ActiveDisc=INDEX_NONE;
    // 左副手、右主手；任何一只手取不到物品就退回单盘（组中心仍在中点，行为不变）。
    AddDisc(OffId,1);AddDisc(MainId,0);
    bDualDiscs=Discs.Num()>1;
}
UColdSteelAmmoWheel::FLayout UColdSteelAmmoWheel::ComputeLayout(const FVector2D& Size) const
{
    FLayout L;L.Size=Size;L.Center=Size*.5;
    L.Scale=ColdSteelUI::PixelScale(this);if(L.Scale<=0.f)L.Scale=1.f;
    L.Gap=AmmoWheelDualGap/L.Scale;
    int32 Count=0;for(const auto& Disc:Discs)Count=FMath::Max(Count,Disc.Choices.Num());
    const float Base=FMath::Clamp(220.f+Count*5.f,240.f,340.f)/L.Scale;
    if(bDualDiscs)
    {
        // 并排两个盘：4R+间隙 放进视口宽度，短边仍按原规则限制（不拉伸成椭圆）。
        const float Width=FMath::Max(160.f/L.Scale,float(Size.X)*.94f-L.Gap);
        L.R=FMath::Min(Base,FMath::Min(Width*.25f,float(Size.Y)*.35f));
    }
    else L.R=FMath::Min(Base,float(FMath::Min(Size.X*.44,Size.Y*.35)));
    L.R=FMath::Max(L.R,1.f);L.Inner=L.R*.30f;
    const float Sep=L.R+L.Gap*.5f;
    L.Offsets.SetNum(Discs.Num());
    for(int32 I=0;I<Discs.Num();++I)
    {
        double X=0.;
        if(bDualDiscs)X=Discs[I].Hand==0?Sep:-Sep;
        L.Offsets[I]=FVector2D(X,0.);
    }
    return L;
}
void UColdSteelAmmoWheel::UpdateHover(const FLayout& Layout)
{
    ActiveDisc=INDEX_NONE;
    for(int32 I=0;I<Discs.Num();++I)
    {
        auto& Disc=Discs[I];
        // 指针（半径比例）折算到该盘自己的原点；不在盘内就不参与本次选择。
        const FVector2D Local=Layout.R>0.f?Pointer-FVector2D(Layout.Offsets[I])/Layout.R:Pointer;
        if(Local.SizeSquared()>1.0){Disc.Hover=INDEX_NONE;continue;}
        ActiveDisc=I;
        const int32 Count=Disc.Choices.Num();
        if(Count==0||Local.SizeSquared()<AmmoWheelDeadZone*AmmoWheelDeadZone){Disc.Hover=INDEX_NONE;continue;}
        // Segment zero is centered at twelve o'clock. Drawing and hit selection
        // use the same 2PI/N step, with no fixed three/six segment limit.
        const double Step=2.*PI/Count;
        const double Angle=FMath::Atan2(Local.Y,Local.X)+HALF_PI;
        const int32 Next=int32(FMath::FloorToDouble(FMath::Fmod(Angle+Step*.5+4.*PI,2.*PI)/Step))%Count;
        const double Distance=Disc.Hover>=0?FMath::Abs(FMath::UnwindRadians(Angle-Disc.Hover*Step)):PI;
        if(Disc.Hover<0||Next==Disc.Hover||Distance>Step*.5+FMath::Min(FMath::DegreesToRadians(4.),Step*.10))Disc.Hover=Next;
    }
}
void UColdSteelAmmoWheel::RefreshCounts()
{
    if(!Model)return;
    // Keep segment positions stable until this opening ends.
    for(auto& Disc:Discs)
    {
        const auto* Gun=Model->FindItem(Disc.Instance);
        for(auto& Choice:Disc.Choices){Choice.Count=Model->PouchCount(Choice.Id);Choice.Current=Gun&&Model->AmmoDefinitionFor(*Gun)==Choice.Id;}
    }
    if(auto Slate=GetCachedWidget())Slate->Invalidate(EInvalidateWidgetReason::Paint);
}
void UColdSteelAmmoWheel::MovePointer(FVector2D Delta)
{
    // Delta 是屏幕像素。Pointer 是半径比例，指针沿鼠标位移积分而不是跟随绝对位置。
    const float PixelsPerRadius=FMath::Max(40.f,AmmoWheelPixelsPerRadius.GetValueOnGameThread());
    Pointer+=Delta/PixelsPerRadius;
    const FLayout Layout=ComputeLayout(GetCachedGeometry().GetLocalSize());
    if(bDualDiscs)
    {
        // 双盘共用一个指针：可以在两盘之间自由穿行，只限制在视口内（留 8px 边距）。
        // 刚加入视口、几何尺寸还是 0 的那一帧不钳制，避免把这一帧的位移吃掉。
        if(Layout.Size.X>0.&&Layout.Size.Y>0.&&Layout.R>0.f)
        {
            const double Margin=8./Layout.Scale/Layout.R;
            const FVector2D Limit(FMath::Max(0.,Layout.Size.X*.5/Layout.R-Margin),FMath::Max(0.,Layout.Size.Y*.5/Layout.R-Margin));
            Pointer.X=FMath::Clamp(Pointer.X,-Limit.X,Limit.X);
            Pointer.Y=FMath::Clamp(Pointer.Y,-Limit.Y,Limit.Y);
        }
    }
    else Pointer=Pointer.GetClampedToMaxSize(.96);
    UpdateHover(Layout);
    if(auto Slate=GetCachedWidget())Slate->Invalidate(EInvalidateWidgetReason::Paint);
}
FString UColdSteelAmmoWheel::SelectedAmmo() const
{
    if(!Discs.IsValidIndex(ActiveDisc))return FString();
    const auto& Disc=Discs[ActiveDisc];
    return Disc.Choices.IsValidIndex(Disc.Hover)&&Disc.Choices[Disc.Hover].Count>0&&!Disc.Choices[Disc.Hover].Current?Disc.Choices[Disc.Hover].Id:FString();
}
const FString& UColdSteelAmmoWheel::WeaponId() const
{
    static const FString Empty;
    if(Discs.IsValidIndex(ActiveDisc))return Discs[ActiveDisc].Instance;
    return Discs.Num()?Discs[0].Instance:Empty;
}
int32 UColdSteelAmmoWheel::NativePaint(const FPaintArgs& Args,const FGeometry& G,const FSlateRect& Cull,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool Enabled) const
{
    Layer=Super::NativePaint(Args,G,Cull,Out,Layer,Style,Enabled);
    if(Discs.IsEmpty())return Layer;
    const FLayout Layout=ComputeLayout(G.GetLocalSize());
    const float Scale=Layout.Scale,R=Layout.R,Inner=Layout.Inner;
    // Mid 是组中心：单盘时就是盘心，双盘时是两盘正中的中点（也是取消区）。
    const FVector2f Mid(Layout.Center);
    const auto Resource=FSlateApplication::Get().GetRenderer()->GetResourceHandle(*FCoreStyle::Get().GetBrush("WhiteBrush"));
    const auto Transform=G.GetAccumulatedRenderTransform();
    auto TextAt=[&](const FString& Text,FVector2f At,float Pixels,const FLinearColor& Color,bool Numeric=false,bool Medium=false)
    {
        const auto Font=Numeric?ColdSteelUI::NumberFont(Pixels*.75f/Scale):ColdSteelUI::TextFont(Pixels*.75f/Scale,Medium);
        const FVector2D Size=FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(Text,Font);
        FSlateDrawElement::MakeText(Out,Layer+4,G.ToPaintGeometry(Size,FSlateLayoutTransform(FVector2D(At)-Size*.5)),Text,Font,ESlateDrawEffect::None,Color);
    };
    // 环形带：Radii 与 Colors 一一对应，沿 A0→A1 生成三角带。整圈（0→2π）用于连续底盘、
    // 内圈环与外沿阴影，单段（扇区起止角）用于扇区与等级标识。几何都建在盘自己的原点上。
    auto Ribbon=[&](int32 L,const FVector2f& C,float A0,float A1,const TArray<float>& Radii,const TArray<FLinearColor>& Colors,int32 Segments)
    {
        const int32 NR=Radii.Num();
        TArray<FSlateVertex> Verts;TArray<SlateIndex> Indices;
        Verts.Reserve((Segments+1)*NR);Indices.Reserve(Segments*(NR-1)*6);
        for(int32 J=0;J<=Segments;++J)
        {
            const float A=FMath::Lerp(A0,A1,float(J)/Segments);const FVector2f Dir(FMath::Cos(A),FMath::Sin(A));
            for(int32 K=0;K<NR;++K)Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(Transform,C+Dir*Radii[K],FVector2f(.5f),Colors[K].ToFColor(true)));
            if(!J)continue;
            for(int32 K=0;K<NR-1;++K)
            {
                const SlateIndex Low=SlateIndex(J*NR+K),High=SlateIndex((J-1)*NR+K);
                Indices.Append({High,Low,SlateIndex(Low+1),High,SlateIndex(Low+1),SlateIndex(High+1)});
            }
        }
        FSlateDrawElement::MakeCustomVerts(Out,L,Resource,Verts,Indices,nullptr,0,0);
    };
    auto Ring=[&](const FVector2f& C,float Radius,float A0,float A1,int32 Segments)
    {
        TArray<FVector2f> Points;
        for(int32 J=0;J<=Segments;++J){const float A=FMath::Lerp(A0,A1,float(J)/Segments);Points.Add(C+FVector2f(FMath::Cos(A),FMath::Sin(A))*Radius);}
        return Points;
    };
    // 非活动盘只压暗盘面（顶点色），不调 RenderOpacity，文字与图标保持清晰。
    auto Dimmed=[&](FLinearColor Color,float Dim){Color.A*=Dim;return Color;};
    for(int32 D=0;D<Discs.Num();++D)
    {
        const auto& Disc=Discs[D];
        if(Disc.Choices.IsEmpty())continue;
        // 每个圆盘有自己的原点：扇区几何、盘心文字与提示都跟着它走。
        const FVector2f Center=Mid+FVector2f(Layout.Offsets[D]);
        const bool Active=!bDualDiscs||D==ActiveDisc;
        const int32 Hover=Active?Disc.Hover:INDEX_NONE;
        const int32 Count=Disc.Choices.Num();
        // 双盘盘径变小，扇区文字按盘径等比收缩；单盘 Fit=1。
        // 比较用屏幕像素（R 是 Slate 单位），否则高 DPI 下会被误判成小盘。
        const float Fit=bDualDiscs?FMath::Clamp(R*Scale/AmmoWheelLabelRadius,.70f,1.f):1.f;
        const float Dim=Active?1.f:.55f;
        // 图标格与文字的径向排布（自上而下倒推，单位 Slate）：
        //   0.707×Side  轴对齐正方形的**角点余量**——四角比外沿多出 0.707×边长
        //   Side/2      图标中心 → 外沿
        //   Side/2      图标中心 → 内沿
        //   文字块      名称 + 数量（状态行交给盘心，见下）
        // 只验算"外沿 ≤ 0.97R"是不够的：96px 的格子在 30°/150° 扇区角点已经到 251 > R=240，
        // 图标就戳出盘沿（用户 2026-09-22 反馈）。所以按"整格内接于 0.97R"反解边长。
        const float Rim=0.97f*R;
        const float HubOut=Inner+6.f/Scale;
        const float NameDrop=18.f*Fit/Scale;     // 图标格（含 4px 凹槽留白）内沿 → 名称中心，留出净空
        const float CountDrop=26.f*Fit/Scale;    // 名称中心 → 数量中心
        const float TextBlock=NameDrop+CountDrop+12.f*Fit/Scale;
        const float CellSide=FMath::Clamp((Rim-HubOut-TextBlock-2.f/Scale)/1.2071f,
            FMath::Min(48.f/Scale,R*.20f),96.f/Scale)*Fit;
        const float CellRho=Rim-0.7071f*CellSide-2.f/Scale;         // 图标中心半径
        const float CellNameRho=CellRho-CellSide*.5f-NameDrop;      // 名称中心半径
        const float CellCountRho=CellNameRho-CountDrop;             // 数量中心半径
        // 图标凹槽：中性深底，不掺等级色；照片自带的色场是这一格唯一的彩色来源。
        FLinearColor SlotFill=ColdSteelUI::Content;SlotFill.A=150.f;
        const double Step=2*PI/Count;
        // 发丝缝取代原来的明显缺口：缝隙里露的是连续底盘，扇区因此看起来是一整盘。
        const float Seam=FMath::Min(AmmoWheelSeam,float(Step)*.012f);
        const int32 Segments=FMath::Max(6,FMath::CeilToInt(288.f/Count));
        // ① 外沿柔和阴影：整盘从世界里浮起来；向外的暗环，不是彩色装饰边框。
        Ribbon(Layer+1,Center,0.f,2.f*PI,{R,R*1.055f},{FLinearColor(0,0,0,.34f*Dim),FLinearColor(0,0,0,0)},AmmoWheelRingSegments);
        // ② 连续玻璃底盘：整盘一圈的中性玻璃底（深底 + 玻璃），把扇区连成一块面。
        Ribbon(Layer+1,Center,0.f,2.f*PI,{Inner*.92f,R},{Dimmed(ColdSteelUI::Content,Dim),Dimmed(ColdSteelUI::GlassTint,Dim)},AmmoWheelRingSegments);
        // ③ 扇区：中性玻璃 + 径向渐变做厚度。银白只给悬停，等级色不作整片染色。
        for(int32 I=0;I<Count;++I)
        {
            const auto& Choice=Disc.Choices[I];
            const bool Selected=I==Hover,Available=Choice.Count>0;
            const float Middle=-HALF_PI+I*Step,Start=Middle-Step*.5f+Seam,End=Middle+Step*.5f-Seam;
            const float Outer=Selected?R*AmmoWheelHoverLift:R;
            FLinearColor Low=ColdSteelUI::Content,High=ColdSteelUI::GlassTint;
            if(Selected){Low=FMath::Lerp(Low,ColdSteelUI::Accent,.18f);High=FMath::Lerp(High,ColdSteelUI::Accent,.26f);}
            if(!Available){Low=FMath::Lerp(Low,ColdSteelUI::ButtonDisabled,.55f);High=FMath::Lerp(High,ColdSteelUI::ButtonDisabled,.45f);}
            Low.A*=.92f*Dim;High.A*=.96f*Dim;
            // 中圈高光带：内暗—中亮—外略收，模拟玻璃厚度与顶面反光。
            FLinearColor Shine=FMath::Lerp(Low,High,.5f);Shine.A=FMath::Min(255.f,High.A*1.12f);
            Ribbon(Layer+2,Center,Start,End,{Inner,Outer*.74f,Outer},{Low,Shine,High},Segments);
            // 扇区细边：中性 1px 收口，悬停换银白；不做等级色描边。
            FSlateDrawElement::MakeLines(Out,Layer+3,G.ToPaintGeometry(),Ring(Center,Outer,Start,End,Segments),ESlateDrawEffect::None,
                Selected?ColdSteelUI::Accent:Dimmed(ColdSteelUI::Border,Dim),true,(Selected?1.6f:1.f)/Scale);
        }
        // ④ 内圈环：把每个扇区的内沿连成一整圈，盘心缺口变成"凹陷的玻璃中心"而不是断开的缝。
        Ribbon(Layer+3,Center,0.f,2.f*PI,{Inner*.94f,Inner*1.03f,Inner*1.12f},
            {Dimmed(ColdSteelUI::Content,Dim),Dimmed(ColdSteelUI::GlassTint,Dim),Dimmed(ColdSteelUI::Content,Dim)},AmmoWheelRingSegments);
        FSlateDrawElement::MakeLines(Out,Layer+3,G.ToPaintGeometry(),Ring(Center,Inner*.94f,0.f,2.f*PI,AmmoWheelRingSegments),ESlateDrawEffect::None,Dimmed(ColdSteelUI::Border,Dim),true,1.f/Scale);
        FSlateDrawElement::MakeLines(Out,Layer+3,G.ToPaintGeometry(),Ring(Center,Inner*1.12f,0.f,2.f*PI,AmmoWheelRingSegments),ESlateDrawEffect::None,Dimmed(ColdSteelUI::Border,Dim),true,1.f/Scale);
        // ⑤ 等级标识：每个扇区在内圈环上占自己那段弧。等级色只出现在这条弧与图标底板上。
        for(int32 I=0;I<Count;++I)
        {
            const auto& Choice=Disc.Choices[I];
            const auto* Type=Model->AmmoType(Choice.Id);
            FLinearColor Marker=Type?Type->TierColor:ColdSteelUI::Border;
            const float Middle=-HALF_PI+I*Step;
            if(Choice.Current)Marker=ColdSteelUI::Accent;          // 当前装填：银白
            else if(Choice.Count==0)Marker.A*=.35f;                // 已用尽：只留淡淡标识
            if(I==Hover)Marker.A=255.f;                            // 悬停：标识点亮
            Ribbon(Layer+3,Center,Middle-float(Step)*.34f,Middle+float(Step)*.34f,{Inner*.99f,Inner*1.07f},
                {Dimmed(Marker,Dim),Dimmed(Marker,.35f*Dim)},FMath::Max(4,Segments/3));
        }
        // ⑥ 外沿收口：一整圈细边；双盘时活动盘再描一圈银白，一眼看出鼠标在哪个盘。
        FSlateDrawElement::MakeLines(Out,Layer+3,G.ToPaintGeometry(),Ring(Center,R,0.f,2.f*PI,AmmoWheelRingSegments),ESlateDrawEffect::None,Dimmed(ColdSteelUI::Border,Dim),true,1.f/Scale);
        if(bDualDiscs)FSlateDrawElement::MakeLines(Out,Layer+3,G.ToPaintGeometry(),Ring(Center,R*1.02f,0.f,2.f*PI,AmmoWheelRingSegments),ESlateDrawEffect::None,
            Dimmed(Active?ColdSteelUI::Accent:ColdSteelUI::Border,Dim),true,(Active?2.f:1.f)/Scale);
        // ⑦ 盘心：深底 + 玻璃面的凹陷中心；指针在死区时描银白，提示松开 R 取消。
        const bool InHub=Active&&FVector2D(Pointer-FVector2D(Layout.Offsets[D])).SizeSquared()<AmmoWheelDeadZone*AmmoWheelDeadZone;
        const auto HubBase=ColdSteelUI::RoundedBrush(FLinearColor::White,Inner*.94f,InHub?ColdSteelUI::Accent:ColdSteelUI::Border,InHub?1.4f/Scale:1.f/Scale);
        FSlateDrawElement::MakeBox(Out,Layer+3,G.ToPaintGeometry(FVector2D(Inner*1.88f),FSlateLayoutTransform(FVector2D(Center)-FVector2D(Inner*.94f))),&HubBase,
            ESlateDrawEffect::None,Dimmed(ColdSteelUI::Content,Dim));
        const auto HubGlass=ColdSteelUI::RoundedBrush(FLinearColor::White,Inner*.78f,ColdSteelUI::Border,1.f/Scale);
        FSlateDrawElement::MakeBox(Out,Layer+3,G.ToPaintGeometry(FVector2D(Inner*1.56f),FSlateLayoutTransform(FVector2D(Center)-FVector2D(Inner*.78f))),&HubGlass,
            ESlateDrawEffect::None,Dimmed(ColdSteelUI::GlassTint,Dim));
        const auto* Selected=Disc.Choices.IsValidIndex(Hover)?&Disc.Choices[Hover]:nullptr;
        // 非活动盘没有待切换目标，盘心显示这只手当前装填什么，提示把鼠标移过来。
        const FColdSteelAmmoChoice* Loaded=nullptr;
        for(const auto& Choice:Disc.Choices)if(Choice.Current){Loaded=&Choice;break;}
        TextAt(Active?(Selected?Selected->Name:TEXT("切换弹种")):Loaded?Loaded->Name:TEXT("切换弹种"),Center-FVector2f(0,18*Fit/Scale),16*Fit,ColdSteelUI::TextPrimary,false,Active&&Selected!=nullptr);
        TextAt(Active?(Selected?FString::Printf(TEXT("%lld 发"),Selected->Count):TEXT("移动鼠标选择")):TEXT("移动鼠标至此"),Center+FVector2f(0,5*Fit/Scale),12*Fit,ColdSteelUI::TextSecondary);
        TextAt(Active?(Selected&&Selected->Count>0&&!Selected->Current?TEXT("松开 R 换弹"):TEXT("松开 R 取消")):FString(),Center+FVector2f(0,26*Fit/Scale),12*Fit,ColdSteelUI::TextSecondary);
        TextAt(Disc.Caption,Center-FVector2f(0,R+47/Scale),16*Fit,ColdSteelUI::TextPrimary);
        const FString EffectId=Selected?Selected->Id:Disc.LoadedId;
        TextAt(Model->AmmoEffectSummary(EffectId),Center-FVector2f(0,R+24/Scale),12*Fit,ColdSteelUI::TextSecondary);
        // ⑧ 扇区内容：图标底板（等级色标记）+ 名称 / 数量 / 状态，字号遵循 24/20/16/14/12 档位。
        for(int32 I=0;I<Count;++I)
        {
            const auto& Choice=Disc.Choices[I];const bool SelectedSector=I==Hover;
            const float Middle=-HALF_PI+float(I)*float(Step);
            // 扇区内容沿**半径方向**排布：外段放图标，内段依次是名称 / 数量 / 状态，全部落在扇区中线上。
            // 以前把偏移量加在屏幕竖直方向（+(0,26/49/73)、-(0,24)），只有 12 点那个扇区碰巧居中；
            // 30°/150° 的扇区整组内容会被推向一侧，图标就不在扇形格子中间（用户 2026-09-22 反馈）。
            const FVector2f Dir(FMath::Cos(Middle),FMath::Sin(Middle));
            auto Along=[&](float Rho){return Center+Dir*Rho;};
            const FVector2f TextAt2=Along(R*.67f);
            const auto Color=Choice.Count==0?ColdSteelUI::TextTertiary:ColdSteelUI::TextPrimary;
            if(Count<=8)
            {
                // 等级图是整张照片：主体在中间，四周是画面自带的底板色（7.62 甚至是整块不透明等级色）。
                // 所以轮盘上用中心裁切版本把主体放大，底板只做中性凹槽，不再叠加等级色——
                // 以前"照片自带色场 + 等级色底板"两层色块叠在一起，主体被淹没。等级色只留在内圈标识弧上。
                const auto* Icon=Count<=6?FramedIcon(Choice.Id):nullptr;
                if(Icon)
                {
                    // 悬停放大只向内长：外沿与四角留在原处，不会因为悬停而戳出盘沿。
                    const float Side=CellSide*(SelectedSector?1.06f:1.f);
                    const FVector2D IconSize(Side);
                    const FVector2D IconAt=FVector2D(Along(CellRho-(Side-CellSide)*.5f))-IconSize*.5;
                    const float Pad=4.f/Scale;
                    const auto IconSlot=ColdSteelUI::RoundedBrush(FLinearColor::White,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1.f/Scale);
                    FSlateDrawElement::MakeBox(Out,Layer+4,G.ToPaintGeometry(IconSize+FVector2D(Pad*2),FSlateLayoutTransform(IconAt-FVector2D(Pad))),&IconSlot,
                        ESlateDrawEffect::None,Dimmed(SlotFill,Dim));
                    FSlateDrawElement::MakeBox(Out,Layer+4,G.ToPaintGeometry(IconSize,FSlateLayoutTransform(IconAt)),Icon,
                        ESlateDrawEffect::None,Choice.Count==0?FLinearColor(.55f,.55f,.55f,1):FLinearColor::White);
                }
                // 名称与数量留在格内；"当前装填／已用尽／待切换"不再占格——盘心已经显示悬停项的名称、
                // 剩余发数与动作提示，当前装填另有内圈银白标识弧，状态行是冗余的，去掉它才腾出图标的位置。
                TextAt(Choice.Name,Along(Icon?CellNameRho:R*.67f+21.f*Fit/Scale),14*Fit,Color,false,SelectedSector);
                TextAt(FString::Printf(TEXT("%lld"),Choice.Count),Along(Icon?CellCountRho:R*.67f-2.f*Fit/Scale),20*Fit,Color,true);
            }
            else if(Count<=24)TextAt(FString::FromInt(I+1),TextAt2,14*Fit,Color,true);
            // Dense wheels still split equally; full hovered names/counts live in the
            // hub, rather than shrinking or overlapping sector text.
        }
    }
    if(bDualDiscs)
    {
        TextAt(TEXT("移动鼠标到左／右圆盘选弹 · 松开 R 换弹"),Mid+FVector2f(0,R+24/Scale),14,ColdSteelUI::TextPrimary);
        TextAt(TEXT("移到两盘之间或盘心取消 · Esc 取消"),Mid+FVector2f(0,R+46/Scale),12,ColdSteelUI::TextSecondary);
    }
    else
    {
        TextAt(TEXT("移动鼠标选择 · 松开 R 换弹"),Mid+FVector2f(0,R+24/Scale),14,ColdSteelUI::TextPrimary);
        TextAt(TEXT("移回中心取消 · Esc 取消"),Mid+FVector2f(0,R+46/Scale),12,ColdSteelUI::TextSecondary);
    }
    // ⑨ 指针：银白圆点 + 深色描边；悬停在可提交弹种上时加一圈淡淡银白光晕。
    const FVector2f Point=Mid+FVector2f(Pointer)*R;
    if(!SelectedAmmo().IsEmpty())
    {
        const auto Glow=ColdSteelUI::RoundedBrush(FLinearColor::White,7.f/Scale,FLinearColor::Transparent,0.f);
        FSlateDrawElement::MakeBox(Out,Layer+5,G.ToPaintGeometry(FVector2D(14/Scale),FSlateLayoutTransform(FVector2D(Point)-FVector2D(7/Scale))),&Glow,
            ESlateDrawEffect::None,FLinearColor(ColdSteelUI::Accent.R,ColdSteelUI::Accent.G,ColdSteelUI::Accent.B,.28f));
    }
    const auto Dot=ColdSteelUI::RoundedBrush(FLinearColor::White,4/Scale,FLinearColor::Black,1/Scale);
    FSlateDrawElement::MakeBox(Out,Layer+5,G.ToPaintGeometry(FVector2D(8/Scale),FSlateLayoutTransform(FVector2D(Point)-FVector2D(4/Scale))),&Dot,ESlateDrawEffect::None,ColdSteelUI::TextPrimary);
    return Layer+5;
}