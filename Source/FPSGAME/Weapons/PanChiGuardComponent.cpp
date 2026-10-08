#include "PanChiGuardComponent.h"
#include "RuneSwordComponent.h"
#include "RuneSwordGuardTuning.h"
#include "MeleeWeaponStats.h"
#include "../Skills/SwordUppercutTuning.h"
#include "FPSMeleeLightningComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/CorrosivePusDamage.h"
#include "../Monsters/PoisonMaggotMonster.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Movement/PlayerGuardBreakComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/GameStateBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Net/UnrealNetwork.h"
#include "TimerManager.h"

UPanChiGuardComponent::UPanChiGuardComponent()
{
    SetIsReplicatedByDefault(true);PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;PrimaryComponentTick.TickInterval=.04f;
}
double UPanChiGuardComponent::Clock() const
{const auto* W=GetWorld();const auto* G=W?W->GetGameState():nullptr;return G?G->GetServerWorldTimeSeconds():W?W->GetTimeSeconds():0.;}
void UPanChiGuardComponent::Configure(const UColdSteelStatusModel* InProfile)
{
    Profile=InProfile;
    const auto* I=InProfile&&!InProfile->ActiveProductionTool()?InProfile->Equipped():nullptr;
    const auto* G=InProfile?InProfile->GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    FString Next,Data;FMeleeModifiers NextModifiers;
    if(I&&G&&I->Definition==TEXT("ue_xuanchi_zhenyue")&&G->Installed(*I).FindRef(TEXT("guard"))==TEXT("panchi_zhanyue"))
        if(const auto* O=G->Option(I->Definition,TEXT("guard"),TEXT("panchi_zhanyue")))
        {Next=I->InstanceId;Data=I->Data;NextModifiers=O->Melee;}
    if(Next!=EquippedInstance)ClearCharges();
    EquippedInstance=MoveTemp(Next);EquippedData=MoveTemp(Data);Modifiers=NextModifiers;
    if(!EquippedInstance.IsEmpty())RequestVisuals();
    SetComponentTickEnabled(!EquippedInstance.IsEmpty()||Clock()-ReleaseAt<ReleaseVisualSeconds);
    RefreshGuardVisual();
}
bool UPanChiGuardComponent::IsActive() const
{
    if(!Profile.IsValid()||EquippedInstance.IsEmpty()||Profile->ActiveProductionTool())return false;
    const auto* I=Profile->Equipped();const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    return I&&I->InstanceId==EquippedInstance&&I->Data==EquippedData&&H&&!H->IsDead();
}
float UPanChiGuardComponent::Remaining() const {return IsActive()?FMath::Max(0.,ChargesEnd-Clock()):0.f;}
int32 UPanChiGuardComponent::Charges() const {return Remaining()>0.f?StoredCharges:0;}
float UPanChiGuardComponent::CooldownRemaining() const {return IsActive()?FMath::Max(0.,ReadyAt-Clock()):0.f;}
void UPanChiGuardComponent::ConfirmGuard(bool bPerfect)
{
    if(!GetOwner()->HasAuthority()||!IsActive()||Modifiers.PanChiSeconds<=0.)return;
    StoredCharges=FMath::Min(FMath::RoundToInt(Modifiers.PanChiMaxStacks),Charges()+(bPerfect?2:1));
    ChargesEnd=Clock()+Modifiers.PanChiSeconds;Publish();
}
void UPanChiGuardComponent::ClearCharges()
{
    // ReadyAt deliberately survives equipment switches and death on this pawn.
    if(GetOwner()->HasAuthority()){StoredCharges=0;ChargesEnd=0.;}
    ConsumedAttackSerial=0;ConsumedToughness=1.f;bRemoteGuard=false;Publish();
}
void UPanChiGuardComponent::Publish()
{if(GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();RefreshGuardVisual();UStatusEffectsComponent::Notify(GetOwner());}
void UPanChiGuardComponent::OnRep_Charges()
{RefreshGuardVisual();UStatusEffectsComponent::Notify(GetOwner());}
void UPanChiGuardComponent::StampBladeAttack(AActor* Owner,FColdSteelSkillShot& Shot)
{
    if(auto* G=Owner?Owner->FindComponentByClass<UPanChiGuardComponent>():nullptr;G&&G->IsActive())
    {if(++G->AttackSerial==0)++G->AttackSerial;Shot.GuardAttackSerial=G->AttackSerial;Shot.GuardSourceInstance=G->EquippedInstance;}
}
bool UPanChiGuardComponent::CanEmpowerUppercut() const
{return IsActive()&&Charges()>0&&CooldownRemaining()<=0.f;}
bool UPanChiGuardComponent::IsUppercutHit(const FColdSteelSkillShot& Shot) const
{
    return GetOwner()->HasAuthority()&&IsActive()&&Shot.bMelee&&!Shot.bRicochet&&Shot.AttackMeta==SwordUppercut::AttackMeta
        &&Shot.GuardAttackSerial!=0&&Shot.GuardSourceInstance==EquippedInstance&&Shot.ItemDefinition==TEXT("ue_xuanchi_zhenyue");
}
float UPanChiGuardComponent::UppercutToughnessMultiplier(const FColdSteelSkillShot& Shot) const
{
    if(!IsUppercutHit(Shot))return 1.f;
    // Every target of the same cleave keeps its multiplier, but no second release.
    if(Shot.GuardAttackSerial==ConsumedAttackSerial)return ConsumedToughness;
    return CooldownRemaining()<=0.f?1.f+Charges()*float(Modifiers.PanChiToughnessPerStack):1.f;
}
void UPanChiGuardComponent::SetGuardIntent(bool bRaised)
{
    if(bRaised&&!IsActive())return;
    if(bRemoteGuard==bRaised)return;
    bRemoteGuard=bRaised;if(bRaised)RemoteGuardStarted=Clock();
    if(const auto* Pawn=Cast<APawn>(GetOwner());Pawn&&Pawn->IsLocallyControlled()&&!Pawn->HasAuthority())ServerSetGuardIntent(bRaised);
}
void UPanChiGuardComponent::ServerSetGuardIntent_Implementation(bool bRaised)
{
    if(!bRaised){bRemoteGuard=false;return;}
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!IsActive()||!Pawn||Profile->Stamina()<=0.f||Pawn->IsDodging()||Pawn->IsSliding()||Pawn->IsCastBlockingLeftHandAction())return;
    if(!bRemoteGuard)RemoteGuardStarted=Clock();bRemoteGuard=true;
}
float UPanChiGuardComponent::ResolveRemoteGuard(float Damage,const UDamageType* Type,AController* Instigator,AActor* Causer)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||!Pawn->HasAuthority()||Pawn->IsLocallyControlled()||!IsActive()||!bRemoteGuard||Damage<=0.f)return Damage;
    if(Pawn->IsDodging()||Pawn->IsSliding()||Pawn->IsCastBlockingLeftHandAction()){bRemoteGuard=false;return Damage;}
    if(Type&&(Type->IsA<UMaggotPoisonDamage>()||Type->IsA<UCorrosivePusDamage>()))return Damage;
    auto* Model=const_cast<UColdSteelStatusModel*>(Profile.Get());
    const auto M=ColdSteelMelee::EquippedModifiers(Model);
    AActor* Source=Instigator?Instigator->GetPawn():Causer;
    if(Causer&&(!Source||Source==Causer)){if(Causer->GetInstigator())Source=Causer->GetInstigator();else if(Causer->GetOwner())Source=Causer->GetOwner();}
    if(IsValid(Source)&&Source!=Pawn&&Clock()-RemoteGuardStarted<=RuneSwordGuardTuning::ParrySeconds*M.ParryWindow)
    {
        const FVector Toward=(Source->GetActorLocation()-Pawn->GetActorLocation()).GetSafeNormal2D();
        const FVector Forward=FRotationMatrix(FRotator(0,Pawn->GetControlRotation().Yaw,0)).GetUnitAxis(EAxis::X);
        if(!Toward.IsNearlyZero()&&FVector::DotProduct(Toward,Forward)>=FMath::Cos(FMath::DegreesToRadians(RuneSwordGuardTuning::ParryHalfAngleDegrees)))
        {
            ConfirmGuard(true);
            if(Type&&Type->IsA<UEnemyMeleeDamage>()&&!Source->ActorHasTag(TEXT("ParryImmune")))
                if(auto* Combat=Source->FindComponentByClass<UMonsterCombatComponent>())Combat->ReceiveParry(Pawn,RuneSwordGuardTuning::ParryStunSeconds,RuneSwordGuardTuning::ParryKnockbackCM);
            return 0.f;
        }
    }
    const float Cost=ColdSteelMelee::BlockStamina(M);const bool Broken=Model->Stamina()<Cost;
    Model->SpendStamina(FMath::Min(Model->Stamina(),Cost));
    if(Broken)
    {
        bRemoteGuard=false;
        auto* Stun=Pawn->FindComponentByClass<UPlayerGuardBreakComponent>();
        if(!Stun){Stun=NewObject<UPlayerGuardBreakComponent>(Pawn);Pawn->AddInstanceComponent(Stun);Stun->RegisterComponent();}
        Stun->Apply(RuneSwordGuardTuning::BreakStunSeconds);
    }
    else ConfirmGuard(false);
    return Damage*(1.-FMath::Clamp((1.-RuneSwordGuardTuning::DamageTakenRatio)*M.BlockReduction,0.,1.));
}
void UPanChiGuardComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(GetOwner()->HasAuthority())
    {
        if(!IsActive()&&(StoredCharges>0||bRemoteGuard))ClearCharges();
        else if(StoredCharges>0&&Remaining()<=0.f){StoredCharges=0;ChargesEnd=0.;Publish();}
        if(ReadyAt>0.&&Clock()>=ReadyAt){ReadyAt=0.;Publish();}
    }
    TickDragonFlight(Delta);
    RefreshGuardVisual();
    TickReleaseVisual();
    if(!IsActive()&&Clock()-ReleaseAt>=ReleaseVisualSeconds)SetComponentTickEnabled(false);
}
void UPanChiGuardComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    ClearCharges();
    if(VisualLoad)VisualLoad->CancelHandle();VisualLoad.Reset();
    if(GuardMesh.IsValid()&&GuardMesh->GetOverlayMaterial()==GuardMID)GuardMesh->SetOverlayMaterial(nullptr);
    if(SpiritMesh)SpiritMesh->DestroyComponent();
    if(MoteMesh)MoteMesh->DestroyComponent();
    if(CircleMesh)CircleMesh->DestroyComponent();
    Super::EndPlay(Reason);
}
void UPanChiGuardComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(UPanChiGuardComponent,StoredCharges,COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UPanChiGuardComponent,ChargesEnd,COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UPanChiGuardComponent,ReadyAt,COND_OwnerOnly);
}
