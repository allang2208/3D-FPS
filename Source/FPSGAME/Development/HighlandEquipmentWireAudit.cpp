#include "HighlandEquipmentWireAudit.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Weapons/MeleeWeaponStats.h"
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
    for(auto& Item:State.Items)if(Item.InstanceId==Identity(Host))
    {
        Item.Place=Phase==4?0:1;Item.Cell=Phase==4?0:6;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_1"),Ridge(Phase)?TEXT("highland_ridge_piercer"):TEXT("factory"));
        Parts->SetStringField(TEXT("pommel"),Gale(Phase)?TEXT("highland_gale_oath"):TEXT("factory"));
        Parts->SetStringField(TEXT("grip"),Phase==2?TEXT("long_twohand"):TEXT("factory"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Item.Data.Reset();FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&Item.Data));
    }
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
    for(const TCHAR* Slot:{TEXT("blade_1"),TEXT("pommel")})
    {
        const bool Blade=FCString::Strcmp(Slot,TEXT("blade_1"))==0;
        const auto ID=Blade?(Ridge(Phase)?TEXT("highland_ridge_piercer"):TEXT("factory")):(Gale(Phase)?TEXT("highland_gale_oath"):TEXT("factory"));
        const FString Expected=Slots->GetObjectField(Slot)->GetObjectField(ID)->GetStringField(TEXT("mesh"));
        if(Weapons)for(const auto& W:*Weapons)if(W.ItemInstance==Identity(Host))for(const auto& Part:W.Parts)if(Part.Slot==Slot)
        {++Descriptors;Good&=Part.Mesh.ToSoftObjectPath().ToString()==Expected;}
        const FName Tag(*(FString(TEXT("SwordSlot="))+Slot));
        for(const auto& Entry:Meshes)if(Entry.Instance==Identity(Host))if(auto* M=Cast<UStaticMeshComponent>(Entry.Mesh);M&&M->ComponentHasTag(Tag))
        {++WorldParts;Good&=M->GetStaticMesh()&&M->GetStaticMesh()->GetPathName()==Expected;}
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
            StatsGood=FMath::IsNearlyEqual(S.Modifiers.SprintStamina,Gale(Phase)?.85:1.,.001)&&
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
    Details=FString::Printf(TEXT("highland phase=%d local=%d descriptors=%d world_parts=%d paths=%d stats=%d release_rpc=%d"),Phase,Pawn->IsLocallyControlled(),Descriptors,WorldParts,Good,StatsGood,ReleaseOK);
    return StatsGood&&ReleaseOK&&(Phase==4?Descriptors==0&&WorldParts==0:Descriptors==2&&WorldParts==2&&Good);
}
}
