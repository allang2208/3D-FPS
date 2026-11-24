#include "ColdSteelPlayerState.h"
#include "ColdSteelAuthorityContext.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/Bow/BowArrow.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowMountainEchoComponent.h"
#include "../Weapons/Bow/BowCadenceComponent.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/FPSElementalArrowComponent.h"
#include "../Skills/FPSIlluminationArrowComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Movement/PlayerKnockdownComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

bool AColdSteelPlayerState::IsBowDrawActive(const AFPSGAMECharacter* Character) const
{
    return HasAuthority()&&BowDrawStartedAt>=0.&&BowDrawPawn.Get()==Character;
}

void AColdSteelPlayerState::CancelBowDraw(bool bExhausted)
{
    if(!HasAuthority()||BowDrawStartedAt<0.)return;
    auto* Character=Cast<AFPSGAMECharacter>(BowDrawPawn.Get());
    const FString Weapon=BowDrawWeapon;
    const FGuid DrawId=BowDrawId;
    BowDrawStartedAt=-1.;BowDrawPawn.Reset();BowDrawWeapon.Reset();
    BowDrawId.Invalidate();
    ClientCancelBowDraw(Character,Weapon,DrawId,bExhausted);
}

void AColdSteelPlayerState::ResetBowPerfectSpeedBonus()
{
    if(!HasAuthority())return;
    bBowPerfectSpeedBonus=false;BowPerfectPawn.Reset();BowPerfectWeapon.Reset();
}
void AColdSteelPlayerState::RefreshBowPerfectOwner()
{
    const auto* Pawn=GetPawn();
    const auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Model?Model->ActiveBow():nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Pawn||BowPerfectPawn.Get()!=Pawn||!Item||Item->InstanceId!=BowPerfectWeapon||!Health||Health->IsDead())
        ResetBowPerfectSpeedBonus();
}

void AColdSteelPlayerState::TickBowDrawAuthority()
{
    RefreshBowPerfectOwner();
    if(BowDrawStartedAt<0.)return;
    const auto* Character=Cast<AFPSGAMECharacter>(GetPawn());
    const auto* Model=ColdSteelAuthority::ForPawn(Character);
    const auto* Bow=Model?Model->ActiveBow():nullptr;
    const auto* Health=Character?Character->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const bool bExhausted=Model&&(Model->Stamina()<=0.f||
        (ColdSteelBow::AuroraRiser(Model,Bow)&&!Model->HasInfiniteMana()&&Model->Mana()<=0.f));
    if(!Character||BowDrawPawn.Get()!=Character||!Bow||Bow->InstanceId!=BowDrawWeapon
        ||!Health||Health->IsDead()||Character->IsTraversing()||Character->IsSprinting()
        ||Character->IsCastBlockingLeftHandAction()||UPlayerKnockdownComponent::IsKnockedDown(Character)||bExhausted)
        CancelBowDraw(bExhausted);
}

void AColdSteelPlayerState::ClientCancelBowDraw_Implementation(AFPSGAMECharacter* Character,const FString& Weapon,FGuid DrawId,bool bExhausted)
{
    if(!Character||Character!=GetPawn()||!Character->IsLocallyControlled())return;
    const auto* Model=ColdSteelAuthority::ForPawn(Character);
    const auto* Item=Model?Model->ActiveBow():nullptr;
    if(!Item||Item->InstanceId!=Weapon)return;
    if(auto* Bow=Character->FindComponentByClass<UBowWeaponComponent>();Bow&&Bow->IsDrawing()&&Bow->NetworkDrawId()==DrawId)
    {
        if(bExhausted)Bow->CancelDrawForExhaustion(Model->Stamina()>0.f&&ColdSteelBow::AuroraRiser(Model,Item));
        else Bow->CancelAction(false);
    }
}

void AColdSteelPlayerState::ClientConfirmBowDraw_Implementation(AFPSGAMECharacter* Character,const FString& Weapon,FGuid DrawId,float FullDrawSeconds,bool PerfectSpeed)
{
    if(!Character||Character!=GetPawn()||!Character->IsLocallyControlled())return;
    if(auto* Bow=Character->FindComponentByClass<UBowWeaponComponent>())Bow->ConfirmNetworkDraw(Weapon,DrawId,FullDrawSeconds,PerfectSpeed);
}

void AColdSteelPlayerState::ServerSetBowDraw_Implementation(AFPSGAMECharacter* Character,const FString& Weapon,bool bDrawing,float CarriedSeconds,FGuid DrawId)
{
    if (!HasAuthority() || !Character || Character != GetPawn()) return;
    if(!DrawId.IsValid()||(!bDrawing&&(DrawId!=BowDrawId||Weapon!=BowDrawWeapon)))return;
    BowDrawStartedAt=-1.;BowDrawPawn.Reset();BowDrawWeapon.Reset();
    BowDrawId.Invalidate();
    if (!bDrawing || !FMath::IsFinite(CarriedSeconds)) return;
    const auto* PC=Cast<APlayerController>(GetOwner());
    const auto* Model=PC&&PC->IsLocalController()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():ShadowModel.Get();
    const auto* Bow=Model?Model->ActiveBow():nullptr;
    const auto* Health=Character->FindComponentByClass<UFPSCombatHealthComponent>();
    if (!Bow || Bow->InstanceId!=Weapon || !Health || Character->IsTraversing()
        ||Character->IsSprinting()||Character->IsCastBlockingLeftHandAction()||Model->Stamina()<=0.f)
    {ClientCancelBowDraw(Character,Weapon,DrawId,Model&&Model->Stamina()<=0.f);return;}
    if(ColdSteelBow::AuroraRiser(Model,Bow)&&!Model->HasInfiniteMana()&&Model->Mana()<=0.f)
    {ClientCancelBowDraw(Character,Weapon,DrawId,true);return;}
    // 死亡或弓已卸下时清掉待生效的完美节拍加速，避免重生/换弓后白拿一次加速。
    if (Health->IsDead()) { bBowPerfectSpeedBonus=false;ClientCancelBowDraw(Character,Weapon,DrawId,false);return; }
    RefreshBowPerfectOwner();
    BowDrawPawn=Character;BowDrawWeapon=Weapon;BowDrawId=DrawId;
    if(auto* Cadence=Character->FindComponentByClass<UBowCadenceComponent>())Cadence->RefreshEquipment(Model);
    BowDrawSeconds=float(ColdSteelBow::Evaluate(*Bow,Model).Draw)*ColdSteelBow::DrawSpeedScale(bBowPerfectSpeedBonus);
    // DrawEntry may finish partway through a rendered frame. Bound the carried
    // portion, while retaining the same start as the owner's animation clock.
    BowDrawStartedAt=GetWorld()->GetTimeSeconds()-FMath::Clamp(CarriedSeconds,0.f,.25f);
    ClientConfirmBowDraw(Character,Weapon,DrawId,BowDrawSeconds,bBowPerfectSpeedBonus);
}

bool AColdSteelPlayerState::ExecuteBowShot(const FColdSteelInventoryRequest& Request,UColdSteelStatusModel* Model,FString& Reason)
{
    // The inventory dispatcher retires preparation and prediction for every failure,
    // including failures that happen before this function is reached.
    auto Reject=[&](const TCHAR* Why)
    {
        Reason=Why;return false;
    };
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    const double DrawAge=GetWorld()->GetTimeSeconds()-BowDrawStartedAt;
    const bool HasDrawSession=BowDrawStartedAt>=0. && BowDrawPawn==Pawn && BowDrawWeapon==Request.Item
        &&Request.BowDrawId.IsValid()&&Request.BowDrawId==BowDrawId;
    if(HasDrawSession){BowDrawStartedAt=-1.;BowDrawPawn.Reset();BowDrawWeapon.Reset();BowDrawId.Invalidate();}
    const auto* Bow=Model?Model->ActiveBow():nullptr;
    const FVector Direction=FVector(Request.Direction).GetSafeNormal();
    if(!Pawn||!Bow||Bow->InstanceId!=Request.Item||Pawn->IsTraversing()
        ||!FMath::IsFinite(Request.Charge)||Request.Charge<ColdSteelBow::MinimumFireDrawFraction||Request.Charge>1.f
        ||Request.Eye.ContainsNaN()||Request.Origin.ContainsNaN()||Direction.ContainsNaN()||Direction.IsNearlyZero()
        ||FVector::DistSquared(Request.Eye,Pawn->GetPawnViewLocation())>FMath::Square(150.f)
        ||FVector::DistSquared(Request.Origin,Request.Eye)>FMath::Square(200.f)
        ||FVector::DotProduct(Direction,Pawn->GetBaseAimRotation().Vector())<.7f
        ||!HasDrawSession)
    {return Reject(TEXT("弓或瞄准位置已变化，请重新拉弓"));}
    const FColdSteelItem Fired=*Bow;
    auto* Element=Pawn->FindComponentByClass<UFPSElementalArrowComponent>();
    auto* Light=Pawn->FindComponentByClass<UFPSIlluminationArrowComponent>();FIlluminationArrowCast LightCast;
    if(Request.bIlluminationArrow&&Request.ArrowElement!=EArrowElement::None)return Reject(TEXT("一次只能准备一种魔法箭"));
    if((Request.bIlluminationArrow&&!Light)||(Light&&!Light->BuildShot(Request.bIlluminationArrow,LightCast,Reason)))return Reject(*Reason);
    FElementalArrowCast ElementCast;
    if((Request.ArrowElement!=EArrowElement::None&&!Element)||(Element&&!Element->BuildShot(Request.ArrowElement,ElementCast,Reason)))
        return Reject(*Reason);
    const auto Stats=ColdSteelBow::Evaluate(Fired,Model);
    const auto Piercing=HeartPiercingArrow::ForModel(Model,INDEX_NONE,BowDrawSeconds);
    const double Now=GetWorld()->GetTimeSeconds();
    if(Now-LastBowShotAt<FMath::Max(.1,Stats.Nock*.5))return Reject(TEXT("射击间隔过短"));
    // A release must belong to a real draw session and cannot claim a full draw
    // immediately after ServerSetBowDraw. Ongoing stamina, not a timeout, owns
    // the session lifetime; the shadow model drains the same rate as the owner.
    if(!HasDrawSession
        || DrawAge<double(BowDrawSeconds)*FMath::Clamp(Request.Charge,0.f,1.f)-.2)
        return Reject(TEXT("拉弓会话无效或未完成"));
    // Full cadence uses the server's live stack/expiry state. It bypasses only
    // the rhythm window; the draw, minimum charge and resource gates still apply.
    const auto* ActiveCadence=UBowCadenceComponent::ForItem(Model,Fired);
    const bool AutomaticRhythm=ActiveCadence&&ActiveCadence->HasAutomaticRhythmFor(Fired.InstanceId);
    // Otherwise both clocks must agree; the allowance only absorbs delivery jitter.
    const bool Perfect=AutomaticRhythm||(HasDrawSession && Request.Charge>=1.f
        && ColdSteelBow::IsPerfectRelease(Request.BowReleaseElapsed,BowDrawSeconds,float(Stats.RhythmWindow))
        && FMath::Abs(DrawAge-Request.BowReleaseElapsed)<=.15);
    const bool bPiercing=HeartPiercingArrow::IsCharged(Piercing,float(DrawAge),Request.Charge)
        && FMath::IsFinite(Request.BowChargeElapsed)
        && FMath::Abs(DrawAge-Request.BowChargeElapsed)<=.2
        && HeartPiercingArrow::IsCharged(Piercing,Request.BowChargeElapsed,Request.Charge);
    const FString Ammo=Model->AmmoDefinitionFor(Fired);
    const bool Owned=!Pawn->HasInfiniteReserveAmmoFor(Ammo);
    // Evaluate already includes the player's action-cost multiplier, as the panel does.
    const float Cost=float(Stats.Stamina)*FMath::Lerp(.4f,1.f,Request.Charge);
    const bool bAurora=ColdSteelBow::AuroraRiser(Model,&Fired)!=nullptr;
    const float BeamMana=bAurora?Model->AdjustedManaCost(Cost):0.f;
    const float SkillMana=Request.bIlluminationArrow?LightCast.ManaCost:(ElementCast.Element!=EArrowElement::None?ElementCast.ManaCost:0.f);
    if(!Model->CanSpendMana(BeamMana+SkillMana))return Reject(TEXT("魔法不足，已收弓"));
    if(!Model->CanSpendStamina(Cost)||(Owned&&Model->PouchCount(Ammo)<1))
    {Reason=TEXT("体力或箭支不足");return Reject(TEXT("体力或箭支不足"));}
    auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    const auto Visual=G?G->ResolveBowVisual(Fired):Fired;
    const auto N=[&](const TCHAR* Key,float Default){return float(ColdSteelInventory::Number(Visual,Key,Default));};
    auto* Shaft=LoadObject<UStaticMesh>(nullptr,*ColdSteelInventory::Text(Visual,TEXT("bow_part_arrow_mesh")));
    const auto HeadPath=ColdSteelInventory::Text(Visual,TEXT("arrow_head_mesh"));
    auto* Head=HeadPath.IsEmpty()?nullptr:LoadObject<UStaticMesh>(nullptr,*HeadPath);
    FActorSpawnParameters Spawn;Spawn.Owner=Pawn;Spawn.Instigator=Pawn;
    Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Arrow=GetWorld()->SpawnActor<ABowArrow>(Request.Origin,Direction.Rotation(),Spawn);
    if(!Arrow)return Reject(TEXT("箭支生成失败"));
    const auto Before=Model->Snapshot();auto After=Before;
    if(!Model->HasInfiniteMana())After.Mana-=BeamMana;
    if(Owned)After.AmmoPouch.FindOrAdd(Ammo)-=1;
    After.Stamina=FMath::Max(0.f,After.Stamina-Cost);
    After.StaminaRecoveryDelay=Model->StaminaTuning.RecoveryDelay;
    if(ElementCast.Element!=EArrowElement::None)Model->StageElementalArrowCost(After,ElementCast);
    if(Request.bIlluminationArrow)Model->StageIlluminationArrowCost(After,LightCast);
    if(!Model->CommitCampfireState(After,TEXT("Inventory"),SlotName))
    {Arrow->Destroy();Reason=TEXT("箭支扣除未保存，未发射");return Reject(TEXT("箭支扣除未保存，未发射"));}
    auto Shot=ColdSteelSkills::Snapshot(Pawn,&Fired,true);Shot.DamageContext=Request.Charge;
    Shot.bAuroraBeam=bAurora;
    Shot.bPerfectBowRelease=Perfect;
    Shot.bHeartPiercingArrow=bPiercing;
    Shot.BowTargetPenetration=bPiercing?Piercing.TargetPenetration:0;
    if(N(TEXT("critical_chance"),-1)>=0)Shot.CriticalChance=FMath::Max(Shot.CriticalChance,N(TEXT("critical_chance"),-1));
    if(N(TEXT("toughness_multiplier"),0)>0)Shot.ToughnessDamageMultiplier=N(TEXT("toughness_multiplier"),0);
    const float Damage=(Shot.DamagePanel.Total()>0?Shot.DamagePanel.Total():N(TEXT("full_damage"),69))
        *ColdSteelBow::DrawDamageMultiplier(Request.Charge)*Model->AmmoDamageMultiplier(Fired)
        *(bPiercing?Piercing.DamageMultiplier:1.f);
    Arrow->Configure(Damage,float(Stats.Speed)*100.f*FMath::Lerp(FMath::Clamp(N(TEXT("min_speed_ratio"),.35f),0.f,1.f),1.f,Request.Charge)
        *(bPiercing?Piercing.SpeedMultiplier:1.f),
        N(TEXT("arrow_gravity_cm"),980),float(Stats.Range)*100.f,Shot,Shaft,Head,
        N(TEXT("arrow_radius_cm"),.3f),N(TEXT("arrow_length_cm"),76),Ammo,Owned,N(TEXT("arrow_recovery_seconds"),120));
    Arrow->SetElementalCast(ElementCast);
    if(Request.bIlluminationArrow){Arrow->SetIlluminationCast(LightCast);Light->ShotCommitted();}
    if(Element&&ElementCast.Element!=EArrowElement::None)Element->ShotCommitted();
    if(bAurora||Request.bIlluminationArrow||ElementCast.Element!=EArrowElement::None)Model->NotifyMagicReleased();
    if(auto* Echo=Pawn->FindComponentByClass<UBowMountainEchoComponent>())Echo->CommitArrow(Arrow,Fired.InstanceId,Request.Charge,Request.Eye);
    if(auto* Cadence=Pawn->FindComponentByClass<UBowCadenceComponent>())Cadence->CommitRelease(Fired.InstanceId,Perfect);
    Arrow->ResolveLaunchObstruction(Request.Eye);LastBowShotAt=Now;
    // 本次命中节拍 → 下一条箭 +25% 拉弓速度；未命中则清除。
    bBowPerfectSpeedBonus=Perfect;
    BowPerfectPawn=Pawn;BowPerfectWeapon=Fired.InstanceId;bLastBowShotPiercing=bPiercing;
    Reason=TEXT("已发射箭支");return true;
}
