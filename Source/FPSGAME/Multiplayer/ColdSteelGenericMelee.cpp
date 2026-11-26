#include "ColdSteelGenericMelee.h"
#include "../Weapons/WoodenTorchItem.h"
#include "../Weapons/WoodenTorchComponent.h"
#include "../Weapons/EagleTalonGuardComponent.h"
#include "ColdSteelPlayerState.h"
#include "ColdSteelAuthorityContext.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Skills/LightningHasteSpeed.h"
#include "../Skills/SwordUppercutTuning.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/RuneSwordRhythm.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/RuneSwordThrustRhythm.h"
#include "../Weapons/RuneSwordOverheadRhythm.h"
#include "../Weapons/RuneSwordRisingDragon.h"
#include "../Weapons/HighlandRidgeThrust.h"
#include "../Weapons/HighlandBreakSweep.h"
#include "../Weapons/Staff/StaffQuickCombatMotion.h"
#include "../Weapons/Staff/StaffPrimaryAttackMotion.h"
#include "../Weapons/Unarmed/UnarmedPunchTuning.h"
#include "../Production/ProductionToolStats.h"
#include "../Production/ProductionAxeImpactMotion.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

namespace
{
bool IsOrdinaryTool(const FColdSteelItem* Item)
{
    if(!Item||!ColdSteelInventory::IsEquippedProductionTool(*Item))return false;
    const FString Kind=ColdSteelInventory::Text(*Item,TEXT("tool_kind"));
    return Kind==TEXT("axe")||Kind==TEXT("pickaxe")||Kind==TEXT("shovel");
}
bool UsesStaffStrike(const FColdSteelItem* Item,const UGunsmithSystem* Smith)
{
    return Item&&(ColdSteelInventory::UsesStaffMelee(*Item)
        ||(Smith&&Smith->IsStaff(Item->Definition)));
}
}

uint32 AColdSteelPlayerState::RequestGenericMeleeStart(APawn* Pawn,const FString& Instance,uint8 Family,uint8 Meta)
{
    if(!Pawn||Pawn!=GetPawn()||!Pawn->IsLocallyControlled())return 0;
    if(!++GenericMeleeSequence)++GenericMeleeSequence;
    const uint32 Serial=GenericMeleeSequence;
    ServerRememberGenericMeleeStart(Pawn,Instance,Family,Meta,Serial);
    // Owners predict locally. Listen hosts must not play an attack rejected by
    // their immediate authority call.
    return !HasAuthority()||GenericMeleeReceipts.Contains(Serial)?Serial:0;
}

void AColdSteelPlayerState::ServerRememberGenericMeleeStart_Implementation(APawn* SourcePawn,
    const FString& Instance,uint8 Family,uint8 Meta,uint32 Serial)
{
    using namespace ColdSteelGenericMelee;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    if(!HasAuthority()||!Pawn||Pawn!=SourcePawn||!GetWorld()||!Serial)return;
    if(GenericMeleePawn.Get()!=Pawn)
    {
        GenericMeleeReceipts.Reset();GenericMeleeReadyAt=0.;
        LastGenericMeleeSequence=0;GenericMeleePawn=Pawn;
    }
    if(LastGenericMeleeSequence&&int32(Serial-LastGenericMeleeSequence)<=0)return;
    // Retire rejected IDs too: an intent denied during eating cannot be replayed
    // after the reservation ends and become an accepted old attack.
    LastGenericMeleeSequence=Serial;
    auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    const auto* HP=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    const double Now=GetWorld()->GetTimeSeconds();
    if(!Model||!HP||HP->IsDead()||HasAuthorityConsumableReservation(Pawn)
        ||Pawn->IsCastBlockingLeftHandAction()||Pawn->IsTraversing()||Pawn->IsDodging()||(Pawn->IsSliding()&&Family!=SwordDash)
        ||UBoundCongregateCaptureComponent::IsCaptured(Pawn)||!PendingCastSkill.IsNone()
        ||UppercutActiveSequence||IsQuickCombatExecuting(Pawn)||IsSwordWhirlwindExecuting(Pawn)
        ||Now+.08<GenericMeleeReadyAt)return;
    const auto* Smith=GetGameInstance()?GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    const FColdSteelItem* Item=Family==Tool?Model->ActiveProductionTool():Model->Equipped();
    if(Family==Staff&&(!Item||Item->InstanceId!=Instance))
    {
        const auto* Off=Model->Equipped(Model->ActiveOffhandSlot());
        if(!Off||Off->InstanceId!=Instance||!ColdSteelInventory::IsWoodenTorch(*Off)||Model->ActiveProductionTool())return;
        if((Item&&ColdSteelInventory::IsDualPistol(*Item))||Pawn->IsOffhandReloadActive()||Pawn->IsReloading()||!CanAuthorityBeginConsumable(Pawn))return;
        Item=Off;
    }
    if(Family==Unarmed)
    {
        const int32 Active=Model->Snapshot().ActiveWeaponSlot,Offhand=Active==6?8:11;
        if(Meta!=UnarmedPunch::AttackMeta||!Instance.IsEmpty()||Item||Model->Equipped(Offhand)
            ||Model->ActiveProductionTool())return;
    }
    else if(!Item||Item->InstanceId!=Instance||Instance.IsEmpty())return;
    ColdSteelAuthority::FScope Scope(Model);
    const double Haste=FMath::Max(.05f,LightningHaste::ActionSpeed(Pawn));
    double Duration=0.,ContactStart=0.,ContactEnd=0.,Cost=0.;
    if(Family==Sword||Family==SwordOverhead)
    {
        if(!ColdSteelInventory::IsTwoHandedSword(*Item)||Model->ActiveProductionTool()
            ||Meta<1||Meta>3||(Family==SwordOverhead&&Meta!=1))return;
        const auto Stats=ColdSteelMelee::Evaluate(*Item,Model);
        const double Rate=FMath::Max(.01,Stats.AttackRate);
        Cost=ColdSteelMelee::AttackStamina(Item,Model);
        Duration=Stats.AttackSeconds;
        ContactStart=RuneSwordRhythm::ContactStart/Rate;ContactEnd=RuneSwordRhythm::ContactEnd/Rate;
        if(Family==SwordOverhead)
        {
            Duration=RuneSwordOverheadRhythm::AttackEnd/Rate;
            ContactStart=RuneSwordOverheadRhythm::ContactStart/Rate;ContactEnd=RuneSwordOverheadRhythm::ContactEnd/Rate;
        }
        else if(Meta==3)
        {
            Duration=Stats.ThrustSeconds;
            ContactStart=RuneSwordThrustRhythm::ContactStart/Rate;ContactEnd=RuneSwordThrustRhythm::ContactEnd/Rate;
            if(HighlandRidgeThrust::Installed(Smith,Item))
            {
                const float Lead=HighlandRidgeThrust::CounterLead,Speed=float(Rate)*HighlandRidgeThrust::FinisherPlaybackRate;
                ContactStart=HighlandRidgeThrust::ToWall(Lead+HighlandRidgeThrust::ContactStart,Lead,Speed);
                ContactEnd=HighlandRidgeThrust::ToWall(Lead+HighlandRidgeThrust::ContactEnd,Lead,Speed);
            }
            else if(ColdSteelModularSword::UsesOverheadFinisher(*Item))
            {
                ContactStart=(RuneSwordOverheadRhythm::ContactStart-RuneSwordOverheadRhythm::FinisherEntry)/Rate;
                ContactEnd=(RuneSwordOverheadRhythm::ContactEnd-RuneSwordOverheadRhythm::FinisherEntry)/Rate;
            }
            else if(ColdSteelModularSword::UsesRisingDragonFinisher(*Item))
            {
                ContactStart=RuneSwordRisingDragon::PlaybackTime(RuneSwordUppercutMotion::ReleaseStart)/Rate;
                ContactEnd=RuneSwordRisingDragon::PlaybackTime(RuneSwordUppercutMotion::Finish)/Rate;
            }
        }
    }
    else if(Family==SwordDash)
    {
        if(Meta!=0x16||Item->Definition!=TEXT("ue_forged_steel_greatsword")||Model->ActiveProductionTool()||Model->MasteryProgress(TEXT("dashAttack")).Level<1)return;
        Duration=RuneSwordOverheadRhythm::FinisherSeconds/Haste;
        ContactStart=RuneSwordOverheadRhythm::DashWindupSeconds/Haste;
        ContactEnd=ContactStart+(RuneSwordOverheadRhythm::ContactEnd-RuneSwordOverheadRhythm::ContactStart)/Haste;
        Cost=Model->DashAttackStats().StaminaCost;
    }
    else if(Family==Tool)
    {
        if(Meta!=0||!IsOrdinaryTool(Item))return;
        const auto Stats=ColdSteelTool::Evaluate(*Item,Model);
        const double Rate=FMath::Max(.01,Stats.RateScale);
        double SourceDuration=FMath::Max(.4,ColdSteelInventory::Number(*Item,TEXT("swing_seconds"),.68));
        double SourceContact=FMath::Clamp(ColdSteelInventory::Number(*Item,TEXT("contact_seconds"),.24),.1,SourceDuration-.1);
        if(ColdSteelInventory::Text(*Item,TEXT("tool_kind"))==TEXT("axe"))
        {
            // The same authored configuration as the tool component, cached once.
            static const FProductionAxeImpactMotion Motion=[] {FProductionAxeImpactMotion M;M.Load();return M;}();
            SourceDuration=Motion.SwingSeconds;SourceContact=Motion.ContactSeconds;
        }
        Duration=SourceDuration/Rate;ContactStart=ContactEnd=SourceContact/Rate;Cost=Stats.StaminaCost;
    }
    else if(Family==Unarmed)
    {
        Duration=StaffQuickCombatMotion::Length/Haste;
        ContactStart=ContactEnd=StaffQuickCombatMotion::Contact/Haste;Cost=ColdSteelMelee::UnarmedAttackStamina(Model);
    }
    else if(Family==Staff)
    {
        if(Meta!=0||!UsesStaffStrike(Item,Smith)||Model->ActiveProductionTool())return;
        Duration=FMath::Max(.1,double(ColdSteelWeaponStats::Interval(Item,Model,.5)))/Haste;
        ContactStart=Duration*.4;ContactEnd=Duration*.7;Cost=ColdSteelMelee::UnarmedAttackStamina(Model);
    }
    else return;
    if(!FMath::IsFinite(Duration)||Duration<=0.||Duration>30.||!FMath::IsFinite(ContactStart)
        ||!FMath::IsFinite(ContactEnd)||!Model->CanSpendStamina(float(Cost)))return;
    // Existing action/harvest ledgers retain ownership of their payments.
    for(auto It=GenericMeleeReceipts.CreateIterator();It;++It)
        if(It.Value().Pawn.Get()!=Pawn||Now>It.Value().Expires)It.RemoveCurrent();
    if(GenericMeleeReceipts.Num()>=MaxReceipts)return;
    // Forged sword owners predict ordinary swing costs in StartSwing. Commit the same
    // cost once on the remote shadow, including misses. Gale pays through its own RPC.
    if((Family==Sword||Family==SwordOverhead||Family==SwordDash)&&!Pawn->IsLocallyControlled()&&Item
        &&Item->Definition==TEXT("ue_forged_steel_greatsword"))
    {
        const auto* SwordComponent=Pawn->FindComponentByClass<URuneSwordComponent>();
        if(!SwordComponent||(!SwordComponent->HasGaleGuard(Item)&&!Model->SpendStamina(float(Cost))))return;
        UEagleTalonGuardComponent::Commit(Pawn,Instance,EEagleStrike::Ordinary,Serial);
    }
    // The remote owner predicts the torch cost on entry. Commit it once on the shadow, including a miss.
    if(Family==Staff&&Item&&ColdSteelInventory::IsWoodenTorch(*Item)&&!Pawn->IsLocallyControlled()&&
        !Model->SpendStamina(float(Cost)))return;
    auto& Receipt=GenericMeleeReceipts.Add(Serial);
    Receipt.Pawn=Pawn;if(Item)Receipt.Item=*Item;
    Receipt.Serial=Serial;Receipt.Family=Family;Receipt.Meta=Meta;Receipt.StartedAt=Now;
    // ClientFireTime describes contact, never authorization. Transport allowance
    // accommodates the earlier local start but never bypasses the gate above.
    // Ordinary swords/finishers do not stack contact freezes. Only the staff
    // pauses once (bImpactConfirmed), using its actual authored maximum.
    const double Pause=Family==Staff?FMath::Max(StaffPrimaryAttackMotion::FleshStopSeconds,
        StaffPrimaryAttackMotion::WallStopSeconds):0.;
    Receipt.ContactFrom=Now+ContactStart-ReportGrace-ContactSlack;
    Receipt.ContactUntil=Now+ContactEnd+Pause+ContactSlack;
    Receipt.BusyUntil=Now+Duration;Receipt.Expires=Receipt.BusyUntil+ReportGrace+Pause;
    GenericMeleeReadyAt=Receipt.BusyUntil;
}

bool AColdSteelPlayerState::RequiresGenericMeleeReceipt(const FColdSteelNetHitReport& Report,const FColdSteelItem* Item) const
{
    if(Report.AttackMeta==UnarmedPunch::AttackMeta&&Report.ItemDefinition.IsEmpty())return true;
    if(!Item)return false;
    if(Report.AttackMeta&0x80)return false; // Already requires its quick-combat serial.
    if(IsOrdinaryTool(Item))return true; // Do not let a forged heavy bit bypass tool registration.
    const auto* Smith=GetGameInstance()?GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    if(UsesStaffStrike(Item,Smith))return true;
    if(!ColdSteelInventory::IsTwoHandedSword(*Item))return false;
    if(Report.AttackMeta==0x16)
    {
        const auto* Receipt=GenericMeleeReceipts.Find(Report.GenericMeleeSerial);
        return (Receipt&&Receipt->Family==ColdSteelGenericMelee::SwordDash)
            ||Item->Definition==TEXT("ue_forged_steel_greatsword");
    }
    // Existing special gates remain authoritative. Unknown sword semantics
    // cannot escape the ordinary receipt check by merely setting a flag.
    return Report.AttackMeta!=0x10&&Report.AttackMeta!=0x15
        &&Report.AttackMeta!=SwordUppercut::AttackMeta&&Report.AttackMeta!=HighlandBreakSweep::AttackMeta
        &&!ShadowStep::IsMeta(Report.AttackMeta)
        &&!(Report.AttackMeta&(0x20|0x40));
}

bool AColdSteelPlayerState::ValidateGenericMeleeReceipt(const FColdSteelNetHitReport& Report,
    const APawn* Pawn,const FColdSteelItem* Item) const
{
    using namespace ColdSteelGenericMelee;
    const auto* Receipt=GenericMeleeReceipts.Find(Report.GenericMeleeSerial);
    if(!Pawn||Pawn!=GetPawn()||!Receipt||Receipt->Pawn.Get()!=Pawn||!GetWorld()
        ||!Report.Target||Receipt->Targets.Contains(Report.Target.Get())||Receipt->Targets.Num()>=MaxTargets
        ||GetWorld()->GetTimeSeconds()>Receipt->Expires||Report.AttackMeta!=Receipt->Meta
        ||!FMath::IsFinite(Report.ClientFireTime)||Report.ClientFireTime<=0.
        ||Report.ClientFireTime<Receipt->ContactFrom||Report.ClientFireTime>Receipt->ContactUntil)return false;
    if(Receipt->Family==Unarmed)
    {
        if(Item||!Report.ItemDefinition.IsEmpty()||!Report.ItemInstance.IsEmpty())return false;
    }
    else if(!Item||Item->InstanceId!=Receipt->Item.InstanceId||Item->Definition!=Receipt->Item.Definition
        ||Report.ItemInstance!=Receipt->Item.InstanceId||Report.ItemDefinition!=Receipt->Item.Definition)return false;
    bool Single=Receipt->Family==Tool||Receipt->Family==Unarmed;
    if(Receipt->Family==Sword&&Receipt->Meta==3)
    {
        const auto* Smith=GetGameInstance()?GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
        Single=!ColdSteelModularSword::UsesOverheadFinisher(Receipt->Item)
            &&!ColdSteelModularSword::UsesRisingDragonFinisher(Receipt->Item)
            &&!HighlandRidgeThrust::Installed(Smith,&Receipt->Item);
    }
    return !Single||Receipt->Targets.IsEmpty();
}

void AColdSteelPlayerState::CommitGenericMeleeReceipt(const FColdSteelNetHitReport& Report,
    const APawn* Pawn,const FColdSteelItem* Item)
{
    if(RequiresGenericMeleeReceipt(Report,Item)&&ValidateGenericMeleeReceipt(Report,Pawn,Item))
        GenericMeleeReceipts.FindChecked(Report.GenericMeleeSerial).Targets.Add(Report.Target.Get());
}

void AColdSteelPlayerState::RequestTorchEmbers(APawn* Pawn,uint32 OrdinarySwingSerial,const FVector& Point,const FVector& Normal)
{
    const bool bQuick=OrdinarySwingSerial==0;
    ServerTorchEmbers(Pawn,bQuick?QuickCombatSequence:OrdinarySwingSerial,bQuick,Point,Normal);
}

void AColdSteelPlayerState::ServerTorchEmbers_Implementation(APawn* Pawn,uint32 Serial,bool bQuick,FVector_NetQuantize10 Point,FVector_NetQuantizeNormal Normal)
{
    if(!Serial||!Pawn||Pawn!=GetPawn()||!ShadowModel||ShadowModel->ActiveProductionTool())return;
    const auto* Main=ShadowModel->Equipped();
    const auto* Off=ShadowModel->Equipped(ShadowModel->ActiveOffhandSlot());
    const double Now=GetWorld()->GetTimeSeconds();
    FGenericMeleeReceipt* Receipt=nullptr;
    if(bQuick)
    {
        if(Serial!=QuickCombatServerSequence||QuickCombatPawn.Get()!=Pawn||Now>QuickCombatUntil||Serial==LastTorchQuickSurface||
            !ColdSteelInventory::QuickTorch(Main,Off)||QuickCombatEquipment!=QuickCombatEquipmentKey())return;
    }
    else
    {
        Receipt=GenericMeleeReceipts.Find(Serial);
        if(!Receipt||Receipt->Pawn.Get()!=Pawn||Receipt->Family!=ColdSteelGenericMelee::Staff||
            Receipt->bTorchSurfaceSent||Now>Receipt->Expires||!ColdSteelInventory::IsWoodenTorch(Receipt->Item))return;
        const auto& Id=Receipt->Item.InstanceId;
        if((!Main||Main->InstanceId!=Id)&&(!Off||Off->InstanceId!=Id))return;
    }
    auto* Torch=Pawn->FindComponentByClass<UWoodenTorchComponent>();
    const float Reach=FMath::Max(175.f,ShadowModel->QuickCombatDefinition().QuickCombat.RangeCM+65.f);
    if(Torch&&Torch->PublishSurfaceContact(Point,Normal,Reach))
    {
        if(bQuick)LastTorchQuickSurface=Serial;
        else Receipt->bTorchSurfaceSent=true;
    }
}

bool AColdSteelPlayerState::HasGenericMeleeBusy(const APawn* Pawn) const
{
    if(!HasAuthority()||!Pawn||Pawn!=GetPawn()||GenericMeleePawn.Get()!=Pawn||!GetWorld())return false;
    return GetWorld()->GetTimeSeconds()<GenericMeleeReadyAt;
}
