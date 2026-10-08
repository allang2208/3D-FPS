#include "JingangRuneComponent.h"
#include "FrostSwordRunes.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/HUD.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Net/UnrealNetwork.h"
#include "Rendering/DrawElements.h"
#include "Widgets/SLeafWidget.h"

namespace JingangHud
{
const FSoftObjectPath MaterialPath(TEXT("/Game/Weapons/XuanChiZhenYue20261004/JingangRune20261006/Materials/M_JingangSutraHud.M_JingangSutraHud"));
// Azure V10's full animated quad ends at x=.287H (including its .006H sway).
// The sutra starts beyond .3185H even during its sway, leaving a .0315H gutter.
constexpr float Left=.32f,Top=.20f,Width=.155f,Height=.31f;
}

class SJingangSutraHud final : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SJingangSutraHud){} SLATE_END_ARGS()
    void Construct(const FArguments&)
    {SetVisibility(EVisibility::HitTestInvisible);SetCanTick(false);ForceVolatile(true);Brush.DrawAs=ESlateBrushDrawType::Image;}
    void SetMaterial(UMaterialInstanceDynamic* In){Brush.SetResourceObject(In);}
    void SetFrame(bool Shown,float InAlpha,float InAge){bShown=Shown;Alpha=InAlpha;Age=InAge;}
    virtual FVector2D ComputeDesiredSize(float) const override{return FVector2D::ZeroVector;}
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry& G,const FSlateRect&,FSlateWindowElementList& Out,
        int32 Layer,const FWidgetStyle&,bool) const override
    {
        if(!bShown||Alpha<=.001f||!Brush.GetResourceObject())return Layer;
        const float H=G.GetLocalSize().Y;
        const FVector2f Size(H*JingangHud::Width,H*JingangHud::Height);
        const FVector2f Pos(H*(JingangHud::Left+.0015f*FMath::Sin(Age*.71f)),H*(JingangHud::Top+.003f*FMath::Sin(Age*1.17f)));
        FSlateDrawElement::MakeBox(Out,Layer,G.ToPaintGeometry(Size,FSlateLayoutTransform(Pos)),&Brush,
            ESlateDrawEffect::NoGamma|ESlateDrawEffect::NoPixelSnapping,FLinearColor(1,1,1,Alpha));
        return Layer;
    }
private:
    FSlateBrush Brush;bool bShown=false;float Alpha=0,Age=0;
};

UJingangRuneComponent::UJingangRuneComponent()
{
    SetIsReplicatedByDefault(true);PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
void UJingangRuneComponent::Configure(const UColdSteelStatusModel* InProfile)
{
    Profile=InProfile;
    const auto* Item=InProfile&&!InProfile->ActiveProductionTool()?InProfile->Equipped():nullptr;
    const auto* G=InProfile?InProfile->GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    FString Next,Data;FMeleeModifiers NextModifiers;
    if(Item&&G&&Item->Definition==ColdSteelFrostRunes::XuanChi
        &&G->Installed(*Item).FindRef(TEXT("blade_2"))==ColdSteelFrostRunes::Jingang)
        if(const auto* O=G->Option(Item->Definition,TEXT("blade_2"),ColdSteelFrostRunes::Jingang))
        {Next=Item->InstanceId;Data=Item->Data;NextModifiers=O->Melee;}
    if(Next!=EquippedInstance){Clear();EntryAge=0.f;}
    EquippedInstance=MoveTemp(Next);EquippedData=MoveTemp(Data);Modifiers=NextModifiers;
    SetComponentTickEnabled(!EquippedInstance.IsEmpty());
    if(EquippedInstance.IsEmpty()){if(HudWidget)HudWidget->SetFrame(false,0.f,Age);return;}
    ObserveHealth();
    if(const auto* Pawn=Cast<APawn>(GetOwner());Pawn&&Pawn->IsLocallyControlled())RequestAssets();
}
bool UJingangRuneComponent::Equipped() const
{
    if(!Profile.IsValid()||EquippedInstance.IsEmpty()||Profile->ActiveProductionTool())return false;
    const auto* Item=Profile->Equipped();
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    return Item&&Item->InstanceId==EquippedInstance&&Item->Data==EquippedData&&Health&&!Health->IsDead();
}
EJingangState UJingangRuneComponent::State() const
{
    if(!Equipped())return EJingangState::None;
    const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!H||H->MaxHealth<=0.f)return EJingangState::None;
    // float(0.3) * 100 rounds above 30, wrongly granting low-health bonuses at exactly 30 HP.
    const double HealthRatio=double(H->Health)/double(H->MaxHealth);
    if(HealthRatio>=Modifiers.JingangHighThreshold)return EJingangState::High;
    return HealthRatio<Modifiers.JingangLowThreshold?EJingangState::Low:EJingangState::Middle;
}
float UJingangRuneComponent::DefenseMultiplier() const
{const auto S=State();return S==EJingangState::None?1.f:1.f+Modifiers.JingangBonus*(S==EJingangState::Low?2.f:1.f);}
float UJingangRuneComponent::DamageMultiplier() const
{const auto S=State();return 1.f+Modifiers.JingangBonus*(S==EJingangState::Low?2.f:S==EJingangState::High?1.f:0.f);}
float UJingangRuneComponent::AttackSpeedMultiplier() const
{const auto S=State();return 1.f+Modifiers.JingangBonus*(S==EJingangState::Low?2.f:S==EJingangState::Middle?1.f:0.f);}
float UJingangRuneComponent::CooldownMultiplier() const
{const auto S=State();return FMath::Max(.05f,1.f-float(Modifiers.JingangBonus)*(S==EJingangState::Low?2.f:S==EJingangState::Middle?1.f:0.f));}
double UJingangRuneComponent::Clock() const
{const auto* W=GetWorld();const auto* S=W?W->GetGameState():nullptr;return S?S->GetServerWorldTimeSeconds():W?W->GetTimeSeconds():0.;}
float UJingangRuneComponent::LeechRemaining() const
{return Equipped()?FMath::Max(0.,LeechEndsAt-Clock()):0.f;}
void UJingangRuneComponent::ObserveHealth()
{
    const auto Next=State();
    if(Next==EJingangState::None){if(LastState!=Next||LeechEndsAt>0.)Clear();return;}
    if(Next==LastState)return;
    if(GetOwner()->HasAuthority()&&Next==EJingangState::Low)
    {LeechEndsAt=Clock()+Modifiers.JingangLeechSeconds;GetOwner()->ForceNetUpdate();}
    LastState=Next;UStatusEffectsComponent::Notify(GetOwner());
}
void UJingangRuneComponent::ConfirmAttack(AActor* Target,float AppliedDamage)
{
    if(!GetOwner()->HasAuthority()||!Equipped()||AppliedDamage<=0.f||!IsValid(Target)||Target==GetOwner()
        ||Target->ActorHasTag(TEXT("Friendly"))||Target->ActorHasTag(TEXT("Companion"))
        ||!Target->FindComponentByClass<UMonsterCombatComponent>())return;
    ObserveHealth();
    if(State()==EJingangState::Low){LeechEndsAt=Clock()+Modifiers.JingangLeechSeconds;GetOwner()->ForceNetUpdate();}
    if(LeechRemaining()<=0.f)return;
    if(auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&!H->IsDead())
    {H->Health=FMath::Min(H->MaxHealth,H->Health+AppliedDamage*float(Modifiers.JingangLeechRatio));GetOwner()->ForceNetUpdate();}
    ObserveHealth();UStatusEffectsComponent::Notify(GetOwner());
}
void UJingangRuneComponent::Clear()
{
    if(GetOwner()->HasAuthority()){LeechEndsAt=0.;GetOwner()->ForceNetUpdate();}
    LastState=EJingangState::None;bHadLeech=false;DisplayState=PreviousDisplayState=-1;
    if(HudWidget)HudWidget->SetFrame(false,0.f,Age);
    UStatusEffectsComponent::Notify(GetOwner());
}
const UJingangRuneComponent* UJingangRuneComponent::From(const UColdSteelStatusModel* Model)
{const auto* Pawn=Model?Model->RuntimePawn():nullptr;return Pawn?Pawn->FindComponentByClass<UJingangRuneComponent>():nullptr;}
float UJingangRuneComponent::OutgoingMultiplier(const AActor* Source)
{const auto* Rune=Source?Source->FindComponentByClass<UJingangRuneComponent>():nullptr;return Rune?Rune->DamageMultiplier():1.f;}
void UJingangRuneComponent::OnRep_Leech(){UStatusEffectsComponent::Notify(GetOwner());}
void UJingangRuneComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME_CONDITION(UJingangRuneComponent,LeechEndsAt,COND_OwnerOnly);}
void UJingangRuneComponent::RequestAssets()
{
    if(bRequested)return;bRequested=true;TWeakObjectPtr<UJingangRuneComponent> Weak(this);
    AssetLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(JingangHud::MaterialPath,FStreamableDelegate::CreateLambda([Weak]()
    {if(auto* Self=Weak.Get()){Self->HudMaterial=Cast<UMaterialInterface>(JingangHud::MaterialPath.ResolveObject());if(Self->Equipped())Self->CreateDisplay();}}));
}
void UJingangRuneComponent::CreateDisplay()
{
    if(HudWidget||!HudMaterial)return;
    const auto* Pawn=Cast<APawn>(GetOwner());auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    auto* Local=PC?PC->GetLocalPlayer():nullptr;auto* Viewport=GetWorld()?GetWorld()->GetGameViewport():nullptr;
    if(!Local||!Viewport)return;
    HudMID=UMaterialInstanceDynamic::Create(HudMaterial,this);SAssignNew(HudWidget,SJingangSutraHud);HudWidget->SetMaterial(HudMID);
    Viewport->AddViewportWidgetForPlayer(Local,HudWidget.ToSharedRef(),16);HudPlayer=Local;
}
void UJingangRuneComponent::RemoveDisplay()
{
    if(HudWidget){if(auto* V=GetWorld()?GetWorld()->GetGameViewport():nullptr;V&&HudPlayer.IsValid())V->RemoveViewportWidgetForPlayer(HudPlayer.Get(),HudWidget.ToSharedRef());HudWidget->SetMaterial(nullptr);}
    HudWidget.Reset();HudPlayer.Reset();HudMID=nullptr;
}
void UJingangRuneComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);ObserveHealth();
    const bool HasLeech=LeechRemaining()>0.f;if(HasLeech!=bHadLeech){bHadLeech=HasLeech;UStatusEffectsComponent::Notify(GetOwner());}
    const auto S=State();if(S==EJingangState::None){if(HudWidget)HudWidget->SetFrame(false,0.f,Age);return;}
    const auto* Pawn=Cast<APawn>(GetOwner());const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    if(!Pawn||!PC||!Pawn->IsLocallyControlled())return;
    if(!HudWidget)CreateDisplay();if(!HudWidget||!HudMID)return;
    const bool Shown=PC->GetViewTarget()==Pawn&&(!PC->MyHUD||PC->MyHUD->bShowHUD);
    const int32 Next=int32(S)-1;
    if(Next!=DisplayState){PreviousDisplayState=DisplayState<0?Next:DisplayState;DisplayState=Next;TransitionAge=0.f;}
    Age=FMath::Fmod(Age+Delta,3600.f);EntryAge+=Delta;TransitionAge+=Delta;
    HudMID->SetScalarParameterValue(TEXT("State"),DisplayState);HudMID->SetScalarParameterValue(TEXT("PreviousState"),PreviousDisplayState);
    HudMID->SetScalarParameterValue(TEXT("Blend"),FMath::SmoothStep(0.f,.45f,TransitionAge));
    HudMID->SetScalarParameterValue(TEXT("Age"),Age);HudMID->SetScalarParameterValue(TEXT("Leech"),HasLeech?1.f:0.f);
    HudWidget->SetFrame(Shown,FMath::SmoothStep(0.f,.35f,EntryAge),Age);
}
void UJingangRuneComponent::EndPlay(const EEndPlayReason::Type Reason)
{Clear();if(AssetLoad)AssetLoad->CancelHandle();AssetLoad.Reset();RemoveDisplay();Super::EndPlay(Reason);}
