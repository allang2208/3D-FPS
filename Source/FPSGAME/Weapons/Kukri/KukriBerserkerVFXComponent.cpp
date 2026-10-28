#include "KukriBerserkerVFXComponent.h"
#include "KukriWeaponComponent.h"
#include "KukriArmsMeshComponent.h"
#include "OffhandKukriComponent.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/HUD.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
#include "Rendering/DrawElements.h"
#include "Styling/SlateBrush.h"
#include "Widgets/SLeafWidget.h"

namespace BerserkerFX
{
constexpr int32 PerHand=128,CoreCount=96;
const FSoftObjectPath EdgePath(TEXT("/Game/Weapons/Kukri20261020/Berserker20261028/ActiveFX/M_BerserkerEdge.M_BerserkerEdge"));
const FSoftObjectPath EmberPath(TEXT("/Game/Weapons/Kukri20261020/Berserker20261028/ActiveFX/M_BerserkerEmber.M_BerserkerEmber"));
const FSoftObjectPath WeaponPath(TEXT("/Game/Weapons/Kukri20261020/Berserker20261028/ActiveFX/M_BerserkerWeaponGlow.M_BerserkerWeaponGlow"));
const FSoftObjectPath PlanePath(TEXT("/Engine/BasicShapes/Plane.Plane"));
const FSoftObjectPath FrostEmberPath(TEXT("/Game/Weapons/Kukri20261020/FrostRaven20261028/ActiveFX/M_FrostRavenEmber.M_FrostRavenEmber"));
const FSoftObjectPath FrostWeaponPath(TEXT("/Game/Weapons/Kukri20261020/FrostRaven20261028/ActiveFX/M_FrostRavenWeaponGlow.M_FrostRavenWeaponGlow"));
bool Visible(const USkeletalMeshComponent* Mesh)
{return Mesh&&Mesh->IsRegistered()&&Mesh->IsVisible()&&!Mesh->bHiddenInGame;}
}

class SKukriBerserkerEdge final : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SKukriBerserkerEdge){}
    SLATE_END_ARGS()
    void Construct(const FArguments&)
    {SetVisibility(EVisibility::HitTestInvisible);SetCanTick(false);ForceVolatile(true);Brush.DrawAs=ESlateBrushDrawType::Image;}
    void SetMaterial(UMaterialInstanceDynamic* Material){Brush.SetResourceObject(Material);}
    void Show(bool Value){bShown=Value;}
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry& Geometry,const FSlateRect&,
        FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle&,bool) const override
    {
        if(!bShown||!Brush.GetResourceObject())return Layer;
        FSlateDrawElement::MakeBox(Out,Layer,Geometry.ToPaintGeometry(),&Brush,
            ESlateDrawEffect::NoGamma,FLinearColor::White);
        return Layer;
    }
    virtual FVector2D ComputeDesiredSize(float) const override{return FVector2D::ZeroVector;}
private:
    FSlateBrush Brush;
    bool bShown=false;
};

UKukriBerserkerVFXComponent::UKukriBerserkerVFXComponent()
{
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
bool UKukriBerserkerVFXComponent::UsesWorldBody() const
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    return Pawn&&(!Pawn->IsLocallyControlled()||(Body&&Body->IsThirdPersonViewEnabled()));
}
void UKukriBerserkerVFXComponent::SetState(bool Equipped,float Seconds,uint8 Hands,const TArray<FString>& Instances)
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    bEquipped=Equipped&&Pawn&&GetNetMode()!=NM_DedicatedServer;
    if(WeaponInstances!=Instances){WeaponInstances=Instances;ResolveAge=0.f;}
    const bool Active=bEquipped&&Seconds>0.f;
    if(Active&&!bActive){Age=EntryAge=ResolveAge=0.f;ResolveHands();}
    if(Active&&!UsesWorldBody())
    {if(HandMask!=Hands)ResolveAge=0.f;HandMask=Hands;}
    bActive=Active;
    if(!bActive)RestoreWeaponOverlays();
    if(!bEquipped){Strength=0.f;HandMask=0;Hide();}
    else RequestAssets();
    SetComponentTickEnabled(bActive||Strength>.001f);
}
void UKukriBerserkerVFXComponent::RequestAssets()
{
    if(bRequested)return;
    bRequested=true;
    TWeakObjectPtr<UKukriBerserkerVFXComponent> Weak(this);
    const FSoftObjectPath EmberPath=bFrostRaven?BerserkerFX::FrostEmberPath:BerserkerFX::EmberPath;
    const FSoftObjectPath WeaponPath=bFrostRaven?BerserkerFX::FrostWeaponPath:BerserkerFX::WeaponPath;
    TArray<FSoftObjectPath> Paths{EmberPath,WeaponPath,BerserkerFX::PlanePath};
    if(!bFrostRaven)Paths.Add(BerserkerFX::EdgePath);
    Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(
        Paths,FStreamableDelegate::CreateLambda([Weak,EmberPath,WeaponPath]()
        {
            if(!Weak.IsValid())return;
            auto* Self=Weak.Get();
            if(!Self->bFrostRaven)Self->EdgeMaterial=Cast<UMaterialInterface>(BerserkerFX::EdgePath.ResolveObject());
            Self->EmberMaterial=Cast<UMaterialInterface>(EmberPath.ResolveObject());
            Self->WeaponMaterial=Cast<UMaterialInterface>(WeaponPath.ResolveObject());
            Self->Plane=Cast<UStaticMesh>(BerserkerFX::PlanePath.ResolveObject());
            if(Self->bEquipped)Self->CreatePresentation();
        }));
}
void UKukriBerserkerVFXComponent::CreatePresentation()
{
    auto* Pawn=Cast<APawn>(GetOwner());
    auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    auto* Local=PC?PC->GetLocalPlayer():nullptr;
    auto* Viewport=GetWorld()?GetWorld()->GetGameViewport():nullptr;
    if(!UsesWorldBody()&&(!Local||!Viewport))return;
    if(!WeaponMID&&WeaponMaterial)
    {
        WeaponMID=UMaterialInstanceDynamic::Create(WeaponMaterial,this);
        WeaponMID->SetScalarParameterValue(TEXT("Strength"),0.f);
        ResolveAge=0.f;
    }
    if(!Overlay&&EdgeMaterial&&Local&&Viewport)
    {
        EdgeMID=UMaterialInstanceDynamic::Create(EdgeMaterial,this);
        EdgeMID->SetScalarParameterValue(TEXT("Strength"),0.f);
        SAssignNew(Overlay,SKukriBerserkerEdge);Overlay->SetMaterial(EdgeMID);
        Viewport->AddViewportWidgetForPlayer(Local,Overlay.ToSharedRef(),11);HudPlayer=Local;
    }
    if(Emitters.Num()==2||!Plane||!EmberMaterial)return;
    for(int32 Side=0;Side<2;++Side)
    {
        auto* FX=NewObject<UInstancedStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);
        FX->SetupAttachment(GetOwner()->GetRootComponent());FX->SetMobility(EComponentMobility::Movable);
        FX->SetStaticMesh(Plane);FX->SetMaterial(0,EmberMaterial);FX->SetNumCustomDataFloats(3);
        FX->SetCollisionEnabled(ECollisionEnabled::NoCollision);FX->SetGenerateOverlapEvents(false);
        FX->SetCanEverAffectNavigation(false);FX->SetCastShadow(false);
        FX->bReceivesDecals=false;FX->bAffectDistanceFieldLighting=false;FX->bVisibleInRayTracing=false;
        FX->SetOnlyOwnerSee(!UsesWorldBody());FX->SetVisibility(false);FX->SetTranslucentSortPriority(2);
        FX->PreAllocateInstancesMemory(BerserkerFX::PerHand);
        ParticleTransforms[Side].Init(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector),BerserkerFX::PerHand);
        FX->AddInstances(ParticleTransforms[Side],false,false,false);FX->RegisterComponent();
        Emitters.Add(FX);
    }
}
void UKukriBerserkerVFXComponent::ResolveHands()
{
    const auto* Main=GetOwner()->FindComponentByClass<UKukriWeaponComponent>();
    const auto* Off=GetOwner()->FindComponentByClass<UOffhandKukriComponent>();
    USkeletalMeshComponent* Right=Main&&Main->IsEquipped()?Main->ArmsMesh():nullptr;
    USkeletalMeshComponent* Left=Main&&Main->IsDual()?Right:Off&&Off->OwnsLeftHand()?Off->ArmsMesh():nullptr;
    if(UsesWorldBody())
    {
        auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
        Right=Left=Body?Body->GetBodyMesh():nullptr;
    }
    USkeletalMeshComponent* Sources[]={Right,Left};
    for(int32 Side=0;Side<2;++Side)
    {
        if(HandSources[Side].Get()==Sources[Side])continue;
        if(auto* Previous=HandSources[Side].Get())RemoveTickPrerequisiteComponent(Previous);
        HandSources[Side]=Sources[Side];
        if(Sources[Side])AddTickPrerequisiteComponent(Sources[Side]);
    }
}
void UKukriBerserkerVFXComponent::UpdateHands(const FTransform& View)
{
    using namespace BerserkerFX;
    if(Emitters.Num()!=2)return;
    const FVector Forward=View.GetUnitAxis(EAxis::X),ViewUp=View.GetUnitAxis(EAxis::Z);
    // Keep the rise vertical even while looking up/down; use the view only for billboards.
    const FVector Up=FVector::UpVector;
    for(int32 Side=0;Side<2;++Side)
    {
        auto* FX=Emitters[Side].Get();auto* Source=HandSources[Side].Get();
        const FName Hand=Side?TEXT("hand_l"):TEXT("hand_r");
        const bool Show=(HandMask&(1<<Side))&&Visible(Source)&&Source->DoesSocketExist(Hand)&&!Source->IsBoneHiddenByName(Hand);
        FX->SetVisibility(Show);
        if(!Show)continue;
        if(FX->bOnlyOwnerSee==UsesWorldBody())FX->SetOnlyOwnerSee(!UsesWorldBody());
        if(FX->FirstPersonPrimitiveType!=Source->FirstPersonPrimitiveType)FX->SetFirstPersonPrimitiveType(Source->FirstPersonPrimitiveType);
        const FName Lower=Side?TEXT("lowerarm_l"):TEXT("lowerarm_r");
        const FName Finger=Side?TEXT("middle_02_l"):TEXT("middle_02_r");
        const FTransform Frame=Source->GetSocketTransform(Hand);
        const FVector Wrist=Frame.GetLocation();
        const FVector LowerPos=Source->DoesSocketExist(Lower)?Source->GetSocketLocation(Lower):Wrist-Frame.GetUnitAxis(EAxis::X)*20.;
        const FVector Axis=(Wrist-LowerPos).GetSafeNormal(UE_SMALL_NUMBER,Frame.GetUnitAxis(EAxis::X));
        FVector A,B;Axis.FindBestAxisVectors(A,B);
        const FVector Center=Source->DoesSocketExist(Finger)?FMath::Lerp(Wrist,Source->GetSocketLocation(Finger),.4):Wrist;
        for(int32 I=0;I<PerHand;++I)
        {
            const bool Wisp=I>=CoreCount;
            const float Seed=FMath::Frac(I*.61803399f+Side*.173f);
            const float AlongArm=FMath::Frac(I*.75487766f+.31f);
            const float Duration=(Wisp?2.2f:1.4f)+Seed*(Wisp?1.1f:1.2f);
            const float Life=FMath::Frac(Age/Duration+float(I)/PerHand);
            const float Phase=I*2.399963f+Side*.7f;
            const FVector Radial=A*FMath::Cos(Phase)+B*FMath::Sin(Phase);
            const float Radius=3.6f+AlongArm*3.f+Life*(Wisp?4.f:2.f);
            const float Rise=(Wisp?24.f:15.f)+Seed*(Wisp?15.f:13.f);
            const float Sway=Age*(.8f+Seed*.5f)+Phase;
            // A continuously replenished forearm/hand cloud, like the hammer's
            // suspended hit flecks. Small soft bodies replace fast broken streaks.
            const FVector Birth=FMath::Lerp(LowerPos,Center,.32f+.68f*AlongArm);
            const FVector Drift=A*(FMath::Sin(Sway)*1.6f)+B*(FMath::Cos(Sway*.83f)*1.2f);
            const FVector Position=Birth+Radial*Radius+Up*(Life*Rise)+Drift;
            const FVector Lift=Up+A*(FMath::Cos(Sway)*.10f);
            const FVector Long=(Lift-Forward*FVector::DotProduct(Lift,Forward)).GetSafeNormal(UE_SMALL_NUMBER,ViewUp);
            const FVector Wide=FVector::CrossProduct(Long,Forward).GetSafeNormal();
            const FQuat Rotation=FRotationMatrix::MakeFromXY(Wide,Long).ToQuat();
            const float Envelope=FMath::SmoothStep(0.f,.10f,Life)*(1.f-FMath::SmoothStep(.65f,1.f,Life));
            const float Width=Wisp?2.1f+Seed*1.2f:1.1f+Seed*.85f;
            const float Length=Width*(Wisp?1.75f:(I%6==0?1.8f:1.12f));
            ParticleTransforms[Side][I]=FTransform(Rotation,Position,FVector(Width/100.f,Length/100.f,1.f));
            FX->SetCustomDataValue(I,0,Strength*Envelope*(Wisp?.34f:.92f),false);
            FX->SetCustomDataValue(I,1,Life,false);
            FX->SetCustomDataValue(I,2,Wisp?1.f:0.f,false);
        }
        FX->BatchUpdateInstancesTransforms(0,ParticleTransforms[Side],true,true,true);
    }
}
void UKukriBerserkerVFXComponent::RefreshWeaponOverlays()
{
    if(!bActive||!WeaponMID){RestoreWeaponOverlays();return;}
    const auto* Main=GetOwner()->FindComponentByClass<UKukriWeaponComponent>();
    const auto* Off=GetOwner()->FindComponentByClass<UOffhandKukriComponent>();
    UStaticMeshComponent* Roots[]={Main&&Main->IsEquipped()?Main->WeaponMesh():nullptr,
        Main&&Main->IsDual()?Main->WeaponMesh(true):Off&&Off->IsEquipped()?Off->WeaponMesh():nullptr};
    TArray<UStaticMeshComponent*,TInlineAllocator<16>> Targets;
    if(UsesWorldBody())
    {
        HandMask=0;
        if(const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>())
        {
            TArray<FFPSWeatherWeaponMesh> Parts;Body->GetWeatherWeaponMeshes(Parts,true);
            for(const auto& Part:Parts)
            {
                auto* Mesh=Cast<UStaticMeshComponent>(Part.Mesh);
                if(!Mesh||!WeaponInstances.Contains(Part.Instance)||!Mesh->ComponentHasTag(TEXT("SwordSlot=blade_1"))||
                    !Mesh->IsVisible()||Mesh->bHiddenInGame)continue;
                // Equipment and rune snapshots may arrive on different frames.
                // A former activation cannot illuminate a replacement rune.
                bool RuneSurface=false;
                const TCHAR* Prefix=bFrostRaven?TEXT("M_FrostRaven_"):TEXT("M_Berserker_");
                for(int32 I=0;I<Mesh->GetNumMaterials();++I)
                    if(auto* M=Mesh->GetMaterial(I);M&&M->GetBaseMaterial()&&M->GetBaseMaterial()->GetName().StartsWith(Prefix))RuneSurface=true;
                if(!RuneSurface)continue;
                HandMask|=1<<Part.Hand;Targets.AddUnique(Mesh);
            }
            // Berserker illuminates the complete matching knife, while frost
            // stays on its blade. Never spill either overlay onto the other hand.
            if(!bFrostRaven)for(const auto& Part:Parts)
                if((HandMask&(1<<Part.Hand))&&WeaponInstances.Contains(Part.Instance))
                    if(auto* Mesh=Cast<UStaticMeshComponent>(Part.Mesh);Mesh&&Mesh->IsVisible()&&!Mesh->bHiddenInGame)
                        Targets.AddUnique(Mesh);
        }
    }
    else for(int32 Side=0;Side<2;++Side)
    {
        auto* Root=Roots[Side];
        if(!(HandMask&(1<<Side))||!IsValid(Root))continue;
        if(!bFrostRaven||Root->ComponentHasTag(TEXT("SwordSlot=blade_1")))Targets.AddUnique(Root);
        TArray<USceneComponent*> Children;Root->GetChildrenComponents(true,Children);
        for(auto* Child:Children)
            if(auto* Part=Cast<UStaticMeshComponent>(Child);Part&&Part->ComponentHasTag(TEXT("FrostSwordModule")))
                if(!bFrostRaven||Part->ComponentHasTag(TEXT("SwordSlot=blade_1")))Targets.AddUnique(Part);
    }
    for(auto It=WeaponOverlays.CreateIterator();It;++It)
    {
        auto* Part=It.Key().Get();
        if(IsValid(Part)&&Targets.Contains(Part))continue;
        if(IsValid(Part)&&Part->GetOverlayMaterial()==WeaponMID)Part->SetOverlayMaterial(It.Value());
        It.RemoveCurrent();
    }
    for(auto* Part:Targets)
    {
        if(WeaponOverlays.Contains(Part))continue;
        WeaponOverlays.Add(Part,Part->GetOverlayMaterial());
        Part->SetOverlayMaterial(WeaponMID);
    }
}
void UKukriBerserkerVFXComponent::RestoreWeaponOverlays()
{
    for(const auto& Binding:WeaponOverlays)
        if(auto* Part=Binding.Key.Get();IsValid(Part)&&Part->GetOverlayMaterial()==WeaponMID)
            Part->SetOverlayMaterial(Binding.Value);
    WeaponOverlays.Reset();
}
void UKukriBerserkerVFXComponent::Hide()
{
    RestoreWeaponOverlays();
    if(Overlay)Overlay->Show(false);
    for(const auto& FX:Emitters)if(FX)FX->SetVisibility(false);
}
void UKukriBerserkerVFXComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    auto* Pawn=Cast<APawn>(GetOwner());auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!bEquipped||!Pawn||(Health&&Health->IsDead()))
    {Strength=0.f;Hide();SetComponentTickEnabled(false);return;}
    Age+=Delta;EntryAge+=Delta;
    Strength=FMath::FInterpConstantTo(Strength,bActive?1.f:0.f,Delta,bActive?5.f:2.5f);
    if(Strength<=.001f){Hide();SetComponentTickEnabled(false);return;}
    if((!bFrostRaven&&Pawn->IsLocallyControlled()&&!Overlay)||Emitters.Num()!=2)CreatePresentation();
    const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    const bool WorldView=UsesWorldBody();
    const bool ViewVisible=WorldView||(PC&&PC->GetViewTarget()==Pawn&&(!PC->MyHUD||PC->MyHUD->bShowHUD)&&(!Body||!Body->IsThirdPersonViewEnabled()));
    if(!ViewVisible){Hide();return;}
    if(WeaponMID)
    {
        WeaponMID->SetScalarParameterValue(TEXT("Strength"),bActive?Strength:0.f);
        WeaponMID->SetScalarParameterValue(TEXT("Age"),Age);
        WeaponMID->SetScalarParameterValue(TEXT("EntryBurst"),FMath::Exp(-EntryAge*5.f));
    }
    if(Overlay&&EdgeMID)
    {
        EdgeMID->SetScalarParameterValue(TEXT("Strength"),Strength);
        EdgeMID->SetScalarParameterValue(TEXT("Age"),Age);
        EdgeMID->SetScalarParameterValue(TEXT("EntryBurst"),FMath::Exp(-EntryAge*5.f));
        Overlay->Show(true);
    }
    ResolveAge-=Delta;if(ResolveAge<=0.f){ResolveHands();RefreshWeaponOverlays();ResolveAge=.15f;}
    if(WorldView)PC=GetWorld()->GetFirstPlayerController();
    if(PC){FVector Eye;FRotator Rotation;PC->GetPlayerViewPoint(Eye,Rotation);UpdateHands(FTransform(Rotation,Eye));}
}
void UKukriBerserkerVFXComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(Load)Load->CancelHandle();Load.Reset();Hide();
    if(Overlay)
    {
        if(auto* Viewport=GetWorld()?GetWorld()->GetGameViewport():nullptr;Viewport&&HudPlayer.IsValid())
            Viewport->RemoveViewportWidgetForPlayer(HudPlayer.Get(),Overlay.ToSharedRef());
        Overlay->SetMaterial(nullptr);Overlay.Reset();
    }
    for(const auto& FX:Emitters)if(FX)FX->DestroyComponent();Emitters.Reset();
    Super::EndPlay(Reason);
}
