// Seven phases run on the existing listen-server, owner, observer and reconnect fixture.
namespace ForgedSwordEquipmentWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("ForgedSwordEquipmentWireAudit"));}
const TCHAR* Identity(bool Host){return Host?TEXT("ForgedWire_Host"):TEXT("ForgedWire_Guest");}
const TCHAR* Cases[]={TEXT("late_join_existing_chain"),TEXT("swap_blades_only"),TEXT("long_grip_and_chain"),
    TEXT("restore_factory_pommel"),TEXT("unequip"),TEXT("reequip"),TEXT("reconnect_retained_parts")};
bool Chain(int32 Phase,bool Host){return Phase!=3&&(Phase>=2||Host);}
bool Hollow(int32 Phase,bool Host){return (Phase==1||Phase==3)?!Host:Host;}
bool LongGrip(int32 Phase){return Phase==2;}
FColdSteelProfile Seed(UColdSteelStatusModel* Model,bool Host)
{
    auto State=Model->Snapshot();State.Items.Reset();State.ActiveProductionTool.Reset();State.ActiveWeaponSlot=6;
    auto Item=Model->CreateItem(TEXT("ue_forged_steel_greatsword"));
    Item.InstanceId=Identity(Host);Item.Place=1;Item.Cell=6;State.Items.Add(MoveTemp(Item));return State;
}
void Select(FColdSteelProfile& State,int32 Phase,bool Host)
{
    for(auto& Item:State.Items)if(Item.InstanceId==Identity(Host))
    {
        Item.Place=Phase==4?0:1;Item.Cell=Phase==4?0:6;
        TSharedPtr<FJsonObject> Data;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return;
        auto Parts=MakeShared<FJsonObject>();
        Parts->SetStringField(TEXT("blade_1"),Hollow(Phase,Host)?TEXT("hollow_blade"):TEXT("executioner_blade"));
        Parts->SetStringField(TEXT("pommel"),Chain(Phase,Host)?TEXT("ring_chain_pommel"):TEXT("factory"));
        Parts->SetStringField(TEXT("grip"),LongGrip(Phase)?TEXT("long_twohand"):TEXT("factory"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Item.Data.Reset();
        FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
    }
}
bool Check(AFPSGAMECharacter* Pawn,int32 Phase,bool Host,FString& Details)
{
    auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    if(!Body){Details=TEXT("missing body");return false;}
    const bool ExpectedChain=Chain(Phase,Host);
    const FName Blade=Hollow(Phase,Host)?TEXT("SM_ForgedSteelGreatsword_HollowBlade"):TEXT("SM_ForgedSteelGreatsword_ExecutionerBlade");
    const FName Pommel=ExpectedChain?TEXT("SM_ForgedSteelGreatsword_RingChainPommel"):TEXT("SM_ForgedSteelGreatsword_Pommel_V1");
    const FName Grip=LongGrip(Phase)?TEXT("SM_ForgedSteelGreatsword_Grip_long_twohand_V2"):TEXT("SM_ForgedSteelGreatsword_Grip_V1");
    TArray<FFPSWeatherWeaponMesh> Meshes;Body->GetWeatherWeaponMeshes(Meshes,true);
    int32 Blades=0,Pommels=0,Grips=0,Parts=0;bool Dynamics=false;
    for(const auto& Entry:Meshes)
    {
        if(Entry.Instance!=Identity(Host))continue;
        const auto* Mesh=Cast<UStaticMeshComponent>(Entry.Mesh);
        if(!Mesh||!Mesh->GetStaticMesh())continue;
        ++Parts;const FName Name=Mesh->GetStaticMesh()->GetFName();
        if(Name==Blade&&Mesh->ComponentHasTag(TEXT("SwordSlot=blade_1")))++Blades;
        if(Name==Grip&&Mesh->ComponentHasTag(TEXT("SwordSlot=grip")))++Grips;
        if(Name==Pommel&&Mesh->ComponentHasTag(TEXT("SwordSlot=pommel")))
        {
            ++Pommels;const auto* Tail=Cast<USwordTasselMeshComponent>(Mesh);
            float Active=0.f;
            auto* Material=Mesh->GetMaterial(1);
            Dynamics=ExpectedChain?(Tail&&Tail->IsComponentTickEnabled()&&Material&&
                Material->GetScalarParameterValue(FMaterialParameterInfo(TEXT("TasselActive")),Active)&&Active>.99f):!Tail;
        }
    }
    Details=FString::Printf(TEXT("instance=%s local=%d parts=%d matched_blade=%d grip=%d pommel=%d dynamics_ok=%d"),
        Identity(Host),Pawn->IsLocallyControlled(),Parts,Blades,Grips,Pommels,Dynamics);
    return Phase==4?Parts==0:Blades==1&&Grips==1&&Pommels==1&&Dynamics;
}
}
