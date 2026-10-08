#include "ZhenmoRuneComponent.h"
#include "FrostSwordRunes.h"
#include "FPSMeleeLightningComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameStateBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Net/UnrealNetwork.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "TimerManager.h"

namespace
{
const FSoftObjectPath FieldPath(TEXT("/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/SoftGroundV3/M_ZhenmoSoftGround.M_ZhenmoSoftGround"));
const FSoftObjectPath MotePath(TEXT("/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Particles/NS_ZhenmoRisingGold.NS_ZhenmoRisingGold"));
}

UZhenmoRuneComponent::UZhenmoRuneComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
void UZhenmoRuneComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
}
void UZhenmoRuneComponent::Configure(const UColdSteelStatusModel* InProfile)
{
    Profile=InProfile;
    const auto* Item=InProfile&&!InProfile->ActiveProductionTool()?InProfile->Equipped():nullptr;
    const auto* G=InProfile?InProfile->GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    FString Next;FMeleeModifiers NextModifiers;
    if(Item&&G&&Item->Definition==ColdSteelFrostRunes::XuanChi
        &&G->Installed(*Item).FindRef(TEXT("blade_2"))==ColdSteelFrostRunes::Zhenmo)
        if(const auto* Option=G->Option(Item->Definition,TEXT("blade_2"),ColdSteelFrostRunes::Zhenmo))
        {Next=Item->InstanceId;NextModifiers=Option->Melee;}
    const bool Changed=Next!=EquippedInstance;
    EquippedInstance=MoveTemp(Next);Modifiers=NextModifiers;
    if(GetOwner()->HasAuthority())
    {
        if(Changed)Clear();
        if(!EquippedInstance.IsEmpty())RadiusCM=Modifiers.ZhenmoRadiusCM;
    }
    if(!EquippedInstance.IsEmpty())LoadVisual();
}
bool UZhenmoRuneComponent::Equipped() const
{
    if(!Profile.IsValid()||EquippedInstance.IsEmpty()||Profile->ActiveProductionTool())return false;
    const auto* Item=Profile->Equipped();
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    return Item&&Item->InstanceId==EquippedInstance&&Item->Definition==ColdSteelFrostRunes::XuanChi
        &&(!Health||!Health->IsDead());
}
double UZhenmoRuneComponent::Clock() const
{
    const auto* W=GetWorld();const auto* State=W?W->GetGameState():nullptr;
    return State?State->GetServerWorldTimeSeconds():W?W->GetTimeSeconds():0.;
}
float UZhenmoRuneComponent::Remaining() const
{
    if(GetOwner()->HasAuthority()&&!Equipped())return 0.f;
    return FMath::Max(0.f,float(EndsAt-Clock()));
}
bool UZhenmoRuneComponent::Affects(const AActor* Target) const
{
    // Exact radius at consumption; the periodic broadphase only discovers new targets.
    if(!Target||Remaining()<=0.f)return false;
    return FVector::DistSquared(Target->GetActorLocation(),GetOwner()->GetActorLocation())<=FMath::Square(RadiusCM);
}
void UZhenmoRuneComponent::ConfirmCritical(const FString& SourceInstance)
{
    if(!GetOwner()->HasAuthority()||SourceInstance!=EquippedInstance||!Equipped()||Modifiers.ZhenmoSeconds<=0.)return;
    EndsAt=Clock()+Modifiers.ZhenmoSeconds;GetOwner()->ForceNetUpdate();
    UStatusEffectsComponent::Notify(GetOwner());
    if(!GetWorld()->GetTimerManager().IsTimerActive(PulseTimer))
        GetWorld()->GetTimerManager().SetTimer(PulseTimer,this,&ThisClass::Pulse,.1f,true);
    Pulse();OnRep_Field();
}
void UZhenmoRuneComponent::Pulse()
{
    if(!GetOwner()->HasAuthority())return;
    if(Remaining()<=0.f){Clear();return;}
    TArray<FOverlapResult> Hits;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ZhenmoField),false,GetOwner());
    GetWorld()->OverlapMultiByObjectType(Hits,GetOwner()->GetActorLocation(),FQuat::Identity,
        FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeSphere(RadiusCM),Query);
    TSet<TWeakObjectPtr<AActor>> Next;
    for(const auto& Hit:Hits)
        if(auto* Target=Hit.GetActor();UFPSMeleeLightningComponent::IsEnemy(Target,GetOwner())&&Affects(Target))
        {
            Next.Add(Target);
            if(!Targets.Contains(Target))UCombatStatusFormula::GetOrAdd(Target)->AddZhenmoSource(this);
        }
    for(const auto& Target:Targets)
        if(Target.IsValid()&&!Next.Contains(Target))
            if(auto* Status=Target->FindComponentByClass<UCombatStatusFormula>())Status->RemoveZhenmoSource(this);
    Targets=MoveTemp(Next);
}
void UZhenmoRuneComponent::Clear()
{
    EndsAt=0.;
    if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(PulseTimer);
    for(const auto& Target:Targets)if(Target.IsValid())
        if(auto* Status=Target->FindComponentByClass<UCombatStatusFormula>())Status->RemoveZhenmoSource(this);
    Targets.Reset();
    // Gameplay stops immediately; let the existing light and motes fade together.
    SetComponentTickEnabled(VisualBlend>0.f&&GetNetMode()!=NM_DedicatedServer);
    if(GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();
    UStatusEffectsComponent::Notify(GetOwner());
}
void UZhenmoRuneComponent::LoadVisual()
{
    if(GetNetMode()==NM_DedicatedServer||(FieldMaterial&&MoteSystem)||LoadHandle)return;
    // Equip-time presentation must not queue behind bulk weapon/body preloads.
    LoadHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{FieldPath,MotePath},
        FStreamableDelegate::CreateWeakLambda(this,[this]()
        {
            FieldMaterial=Cast<UMaterialInterface>(FieldPath.ResolveObject());
            MoteSystem=Cast<UNiagaraSystem>(MotePath.ResolveObject());RefreshVisual();
        }),FStreamableManager::AsyncLoadHighPriority);
}
void UZhenmoRuneComponent::OnRep_Field()
{
    const bool Active=Remaining()>0.f;
    SetComponentTickEnabled((Active||VisualBlend>0.f)&&GetNetMode()!=NM_DedicatedServer);
    if(Active)LoadVisual();RefreshVisual();UStatusEffectsComponent::Notify(GetOwner());
}
void UZhenmoRuneComponent::RefreshVisual(float Delta)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    // Begin the fade when the asynchronously loaded presentation can be drawn.
    if(!FieldMaterial)return;
    const float SecondsLeft=Remaining();
    const float TargetBlend=FMath::Clamp(SecondsLeft/1.2f,0.f,1.f);
    VisualBlend=FMath::FInterpConstantTo(VisualBlend,TargetBlend,Delta,1.f/.65f);
    if(SecondsLeft<=0.f&&VisualBlend<=0.f)
    {
        if(FieldSurface)FieldSurface->SetVisibility(false);
        if(FieldMotes&&bMotesActive){FieldMotes->DeactivateImmediate();FieldMotes->SetVisibility(false);}
        bMotesActive=false;bGroundReady=false;return;
    }
    if(FieldMaterial&&!FieldSurface)
    {
        FieldSurface=NewObject<UDynamicMeshComponent>(GetOwner(),TEXT("ZhenmoSoftGround"));
        FieldSurface->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        FieldSurface->SetGenerateOverlapEvents(false);FieldSurface->SetCanEverAffectNavigation(false);
        FieldSurface->SetCastShadow(false);FieldSurface->SetReceivesDecals(false);
        FieldSurface->bAffectDistanceFieldLighting=false;FieldSurface->SetVisibleInRayTracing(false);
        GetOwner()->AddInstanceComponent(FieldSurface);FieldSurface->RegisterComponent();
        FieldMID=UMaterialInstanceDynamic::Create(FieldMaterial,this);FieldSurface->SetMaterial(0,FieldMID);
    }
    FVector Feet=GetOwner()->GetActorLocation();
    if(const auto* Character=Cast<ACharacter>(GetOwner()))Feet.Z-=Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const float Opacity=FMath::SmoothStep(0.f,1.f,VisualBlend);
    if(FieldSurface)
    {
        RefreshGround(Feet);FieldSurface->SetVisibility(true);
        FieldMID->SetScalarParameterValue(TEXT("FieldOpacity"),Opacity);
        FieldMID->SetVectorParameterValue(TEXT("FieldCenter"),FLinearColor(Feet.X,Feet.Y,Feet.Z,0));
        FieldMID->SetScalarParameterValue(TEXT("FieldRadius"),RadiusCM);
    }
    if(MoteSystem&&!FieldMotes)
    {
        FieldMotes=NewObject<UNiagaraComponent>(GetOwner(),TEXT("ZhenmoRisingGold"));
        FieldMotes->SetAutoActivate(false);FieldMotes->SetAutoDestroy(false);
        FieldMotes->SetAsset(MoteSystem);FieldMotes->SetCastShadow(false);
        GetOwner()->AddInstanceComponent(FieldMotes);FieldMotes->RegisterComponent();
    }
    if(FieldMotes)
    {
        // Local-space motes translate with the circle without rotating with the wielder.
        FieldMotes->SetWorldLocationAndRotation(Feet,FRotator::ZeroRotator);
        FieldMotes->SetVariableFloat(TEXT("User.Radius"),RadiusCM);
        const FVector Slope=GroundMoteSlope();
        FieldMotes->SetVariableFloat(TEXT("User.SlopeX"),Slope.X);
        FieldMotes->SetVariableFloat(TEXT("User.SlopeY"),Slope.Y);
        FieldMotes->SetVariableFloat(TEXT("User.FieldOpacity"),Opacity);
        if(!bMotesActive)
        {
            FieldMotes->SetVisibility(true);FieldMotes->Activate(true);bMotesActive=true;
        }
    }
}
void UZhenmoRuneComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Fn)
{
    Super::TickComponent(Delta,Type,Fn);RefreshVisual(Delta);
    if(Remaining()<=0.f&&VisualBlend<=0.f)SetComponentTickEnabled(false);
}
void UZhenmoRuneComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    Clear();if(LoadHandle)LoadHandle->CancelHandle();LoadHandle.Reset();
    if(FieldSurface)FieldSurface->DestroyComponent();
    if(FieldMotes)FieldMotes->DestroyComponent();
    Super::EndPlay(Reason);
}
void UZhenmoRuneComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UZhenmoRuneComponent,EndsAt);DOREPLIFETIME(UZhenmoRuneComponent,RadiusCM);
}
