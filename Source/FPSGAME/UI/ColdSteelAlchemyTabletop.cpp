#include "ColdSteelAlchemyWidget.h"
#include "ColdSteelUIStyle.h"
#include "../Building/AlchemySystem.h"
#include "../Building/PotionWorkbenchVisualComponent.h"
#include "../Building/AlchemyWorkbenchLayout.h"
#include "Components/TextBlock.h"
#include "Components/Border.h"
#include "Components/CanvasPanelSlot.h"
#include "Blueprint/SlateBlueprintLibrary.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "Input/Reply.h"

bool UColdSteelAlchemyWidget::CanTableAct(int32 Id) const
{
    if(!bWorld||bBook||bReturn||bClose||!System||!System->Active()||System->Pending()||System->Saving()||System->Bottling())return false;
    if(!TableVisual.IsValid()||!TableVisual->MatchesSession(WorkingPawn.Get(),System->Job().Id))return false;
    if(Id>=40&&Id<=45)return true;
    if(System->ToolBusy())return false;const auto* R=Recipe();if(!R)return false;const auto& J=System->Job();
    if(Id>=100&&Id<103)
    {
        const int32 I=Id-100;if(!R->Inputs.IsValidIndex(I))return false;const auto& In=R->Inputs[I];
        return !(R->AutoBase&&In.Item==TEXT("alchemy_pure_base_fluid"))&&J.Poured.FindRef(In.Item)<In.Count;
    }
    if(Id>=200&&Id<203)return System->CanGrind(Id-200);
    if(Id==31||Id==32)return !J.Poured.IsEmpty();
    const int32 Current=System->StepIndex();
    if(Id==70)return R->FreeBrewing||(R->Steps.IsValidIndex(Current)&&R->Steps[Current].Action==TEXT("heat"));
    if(Id==50)return !J.Poured.IsEmpty()&&J.Temperature<=R->BottleHeat&&(R->FreeBrewing||Current==R->Steps.Num());
    return false;
}
bool UColdSteelAlchemyWidget::PointerRay(FVector& Origin,FVector& Direction) const
{
    if(!GetOwningPlayer())return false;FVector2D Pixels,Viewport;
    USlateBlueprintLibrary::AbsoluteToViewport(this,PointerScreen,Pixels,Viewport);
    return GetOwningPlayer()->DeprojectScreenPositionToWorld(Pixels.X,Pixels.Y,Origin,Direction);
}
FAlchemyTableHit UColdSteelAlchemyWidget::TableHit() const
{
    if(!bWorld||bBook||!TableVisual.IsValid())return {};
    FVector Origin,Direction;return PointerRay(Origin,Direction)?TableVisual->TraceTabletop(Origin,Direction.GetSafeNormal()):FAlchemyTableHit{};
}
bool UColdSteelAlchemyWidget::BeginStirDrag()
{
    if(!TableVisual.IsValid()||!GetOwningPlayer())return false;
    const FTransform Frame=TableVisual->StirFrame();FVector2D X,Y;
    if(!GetOwningPlayer()->ProjectWorldLocationToScreen(Frame.GetLocation(),StirCenter)||
        !GetOwningPlayer()->ProjectWorldLocationToScreen(Frame.TransformPosition(FVector(10,0,0)),X)||
        !GetOwningPlayer()->ProjectWorldLocationToScreen(Frame.TransformPosition(FVector(0,10,0)),Y))return false;
    StirAxisX=X-StirCenter;StirAxisY=Y-StirCenter;
    return FMath::Abs(StirAxisX.X*StirAxisY.Y-StirAxisX.Y*StirAxisY.X)>1.e-4;
}
bool UColdSteelAlchemyWidget::PointerStirAngle(float& Angle) const
{
    FVector2D Pixels,Viewport;USlateBlueprintLibrary::AbsoluteToViewport(this,PointerScreen,Pixels,Viewport);
    const FVector2D D=Pixels-StirCenter;
    const double Det=StirAxisX.X*StirAxisY.Y-StirAxisX.Y*StirAxisY.X;
    if(FMath::Abs(Det)<=1.e-4)return false;
    // Projected pot-plane axes preserve clockwise/counterclockwise motion at
    // every cursor radius. Only the initial hit must be on the pot or spoon.
    const FVector2D P((D.X*StirAxisY.Y-D.Y*StirAxisY.X)/Det,(StirAxisX.X*D.Y-StirAxisX.Y*D.X)/Det);
    if(P.SizeSquared()<.16)return false; // 4 cm dead zone prevents flips across the centre.
    Angle=FMath::Atan2(P.Y,P.X);return true;
}
void UColdSteelAlchemyWidget::UpdateHover()
{
    if(!HoverPopup||!System||!bWorld||bBook||bReturn||bClose||bEnded||!FSlateApplication::IsInitialized()||!FSlateApplication::Get().IsActive())
    {if(HoverPopup)HoverPopup->SetVisibility(ESlateVisibility::Collapsed);if(TableVisual.IsValid())TableVisual->SetHoverTarget({},false);SetCursor(EMouseCursor::Default);return;}
    auto Hit=TableHit();const auto* R=Recipe();FString Title,Hint;bool Available=false;
    if(bDragging){Hit.Object=EAlchemyTableObject::Liquid;Title=TEXT("搅拌药液");Hint=TEXT("按住左键绕锅心画圈，移出锅沿也能继续。\n停住鼠标即停转，松开左键放回搅拌棒。");Available=true;}
    else if(bWorldHold){Hit.Object=EAlchemyTableObject::Mortar;Title=TEXT("正在研磨");Hint=TEXT("按住左键研磨，松开停止。\n观察粉末由粗粒变细，研磨后再点材料投入坩埚。");Available=true;}
    else switch(Hit.Object)
    {
        case EAlchemyTableObject::Ingredient:
            if(R&&R->Inputs.IsValidIndex(Hit.Ingredient)&&IngredientNames.IsValidIndex(Hit.Ingredient))
            {
                const auto& In=R->Inputs[Hit.Ingredient];const int64 Left=FMath::Max<int64>(0,In.Count-System->Job().Poured.FindRef(In.Item));
                Title=FString::Printf(TEXT("%s · 余 %lld 份"),*IngredientNames[Hit.Ingredient],Left);
                const bool Grind=CanTableAct(200+Hit.Ingredient);Available=CanTableAct(100+Hit.Ingredient)||Grind;
                if(R->AutoBase&&In.Item==TEXT("alchemy_pure_base_fluid"))Hint=TEXT("开炉时已加入基液，这瓶不需要再点。");
                else if(Left==0)Hint=TEXT("本炉备料已全部投入。");
                else {Hint=TEXT("左键：拿起这瓶材料，投入一份。 ");if(Grind)Hint+=TEXT("\n右键：选入研钵，再按住研钵研磨。");else Hint+=TEXT("加入时机请查手册。");}
            }
            break;
        case EAlchemyTableObject::Book:Title=TEXT("配方手册");Hint=TEXT("左键翻阅。按手册决定用料、火候与搅拌；观察药液判断是否融合。");Available=R!=nullptr;break;
        case EAlchemyTableObject::Mortar:
            Title=TEXT("研钵");Available=CanTableAct(200+SelectedGrind);
            Hint=Available&&IngredientNames.IsValidIndex(SelectedGrind)?TEXT("当前材料：")+IngredientNames[SelectedGrind]+TEXT("\n按住左键研磨，松开停止。"):
                TEXT("右键点选需要研磨的材料，再操作研钵。\n无需研磨或已经磨细的材料可直接投入。");break;
        case EAlchemyTableObject::Heater:
        {
            static const TCHAR* Fires[]={TEXT("关闭"),TEXT("低火"),TEXT("中火"),TEXT("高火")};
            Title=FString::Printf(TEXT("火候旋钮 · %s"),Fires[FMath::Clamp(System->Heat(),0,3)]);
            Hint=TEXT("左键升一档；右键降一档；滚轮同样可调节。\n档位：关火、低火、中火、高火，到边界停止。");Available=CanTableAct(40);break;
        }
        case EAlchemyTableObject::Liquid:
        case EAlchemyTableObject::Stirrer:
            Title=TEXT("搅拌棒与药液");Hint=TEXT("按住左键绕锅心拖动，移出锅沿也能继续。\n转动方向和圈数由你的拖动决定，松开停止。");Available=CanTableAct(31);break;
        case EAlchemyTableObject::Hourglass:
            Title=TEXT("十秒沙漏");Hint=System->TimerRunning()?TEXT("正在计时。左键重新翻转；沙漏仅辅助估时。"):TEXT("左键翻转计时。是否需要熬煮请查手册。");Available=CanTableAct(70);break;
        case EAlchemyTableObject::Bottle:
            Title=TEXT("成品量瓶与汤勺");Available=CanTableAct(50);
            Hint=R&&System->Job().Temperature>R->BottleHeat?FString::Printf(TEXT("药液过热，需降至 %.0f °C 以下。\n右侧火候旋钮可关火。"),R->BottleHeat):
                TEXT("左键收火、舀取并装瓶，结束本炉。\n过早装瓶会失败，先按手册观察药液是否炼成。");break;
        case EAlchemyTableObject::Decoration:
            Title=TEXT("背景瓶架 · 陈列物");Hint=TEXT("这里的瓶子不参与当前炼制。\n本炉材料在左侧金属托盘内，悬停可查看名称和用法。");break;
        default:break;
    }
    if(!bDragging&&!bWorldHold&&Hit.Object!=EAlchemyTableObject::Book&&Hit.Object!=EAlchemyTableObject::Decoration&&
        (System->Pending()||System->Saving()||System->Bottling()||(System->ToolBusy()&&Hit.Object!=EAlchemyTableObject::Heater)))
    {Available=false;Hint=System->Saving()?TEXT("正在保存本炉，请稍候。"):System->Bottling()?TEXT("正在舀取、装瓶并放回器具，请稍候。"):TEXT("等待当前器具操作结束后再点击。");}
    if(Hit.Object!=EAlchemyTableObject::None&&Hit.Object!=EAlchemyTableObject::Book&&Hit.Object!=EAlchemyTableObject::Decoration&&
        (!TableVisual.IsValid()||!TableVisual->MatchesSession(WorkingPawn.Get(),System->Job().Id)))
    {Available=false;Hint=TEXT("台面正在同步本炉材料与器具，请稍候。");}
    if(TableVisual.IsValid())TableVisual->SetHoverTarget(Hit,Available);
    SetCursor(Available?EMouseCursor::Hand:EMouseCursor::Default);
    HoverPopup->SetVisibility(Title.IsEmpty()?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
    if(Title.IsEmpty())return;
    if(HoverTitle->GetText().ToString()!=Title)HoverTitle->SetText(FText::FromString(Title));
    if(HoverText->GetText().ToString()!=Hint)HoverText->SetText(FText::FromString(Hint));
    HoverTitle->SetColorAndOpacity(Available?ColdSteelUI::HUDGoldLight:ColdSteelUI::TextSecondary);
    const FGeometry G=GetCachedGeometry();const FVector2D Size=G.GetLocalSize(),Mouse=G.AbsoluteToLocal(PointerScreen);
    const FVector2D BoxSize(380/Scale,126/Scale);FVector2D Position=Mouse+FVector2D(20/Scale,22/Scale);
    if(Position.X+BoxSize.X>Size.X-8/Scale)Position.X=Mouse.X-BoxSize.X-20/Scale;
    if(Position.Y+BoxSize.Y>Size.Y-8/Scale)Position.Y=Mouse.Y-BoxSize.Y-14/Scale;
    Position.X=FMath::Clamp(Position.X,8./Scale,FMath::Max(8./Scale,Size.X-BoxSize.X-8/Scale));
    Position.Y=FMath::Clamp(Position.Y,8./Scale,FMath::Max(8./Scale,Size.Y-BoxSize.Y-8/Scale));
    if(HoverPopupSlot.IsValid())HoverPopupSlot->SetPosition(Position);
}
FReply UColdSteelAlchemyWidget::NativeOnMouseButtonDown(const FGeometry& G,const FPointerEvent& E)
{
    PointerScreen=E.GetScreenSpacePosition();
    if(bBook)return FReply::Handled();if(!bWorld||!System)return Super::NativeOnMouseButtonDown(G,E);
    if(bDragging||bWorldHold)return FReply::Handled();
    const auto Hit=TableHit();const bool Left=E.GetEffectingButton()==EKeys::LeftMouseButton,Right=E.GetEffectingButton()==EKeys::RightMouseButton;
    if(Left&&Hit.Object==EAlchemyTableObject::Book){Book(true);return FReply::Handled();}
    if(Hit.Object==EAlchemyTableObject::Heater)
    {if(Left)Act(44);else if(Right)Act(45);return FReply::Handled();}
    if(Hit.Object==EAlchemyTableObject::Ingredient)
    {
        if(Left)Act(100+Hit.Ingredient);
        else if(Right&&CanTableAct(200+Hit.Ingredient)){Stop();SelectedGrind=Hit.Ingredient;Refresh();}
        return FReply::Handled();
    }
    if(!Left)return FReply::Handled();
    if(Hit.Object==EAlchemyTableObject::Mortar&&CanTableAct(200+SelectedGrind))
    {Stop();Act(200+SelectedGrind);bWorldHold=Held>=200;if(bWorldHold)return FReply::Handled().CaptureMouse(TakeWidget());}
    if((Hit.Object==EAlchemyTableObject::Liquid||Hit.Object==EAlchemyTableObject::Stirrer)&&CanTableAct(31))
    {
        Stop();if(!BeginStirDrag()||!System->Input(EAlchemyOp::Stir,0,0))return FReply::Handled();
        bDragging=true;Held=31;InputClock=0;
        bHasStirAngle=PointerStirAngle(DragAngle);
        return FReply::Handled().CaptureMouse(TakeWidget());
    }
    if(Hit.Object==EAlchemyTableObject::Hourglass)Act(70);
    else if(Hit.Object==EAlchemyTableObject::Bottle)Act(50);
    return FReply::Handled();
}
FReply UColdSteelAlchemyWidget::NativeOnMouseMove(const FGeometry& G,const FPointerEvent& E)
{
    PointerScreen=E.GetScreenSpacePosition();
    if(bDragging)
    {
        if(!E.IsMouseButtonDown(EKeys::LeftMouseButton)){Stop();return FReply::Handled().ReleaseMouseCapture();}
        float Angle;if(!PointerStirAngle(Angle)){bHasStirAngle=false;return FReply::Handled();}
        if(bHasStirAngle)
        {
            const float Change=FMath::FindDeltaAngleRadians(DragAngle,Angle);
            if(FMath::Abs(Change)<PI*.5f){Held=Change>0?32:31;DragRadians+=Change;}
        }
        DragAngle=Angle;bHasStirAngle=true;return FReply::Handled();
    }
    UpdateHover();return Super::NativeOnMouseMove(G,E);
}
FReply UColdSteelAlchemyWidget::NativeOnMouseButtonUp(const FGeometry& G,const FPointerEvent& E)
{
    PointerScreen=E.GetScreenSpacePosition();
    if(E.GetEffectingButton()==EKeys::LeftMouseButton&&(bDragging||bWorldHold)){Stop();return FReply::Handled().ReleaseMouseCapture();}
    return Super::NativeOnMouseButtonUp(G,E);
}
FReply UColdSteelAlchemyWidget::NativeOnMouseWheel(const FGeometry& G,const FPointerEvent& E)
{
    PointerScreen=E.GetScreenSpacePosition();
    if(!bBook&&bWorld&&TableHit().Object==EAlchemyTableObject::Heater)
    {if(E.GetWheelDelta()!=0)Act(E.GetWheelDelta()>0?44:45);return FReply::Handled();}
    return Super::NativeOnMouseWheel(G,E);
}
void UColdSteelAlchemyWidget::NativeOnMouseCaptureLost(const FCaptureLostEvent& E)
{if(bDragging||bWorldHold)Stop();Super::NativeOnMouseCaptureLost(E);}
