#include "HighlandEquipmentWireAudit.h"
#include "KukriCombatWireAudit.h"
#include "../Monsters/NurseZombie.h"
#include "Materials/Material.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

namespace HighlandEquipmentWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("HighlandEquipmentWireAudit"));}
namespace
{
FString Identity(bool Host){return Host?TEXT("HighlandAudit_HostSword"):TEXT("HighlandAudit_GuestSword");}
bool Ridge(int32 Phase){return Phase!=3;}
bool Gale(int32 Phase){return Phase!=1;}
bool Oath(int32 Phase){return Phase!=1 && Phase!=3;}
TWeakObjectPtr<ANurseZombie> Target;
float StartingHP=0.f;
double GuestCreditAtStart=0.;
const TCHAR* BladeId(int32 Phase,bool Host)
{
    return Ridge(Phase)?TEXT("highland_ridge_piercer"):Host?TEXT("highland_broadblade"):TEXT("factory");
}
TSharedPtr<FJsonObject> Catalog()
{
    static TSharedPtr<FJsonObject> Data;
    if(!Data){FString Text;FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/highland-claymore-modules.json")));
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data);}
    return Data;
}
}
FColdSteelProfile Seed(UColdSteelStatusModel* Model,bool Host)
{
    auto State=Model->Snapshot();State.Items.Reset();State.ActiveWeaponSlot=6;State.ActiveProductionTool.Reset();State.DungeonRun={};
    State.Stamina=150;State.bSprintExhausted=false;for(auto& S:State.Skills)S.Value.Level=1;
    auto Item=Model->CreateItem(TEXT("ue_highland_claymore"));Item.Place=1;Item.Cell=6;Item.InstanceId=Identity(Host);State.Items.Add(Item);
    return State;
}
void Select(FColdSteelProfile& State,int32 Phase,bool Host)
{
    State.ActiveWeaponSlot=Phase==4?9:6;
    if(!Host)GuestCreditAtStart=State.OathStaminaRestored;
    if(Phase==2 || Phase==3 || Phase==5)State.Stamina=65.f;
    for(auto& Item:State.Items)if(Item.InstanceId==Identity(Host))
    {
        Item.Place=Phase==4?0:1;Item.Cell=Phase==4?0:6;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_1"),BladeId(Phase,Host));
        Parts->SetStringField(TEXT("guard"),Gale(Phase)?TEXT("highland_gale_wing"):TEXT("factory"));
        if(Oath(Phase))Parts->SetStringField(TEXT("blade_2"),HighlandOathRune::Id);
        Parts->SetStringField(TEXT("pommel"),Gale(Phase)?TEXT("highland_gale_oath"):TEXT("factory"));
        Parts->SetStringField(TEXT("grip"),Phase==2?TEXT("long_twohand"):TEXT("factory"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Item.Data.Reset();FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&Item.Data));
    }
}
void PlaceTarget(AFPSGAMECharacter* Pawn,bool Lethal)
{
    const FVector Forward=Pawn->GetBaseAimRotation().Vector().GetSafeNormal2D();
    Target=KukriCombatWire::SpawnTarget(Pawn->GetWorld(),Pawn->GetActorLocation()+Forward*100.);
    if(Target.IsValid())
    {
        if(Lethal){Target->Health=1.f;Target->ForceNetUpdate();}
        StartingHP=Target->Health;
    }
}
void ObserveJudgment(AFPSGAMECharacter* Pawn)
{
    const auto* Sword=Pawn?Pawn->FindComponentByClass<URuneSwordComponent>():nullptr;
    if(Sword && Sword->OathPresentation().Phase==2)Pawn->Tags.AddUnique(TEXT("HighlandAuditJudgmentSeen"));
}
bool TickGaleAttack(AFPSGAMECharacter* Pawn,int32 Phase)
{
    if(Phase!=2 && Phase!=3)return true;
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();
    if(!Sword)return false;
    const FName Started(Phase==2?TEXT("WireWhirlwindStarted"):TEXT("WireSwingStarted"));
    if(Pawn->ActorHasTag(Started))return true;
    if(!Sword->IsEquipped() || Sword->IsBusy())return false;
    if(Phase==2){if(!Sword->BeginWhirlwind())return false;}
    else {Sword->BeginAttack();if(!Sword->IsBusy())return false;}
    Pawn->Tags.AddUnique(Started);
    return true;
}
bool TickCharge(AFPSGAMECharacter* Pawn,int32 Phase)
{
    // Drive the production input methods on the actual client. The charge and
    // release travel on the weapon component's normal reliable RPC channel.
    static TWeakObjectPtr<AFPSGAMECharacter> Subject;static int32 Stage=0;
    if(Phase!=5||Subject.Get()!=Pawn){Subject=Pawn;Stage=0;if(Phase!=5)return true;}
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();if(!Sword)return false;
    if(Stage==0){Sword->BeginHeavyCharge();if(Sword->IsHeavyCharging())Stage=1;return false;}
    if(Stage==1)
    {
        if(Sword->HeavyChargeFraction()<1.f)return false;
        Sword->ReleaseHeavyCharge();Stage=2;
    }
    return true;
}
bool Check(AFPSGAMECharacter* Pawn,int32 Phase,bool Host,FString& Details)
{
    auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;if(!Body){Details=TEXT("body unavailable");return false;}
    const auto* Property=FindFProperty<FArrayProperty>(Body->GetClass(),TEXT("ReplicatedWeapons"));
    const auto* Weapons=Property?Property->ContainerPtrToValuePtr<TArray<FFPSBodyWeapon>>(Body):nullptr;
    const auto Slots=Catalog()->GetObjectField(TEXT("slots"));
    TArray<FFPSWeatherWeaponMesh> Meshes;Body->GetWeatherWeaponMeshes(Meshes,true);
    int32 Descriptors=0,WorldParts=0;bool Good=Weapons!=nullptr,StatsGood=true;
    for(const TCHAR* Slot:{TEXT("blade_1"),TEXT("pommel"),TEXT("guard")})
    {
        const bool Blade=FCString::Strcmp(Slot,TEXT("blade_1"))==0;
        const bool Guard=FCString::Strcmp(Slot,TEXT("guard"))==0;
        const auto ID=Blade?BladeId(Phase,Host):!Gale(Phase)?TEXT("factory"):Guard?TEXT("highland_gale_wing"):TEXT("highland_gale_oath");
        const auto PartDef=Slots->GetObjectField(Slot)->GetObjectField(ID);
        FString Expected=PartDef->GetStringField(TEXT("mesh"));
        const TSharedPtr<FJsonObject>* Fitted=nullptr;
        if(PartDef->TryGetObjectField(TEXT("mesh_by_blade"),Fitted))(*Fitted)->TryGetStringField(BladeId(Phase,Host),Expected);
        if(Weapons)for(const auto& W:*Weapons)if(W.ItemInstance==Identity(Host))for(const auto& Part:W.Parts)if(Part.Slot==Slot)
        {++Descriptors;Good&=Part.Mesh.ToSoftObjectPath().ToString()==Expected;
         if(Blade)Good&=(Part.RuneId==HighlandOathRune::Id)==Oath(Phase);}
        const FName Tag(*(FString(TEXT("SwordSlot="))+Slot));
        for(const auto& Entry:Meshes)if(Entry.Instance==Identity(Host))if(auto* M=Cast<UStaticMeshComponent>(Entry.Mesh);M&&M->ComponentHasTag(Tag))
        {
            ++WorldParts;Good&=M->GetStaticMesh()&&M->GetStaticMesh()->GetPathName()==Expected;
            if(Blade)
            {
                bool Gold=false;
                for(int32 I=0;I<M->GetNumMaterials();++I)
                    if(auto* Overlay=M->GetOverlayMaterial(true,I))
                        Gold|=Overlay->GetBaseMaterial()->GetName()==TEXT("M_SilverRuneSurface_HighlandOath");
                Good&=Gold==Oath(Phase);
            }
        }
    }
    // Authority uses the remote shadow; the owner uses its local mirror.
    // An observer has no gameplay profile for the other pawn and checks only the replicated equipment.
    if(Pawn->HasAuthority()||Pawn->IsLocallyControlled())
    {
        const auto* Model=ColdSteelAuthority::ForPawn(Pawn);const auto* Item=Model?Model->Equipped():nullptr;
        if(Phase==4)StatsGood=Model&&!Item;
        else if(Item)
        {
            const auto S=ColdSteelMelee::Evaluate(*Item,Model);
            StatsGood=FMath::IsNearlyEqual(S.Modifiers.SprintStamina,Gale(Phase)?.85*.9:1.,.001)&&
                FMath::IsNearlyEqual(S.Modifiers.HeavyChargeSpeedBonus,Gale(Phase)?.2:0.,.001)&&
                FMath::IsNearlyEqual(S.Modifiers.Range,(Ridge(Phase)?1.25:1.)*(Phase==2?1.1:1.),.001);
        }
        else StatsGood=false;
    }
    bool ReleaseOK=true;
    if(Phase==5&&Pawn->HasAuthority()&&!Pawn->IsLocallyControlled())
    {
        const FName Paid(TEXT("HighlandAuditHeavyPaid"));
        const auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();
        if(Sword&&Sword->IsNetworkHeavyReleaseWindowOpen(Identity(Host)))Pawn->Tags.AddUnique(Paid);
        ReleaseOK=Pawn->ActorHasTag(Paid);
    }
    const auto* AuthorityOrOwner=Pawn->HasAuthority()||Pawn->IsLocallyControlled()?ColdSteelAuthority::ForPawn(Pawn):nullptr;
    const double Credit=AuthorityOrOwner?AuthorityOrOwner->Snapshot().OathStaminaRestored:0.;
    if(!Host && (Phase==2 || Phase==3))
    {
        const auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();
        const auto* Status=Pawn->FindComponentByClass<UStatusEffectsComponent>();
        const bool Visible=Status && Status->Snapshot().ContainsByPredicate([](const FStatusEffectView& V)
            {return V.Type==TEXT("galeSwiftness") && V.Remaining>0.f && V.Remaining<=3.05f && FMath::IsNearlyEqual(V.Duration,3.f);});
        if(Sword && Visible && FMath::IsNearlyEqual(Sword->GaleMoveScale(),1.25f))
            Pawn->Tags.AddUnique(Phase==2?TEXT("WireWhirlwindSwift"):TEXT("WireSwingSwift"));
        ReleaseOK=Pawn->ActorHasTag(Phase==2?TEXT("WireWhirlwindSwift"):TEXT("WireSwingSwift"));
        if(AuthorityOrOwner)
        {
            const float Cost=Phase==2?AuthorityOrOwner->WhirlwindStats().StaminaCost:
                ColdSteelMelee::AttackStamina(AuthorityOrOwner->Equipped(),AuthorityOrOwner);
            ReleaseOK&=Cost>0.f && FMath::IsNearlyEqual(Credit-GuestCreditAtStart,double(Cost),.01);
        }
        if(Pawn->HasAuthority())ReleaseOK&=StartingHP==1.f && (!Target.IsValid() || Target->Health<=0.f);
    }
    if(Phase==5)
    {
        ReleaseOK&=Pawn->ActorHasTag(TEXT("HighlandAuditJudgmentSeen"));
        if(!Host && AuthorityOrOwner)
        {
            const auto* Equipped=AuthorityOrOwner->Equipped();
            ReleaseOK&=Equipped && FMath::IsNearlyEqual(Credit-GuestCreditAtStart,double(ColdSteelMelee::HeavyReleaseStamina(Equipped,AuthorityOrOwner))*.25,.002);
            if(Pawn->HasAuthority())ReleaseOK&=Target.IsValid()&&Target->Health<StartingHP;
        }
    }
    Details=FString::Printf(TEXT("highland phase=%d local=%d descriptors=%d world_parts=%d paths=%d stats=%d release_rpc=%d refund=%.3f target_loss=%.2f"),Phase,Pawn->IsLocallyControlled(),Descriptors,WorldParts,Good,StatsGood,ReleaseOK,Credit,Target.IsValid()?StartingHP-Target->Health:0.f);
    return StatsGood&&ReleaseOK&&(Phase==4?Descriptors==0&&WorldParts==0:Descriptors==3&&WorldParts==3&&Good);
}
}
