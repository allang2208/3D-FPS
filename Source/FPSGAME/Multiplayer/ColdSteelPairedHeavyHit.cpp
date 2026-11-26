#include "ColdSteelPreparedHit.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../UI/ColdSteelStatusModel.h"

bool AColdSteelPlayerState::ForwardPairedHeavyHit(AActor* Shooter,const FHitResult& Hit,float Damage,
    const FVector& Direction,const FColdSteelSkillShot& Shot,const FKukriPairedHeavyHit& Pair)
{
    const auto* Pawn=Cast<APawn>(Shooter);
    auto* PS=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    if(!PS)return false;
    const auto& Other=Pair.Second;
    PS->ServerReportPairedHeavyHit(MakeHitReport(Shooter,Hit,Damage,Direction,Shot),
        MakeHitReport(Shooter,Other.Hit,Other.Damage,Other.Direction,Other.Shot));
    return true;
}

void AColdSteelPlayerState::ServerReportPairedHeavyHit_Implementation(
    const FColdSteelNetHitReport& First,const FColdSteelNetHitReport& Second)
{
    const auto* FirstItem=ShadowModel?ShadowModel->FindItem(First.ItemInstance):nullptr;
    const auto* SecondItem=ShadowModel?ShadowModel->FindItem(Second.ItemInstance):nullptr;
    if(!HasAuthority()||!First.Target||First.Target!=Second.Target||First.ItemInstance==Second.ItemInstance
        ||!FirstItem||!SecondItem||!ColdSteelInventory::UsesKukriMoveset(*FirstItem)||!ColdSteelInventory::UsesKukriMoveset(*SecondItem)
        ||First.AttackMeta!=0x10||Second.AttackMeta!=0x10||!(First.Flags&(1<<3))||!(Second.Flags&(1<<3))
        ||(First.Flags&(1<<4))||(Second.Flags&(1<<4))||!First.MasteryAttackSerial
        ||First.MasteryAttackSerial!=Second.MasteryAttackSerial||First.MeleeDamagePhase!=Second.MeleeDamagePhase)return;
    // Both contacts pass the ordinary release receipt, range, occlusion, target
    // history and per-blade duplicate checks. No offhand hit is inferred.
    FColdSteelPreparedHit A,B;
    const bool AcceptedA=PrepareHitReport(First,A);
    const bool AcceptedB=PrepareHitReport(Second,B);
    if(AcceptedA&&AcceptedB)
    {
        FKukriPairedHeavyHit Pair;Pair.Second={B.Hit,FVector(B.Report.Direction),B.Damage,B.Shot};
        SettleHitReport(A,&Pair);
    }
    else if(AcceptedA)SettleHitReport(A);
    else if(AcceptedB)SettleHitReport(B);
}
