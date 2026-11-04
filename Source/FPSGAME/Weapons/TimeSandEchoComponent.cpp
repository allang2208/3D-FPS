#include "TimeSandEchoComponent.h"
#include "MeleeWeaponStats.h"
#include "FPSMeleeLightningComponent.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelDamageNumberSubsystem.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInterface.h"
#include "Sound/SoundBase.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

namespace TimeSandEcho
{
constexpr int32 VisualLimit=128;
constexpr float FadeSeconds=.35f;
const FSoftObjectPath PlanePath(TEXT("/Engine/BasicShapes/Plane.Plane"));
const FSoftObjectPath MaterialPath(TEXT("/Game/Weapons/AzureRunesword20260913/TimeSand20261101/M_TimeSandEcho.M_TimeSandEcho"));
// The same confirmation cue is held by the local character for ordinary melee.
const FSoftObjectPath HitConfirmPath(TEXT("/Game/Audio/PlayerHitFeedback20260914/S_Player_MonsterHit.S_Player_MonsterHit"));
}
UTimeSandEchoComponent::UTimeSandEchoComponent()
{
    SetIsReplicatedByDefault(true);PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
void UTimeSandEchoComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(UTimeSandEchoComponent,Marks);}
float UTimeSandEchoComponent::Clock() const
{
    if(const auto* GS=GetWorld()->GetGameState())return GS->GetServerWorldTimeSeconds();
    return GetWorld()->GetTimeSeconds();
}
void UTimeSandEchoComponent::Configure(const UColdSteelStatusModel* Profile)
{
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(Item&&Item->Definition==TEXT("ue_rune_sword")&&ColdSteelMelee::EquippedModifiers(Profile).TimeSandEchoRatio>0.)LoadVisual();
}
void UTimeSandEchoComponent::LoadVisual()
{
    if(GetNetMode()==NM_DedicatedServer||LoadHandle||(Plane&&Material))return;
    LoadHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(
        TArray<FSoftObjectPath>{TimeSandEcho::PlanePath,TimeSandEcho::MaterialPath,TimeSandEcho::HitConfirmPath},FStreamableDelegate::CreateWeakLambda(this,[this]()
    {
        Plane=Cast<UStaticMesh>(TimeSandEcho::PlanePath.ResolveObject());
        Material=Cast<UMaterialInterface>(TimeSandEcho::MaterialPath.ResolveObject());
        if(!Plane||!Material)return;
        Visual=NewObject<UInstancedStaticMeshComponent>(GetOwner());GetOwner()->AddInstanceComponent(Visual);
        Visual->SetMobility(EComponentMobility::Movable);Visual->SetStaticMesh(Plane);Visual->SetMaterial(0,Material);
        Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);Visual->SetGenerateOverlapEvents(false);
        Visual->SetCanEverAffectNavigation(false);Visual->SetCastShadow(false);Visual->SetReceivesDecals(false);
        Visual->bVisibleInRayTracing=false;Visual->SetNumCustomDataFloats(1);Visual->RegisterComponent();
        Present();
    }));
}
void UTimeSandEchoComponent::Queue(UColdSteelStatusModel* Profile,const FHitResult& Hit,const FColdSteelSkillShot& Shot,const FWeaponDamageParts& Damage,bool Critical)
{
    auto* Target=Hit.GetActor();auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!GetOwner()->HasAuthority()||!Profile||!Combat||Combat->IsDead()||Damage.Total()<=0||Shot.TimeSandEchoDelay<=0.f)return;
    const FString Group=Shot.ItemInstance+TEXT(":")+FString::FromInt(Shot.MasteryAttackSerial);
    if(Marks.ContainsByPredicate([&](const auto& M){return M.Target==Target&&M.Group==Group;}))return;
    auto& M=Marks.AddDefaulted_GetRef();M.Target=Target;M.Group=Group;M.Profile=Profile;
    M.StartedAt=Clock();M.TriggerAt=M.StartedAt+Shot.TimeSandEchoDelay;
    M.LocalPoint=Target->GetActorTransform().InverseTransformPosition(Hit.ImpactPoint);
    M.LocalNormal=Target->GetActorTransform().InverseTransformVectorNoScale(Hit.ImpactNormal).GetSafeNormal(SMALL_NUMBER,FVector::ForwardVector);
    M.Damage=Damage.Scaled(Shot.TimeSandEchoRatio);M.CooldownReward=Shot.TimeSandCooldownReward;M.bCritical=Critical;
    GetOwner()->ForceNetUpdate();OnRep_Marks();
}
void UTimeSandEchoComponent::Settle(FTimeSandEchoMark& M)
{
    M.bSettled=true;
    auto* Target=M.Target.Get();auto* Pawn=Cast<APawn>(GetOwner());auto* Profile=M.Profile.Get();
    auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!Pawn||!Profile||(Health&&Health->IsDead())||!Combat||Combat->IsDead()||!UFPSMeleeLightningComponent::IsEnemy(Target,Pawn))return;
    ColdSteelAuthority::FScope Authority(Profile);
    CombatFormulaRuntime::WeaponHit Receipt;Receipt.Target=Target;Receipt.Incoming=M.Damage;Receipt.bMelee=true;
    Receipt.bDamageAlreadyMitigated=true;
    TGuardValue<CombatFormulaRuntime::WeaponHit*> Scope(CombatFormulaRuntime::ActiveWeaponHit,&Receipt);
    const float Applied=Combat->ApplyHitWithReactionScale(0.f,[&]()
    {return Combat->ApplyHitWithToughnessScale(0.f,[&]()
        {return UGameplayStatics::ApplyDamage(Target,M.Damage.Total(),Pawn->GetController(),Pawn,UCombatDirectDamage::StaticClass());},0.f);});
    const bool Killed=Combat->IsDead();
    if(Applied<=0.f&&!Killed)return;
    if(!RewardedGroups.Contains(M.Group))
    {
        RewardedGroups.Add(M.Group);
        if(RewardedGroups.Num()>128)RewardedGroups.RemoveAt(0,RewardedGroups.Num()-128,EAllowShrinking::No);
        Profile->ReduceRuneSwordHitCooldowns(M.CooldownReward);
    }
    // Cosmetic feedback only: bypass weapon on-hit/lifesteal hooks entirely.
    ClientEchoDamage(Target,Applied,M.bCritical,Killed);
}
void UTimeSandEchoComponent::ClientEchoDamage_Implementation(AActor* Target,float Damage,bool Critical,bool Killed)
{
    auto* Pawn=Cast<APawn>(GetOwner());auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    if(!PC||!PC->IsLocalController()||(Damage<=0.f&&!Killed))return;
    // Use the authoritative echo receipt, never the predicted mark's timer.
    // Do not call NotifyConfirmedWeaponHit: it also triggers other rune hooks.
    if(auto* Sound=Cast<USoundBase>(TimeSandEcho::HitConfirmPath.ResolveObject()))
        UGameplayStatics::PlaySound2D(this,Sound,1.f,1.f);
    if(!Target)return; // A lethal target can disappear before the receipt arrives.
    if(auto* Numbers=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelDamageNumberSubsystem>())
        Numbers->PushDamageNumber(Target,PC,UColdSteelDamageNumberSubsystem::TargetTopAnchor(Target),Damage,Critical,Killed,Damage>=80.f,true);
}
void UTimeSandEchoComponent::OnRep_Marks()
{
    if(!Marks.IsEmpty())LoadVisual();
    SetComponentTickEnabled(!Marks.IsEmpty());Present();
}
void UTimeSandEchoComponent::Present()
{
    if(!Visual)return;
    const float Now=Clock();int32 Index=0;
    for(const auto& M:Marks)
    {
        if(Index>=TimeSandEcho::VisualLimit)break;
        if(!IsValid(M.Target)||Now>M.TriggerAt+TimeSandEcho::FadeSeconds)continue;
        const auto& Frame=M.Target->GetActorTransform();
        const FVector Normal=Frame.TransformVectorNoScale(M.LocalNormal).GetSafeNormal();
        const FVector Point=Frame.TransformPosition(M.LocalPoint)+Normal*2.f;
        const float Age=Now<M.TriggerAt?.6f*FMath::Clamp((Now-M.StartedAt)/FMath::Max(.01f,M.TriggerAt-M.StartedAt),0.f,1.f):
            .6f+.4f*FMath::Clamp((Now-M.TriggerAt)/TimeSandEcho::FadeSeconds,0.f,1.f);
        const FTransform Transform(FRotationMatrix::MakeFromZ(Normal).ToQuat(),Point,FVector(.65,.40,1.));
        if(Index>=Visual->GetInstanceCount())Visual->AddInstance(Transform,true);
        else Visual->UpdateInstanceTransform(Index,Transform,true,false,true);
        Visual->SetCustomDataValue(Index,0,Age,false);++Index;
    }
    while(Visual->GetInstanceCount()>Index)Visual->RemoveInstance(Visual->GetInstanceCount()-1);
    Visual->SetVisibility(Index>0);Visual->MarkRenderStateDirty();
}
void UTimeSandEchoComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);const float Now=Clock();
    if(GetOwner()->HasAuthority())
    {
        for(auto& M:Marks)if(!M.bSettled&&Now>=M.TriggerAt)Settle(M);
        const int32 Removed=Marks.RemoveAll([&](const auto& M){return !IsValid(M.Target)||Now>M.TriggerAt+TimeSandEcho::FadeSeconds;});
        if(Removed)GetOwner()->ForceNetUpdate();
    }
    Present();
    if(Marks.IsEmpty()||(!GetOwner()->HasAuthority()&&!Marks.ContainsByPredicate([&](const auto& M){return Now<=M.TriggerAt+TimeSandEcho::FadeSeconds;})))SetComponentTickEnabled(false);
}
void UTimeSandEchoComponent::EndPlay(EEndPlayReason::Type Reason)
{
    if(LoadHandle)LoadHandle->CancelHandle();LoadHandle.Reset();Marks.Reset();RewardedGroups.Reset();
    if(Visual){Visual->DestroyComponent();Visual=nullptr;}
    Super::EndPlay(Reason);
}
