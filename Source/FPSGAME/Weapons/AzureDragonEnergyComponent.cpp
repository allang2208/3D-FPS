#include "AzureDragonEnergyComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/HUD.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Rendering/DrawElements.h"
#include "Styling/SlateBrush.h"
#include "Widgets/SLeafWidget.h"

namespace AzureDragonHud
{
const FSoftObjectPath HudMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/HudV10/Materials/M_AzureDragonHudV10.M_AzureDragonHudV10"));
// Texture-space layout baked by HudV10/author_hud.py: 512 x [-256, 2048] quad, horn top 51.7, apex 1991.8.
constexpr float QuadWidth=512.f,QuadHeight=2304.f,QuadTop=-256.f,HornY=51.7f,ApexY=1991.8f,CenterX=256.f;
// User concept (left in-game panel): horn->apex covers 69.4% of the view height,
// the column centre sits 18.9% of the height from the left edge and the horns 5.2% from the top.
constexpr float BarHeight=.694f,CenterFromLeft=.189f,HornFromTop=.052f;
constexpr int32 HudZOrder=15; // Under the Cold Steel HUD (20) so panels and backdrops cover it.
}

/** One additive material quad; Slate gamma is bypassed so the material writes concept display values. */
class SAzureDragonEnergyHud final : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SAzureDragonEnergyHud){}
    SLATE_END_ARGS()
    void Construct(const FArguments&)
    {
        SetVisibility(EVisibility::HitTestInvisible);
        SetCanTick(false);
        ForceVolatile(true); // Flames, fill and floating offset change every frame; one box per paint.
        Brush.DrawAs=ESlateBrushDrawType::Image;
        Brush.ImageSize=FVector2D(AzureDragonHud::QuadWidth,AzureDragonHud::QuadHeight);
    }
    void SetMaterial(UMaterialInstanceDynamic* Material){Brush.SetResourceObject(Material);}
    void SetFrame(bool InShown,float InAlpha,const FVector2f& InOffset){bShown=InShown;Alpha=InAlpha;Offset=InOffset;}
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry& Geometry,const FSlateRect&,FSlateWindowElementList& Out,
        int32 Layer,const FWidgetStyle&,bool) const override
    {
        using namespace AzureDragonHud;
        if(!bShown||Alpha<=.001f||!Brush.GetResourceObject())return Layer;
        const float H=Geometry.GetLocalSize().Y;
        const float Unit=BarHeight*H/(ApexY-HornY);
        const FVector2f Size(QuadWidth*Unit,QuadHeight*Unit);
        const FVector2f Position(CenterFromLeft*H-CenterX*Unit+Offset.X*H,HornFromTop*H-(HornY-QuadTop)*Unit+Offset.Y*H);
        FSlateDrawElement::MakeBox(Out,Layer,Geometry.ToPaintGeometry(Size,FSlateLayoutTransform(Position)),&Brush,
            ESlateDrawEffect::NoGamma|ESlateDrawEffect::NoPixelSnapping,FLinearColor(1.f,1.f,1.f,Alpha));
        return Layer;
    }
    virtual FVector2D ComputeDesiredSize(float) const override{return FVector2D::ZeroVector;}
private:
    FSlateBrush Brush;
    bool bShown=false;
    float Alpha=0.f;
    FVector2f Offset=FVector2f::ZeroVector;
};

UAzureDragonEnergyComponent::UAzureDragonEnergyComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

void UAzureDragonEnergyComponent::Configure(bool Enabled)
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    Enabled=Enabled&&Pawn&&Pawn->IsLocallyControlled();
    if(Enabled!=bEnabled){EntryAge=0.f;bHaveYaw=false;}
    bEnabled=Enabled;
    SetComponentTickEnabled(Enabled);
    if(!Enabled){ClearEnergy();HideDisplay();return;}
    RequestAssets();
    if(HudMaterial)CreateDisplay();
}

void UAzureDragonEnergyComponent::SetEnergy(float NormalizedEnergy,bool Summoned,bool ContactPulse)
{
    TargetEnergy=FMath::Clamp(NormalizedEnergy,0.f,1.f);
    if(ContactPulse)HitAge=0.f;
    if(Summoned){DisplayEnergy=1.f;FlareAge=0.f;}
}

void UAzureDragonEnergyComponent::ClearEnergy()
{
    TargetEnergy=DisplayEnergy=0.f;HitAge=FlareAge=10.f;
}

void UAzureDragonEnergyComponent::RequestAssets()
{
    if(bRequested)return;
    bRequested=true;
    TWeakObjectPtr<UAzureDragonEnergyComponent> Weak(this);
    // The material references its five baked layers, so one async request streams the whole HUD.
    AssetLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(AzureDragonHud::HudMaterialPath,
        FStreamableDelegate::CreateLambda([Weak]()
        {
            if(!Weak.IsValid())return;
            auto* Self=Weak.Get();
            Self->HudMaterial=Cast<UMaterialInterface>(AzureDragonHud::HudMaterialPath.ResolveObject());
            if(Self->bEnabled&&Self->HudMaterial)Self->CreateDisplay();
        }));
}

void UAzureDragonEnergyComponent::CreateDisplay()
{
    if(HudWidget||!HudMaterial)return;
    const auto* Pawn=Cast<APawn>(GetOwner());
    auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    ULocalPlayer* Local=PC?PC->GetLocalPlayer():nullptr;
    UGameViewportClient* Viewport=GetWorld()?GetWorld()->GetGameViewport():nullptr;
    if(!Local||!Viewport)return;
    HudMID=UMaterialInstanceDynamic::Create(HudMaterial,this);
    HudMID->SetScalarParameterValue(TEXT("Reveal"),1.f);
    SAssignNew(HudWidget,SAzureDragonEnergyHud);
    HudWidget->SetMaterial(HudMID);
    Viewport->AddViewportWidgetForPlayer(Local,HudWidget.ToSharedRef(),AzureDragonHud::HudZOrder);
    HudPlayer=Local;
}

void UAzureDragonEnergyComponent::HideDisplay()
{
    if(HudWidget)HudWidget->SetFrame(false,0.f,FVector2f::ZeroVector);
}

void UAzureDragonEnergyComponent::RemoveDisplay()
{
    if(HudWidget)
    {
        UGameViewportClient* Viewport=GetWorld()?GetWorld()->GetGameViewport():nullptr;
        if(Viewport&&HudPlayer.IsValid())Viewport->RemoveViewportWidgetForPlayer(HudPlayer.Get(),HudWidget.ToSharedRef());
        HudWidget->SetMaterial(nullptr);
    }
    HudWidget.Reset();HudPlayer.Reset();HudMID=nullptr;
}

void UAzureDragonEnergyComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(!bEnabled)return;
    if(!HudWidget)CreateDisplay();
    if(!HudWidget||!HudMID)return;
    auto* Pawn=Cast<APawn>(GetOwner());
    auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    if(!Pawn||!PC||!Pawn->IsLocallyControlled()||PC->GetViewTarget()!=Pawn||(PC->MyHUD&&!PC->MyHUD->bShowHUD))
    {HideDisplay();return;}
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
    {ClearEnergy();HideDisplay();return;}
    Age=FMath::Fmod(Age+Delta,3600.f);EntryAge+=Delta;HitAge+=Delta;FlareAge+=Delta;
    // Briefly show the full vessel and flare before presenting the consumed charge; each 1/9 step
    // visibly rises through its segment instead of snapping.
    if(FlareAge>=.20f)DisplayEnergy=FMath::FInterpConstantTo(DisplayEnergy,TargetEnergy,Delta,.85f);
    // A light floating card: slow bob plus inertia against turning, clamped to a few pixels.
    const FRotator View=PC->GetControlRotation();
    const float YawSpeed=bHaveYaw?FMath::FindDeltaAngleDegrees(LastYaw,View.Yaw)/FMath::Max(.001f,Delta):0.f;
    LastYaw=View.Yaw;bHaveYaw=true;
    Sway=FMath::FInterpTo(Sway,FMath::Clamp(-YawSpeed*.000025f,-.006f,.006f),Delta,6.f);
    const FVector2f Offset(Sway,.0035f*FMath::Sin(Age*1.73f+.6f));
    HudWidget->SetFrame(true,FMath::SmoothStep(0.f,.24f,EntryAge),Offset);
    HudMID->SetScalarParameterValue(TEXT("Fill"),DisplayEnergy);
    HudMID->SetScalarParameterValue(TEXT("Age"),Age);
    HudMID->SetScalarParameterValue(TEXT("Pulse"),FMath::Exp(-HitAge*10.f));
    HudMID->SetScalarParameterValue(TEXT("Burst"),1.f-FMath::SmoothStep(.04f,.42f,FlareAge));
}

void UAzureDragonEnergyComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    HideDisplay();
    if(AssetLoad)AssetLoad->CancelHandle();AssetLoad.Reset();
    RemoveDisplay();
    Super::EndPlay(Reason);
}
