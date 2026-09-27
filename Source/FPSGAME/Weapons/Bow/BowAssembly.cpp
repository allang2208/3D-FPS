#include "BowAssembly.h"
#include "../../UI/ColdSteelInventoryTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/MaterialInterface.h"
#include "Serialization/JsonSerializer.h"

namespace
{
const FName RootTag(TEXT("BowAssembly")),PartTag(TEXT("BowAssemblyPart"));
const TCHAR* Slots[]={TEXT("riser"),TEXT("grip"),TEXT("arrow_rest"),TEXT("sight"),TEXT("string")};
const TCHAR* Cylinder=TEXT("/Engine/BasicShapes/Cylinder.Cylinder");
FString Field(const TCHAR* Slot,const TCHAR* Suffix){return FString::Printf(TEXT("bow_part_%s_%s"),Slot,Suffix);}
FString Text(const FColdSteelItem& I,const TCHAR* Slot,const TCHAR* Suffix){return ColdSteelInventory::Text(I,*Field(Slot,Suffix));}
FVector Vector(const FColdSteelItem& I,const TCHAR* Key,FVector Default=FVector::ZeroVector)
{
    TArray<FString> Values;ColdSteelInventory::Text(I,Key).ParseIntoArray(Values,TEXT(","),false);
    return Values.Num()==3?FVector(FCString::Atod(*Values[0]),FCString::Atod(*Values[1]),FCString::Atod(*Values[2])):Default;
}
}
bool ColdSteelBowAssembly::IsBowRoot(const UStaticMeshComponent* Root){return Root&&Root->ComponentHasTag(RootTag);}
FString ColdSteelBowAssembly::Key(const FColdSteelItem& I)
{
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data);
    TArray<FString> Keys;if(Data)for(const auto& P:Data->Values)
    {
        const FString K(*P.Key);
        if(K.StartsWith(TEXT("bow_part_"))||K==TEXT("nock_upper_cm")||K==TEXT("nock_lower_cm")||K==TEXT("brace_nock_cm"))Keys.Add(K);
    }
    Keys.Sort();auto Visual=MakeShared<FJsonObject>();for(const auto& K:Keys)Visual->SetField(K,Data->Values.FindChecked(*K));
    FString Encoded;FJsonSerializer::Serialize(Visual,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Encoded));
    return TEXT("bow-v15|")+I.Definition+TEXT("|")+Encoded;
}
void ColdSteelBowAssembly::GatherResources(const FColdSteelItem& I,TArray<FSoftObjectPath>& Out)
{
    for(const TCHAR* Slot:Slots)for(const TCHAR* Suffix:{TEXT("mesh"),TEXT("material")})
    {const FString Path=Text(I,Slot,Suffix);if(!Path.IsEmpty())Out.AddUnique(FSoftObjectPath(Path));}
    if(Text(I,TEXT("string"),TEXT("mesh")).IsEmpty())Out.AddUnique(FSoftObjectPath(Cylinder));
}
TArray<UMeshComponent*> ColdSteelBowAssembly::Components(UStaticMeshComponent* Root)
{
    TArray<UMeshComponent*> Result;if(!Root)return Result;
    if(Root->GetStaticMesh())Result.Add(Root);
    for(USceneComponent* C:Root->GetAttachChildren())if(C&&C->ComponentHasTag(PartTag))
    {
        if(auto* Part=Cast<UStaticMeshComponent>(C);Part&&Part->GetStaticMesh())Result.Add(Part);
        else if(auto* Skin=Cast<USkinnedMeshComponent>(C);Skin&&Skin->GetSkinnedAsset())Result.Add(Skin);
    }
    return Result;
}
void ColdSteelBowAssembly::Clear(UStaticMeshComponent* Root)
{
    if(!Root)return;const auto Children=Root->GetAttachChildren();
    for(USceneComponent* C:Children)if(C&&C->ComponentHasTag(PartTag))C->DestroyComponent();
    Root->ComponentTags.Remove(RootTag);
}
FBox ColdSteelBowAssembly::LocalBounds(UStaticMeshComponent* Root)
{
    FBox Box(ForceInit);
    for(auto* C:Components(Root))Box+=C->CalcBounds(C==Root?FTransform::Identity:C->GetRelativeTransform()).GetBox();
    return Box;
}
FQuat ColdSteelBowAssembly::Rotation()
{
    // Horizontal bow, arc above the string; view the side carrying the sight.
    return FRotationMatrix::MakeFromXZ(FVector::UpVector,FVector::RightVector).ToQuat();
}
bool ColdSteelBowAssembly::Apply(UStaticMeshComponent* Root,const FColdSteelItem& I)
{
    if(!Root)return false;
    TArray<FSoftObjectPath> Required;GatherResources(I,Required);
    for(const auto& P:Required)if(!P.ResolveObject())return false;
    auto Mesh=[&](const TCHAR* Slot){return FSoftObjectPath(Text(I,Slot,TEXT("mesh"))).ResolveObject();};
    UObject* Body=Mesh(TEXT("riser"));
    if(!Cast<UStaticMesh>(Body)&&!Cast<USkeletalMesh>(Body))return false;
    Clear(Root);Root->ComponentTags.AddUnique(RootTag);Root->EmptyOverrideMaterials();Root->SetStaticMesh(Cast<UStaticMesh>(Body));
    Root->SetVisibility(true);Root->SetCollisionEnabled(ECollisionEnabled::NoCollision);Root->SetCanEverAffectNavigation(false);Root->SetForcedLodModel(1);
    auto NewPart=[&](UObject* Asset)->UMeshComponent*
    {
        UMeshComponent* C=nullptr;
        if(auto* Skin=Cast<USkeletalMesh>(Asset))
        {
            auto* P=NewObject<UPoseableMeshComponent>(Root,NAME_None,RF_Transient);
            P->SetSkeletalMesh(Skin);P->SetComponentTickEnabled(false);C=P;
        }
        else
        {
            auto* P=NewObject<UStaticMeshComponent>(Root,NAME_None,RF_Transient);
            P->SetStaticMesh(Cast<UStaticMesh>(Asset));P->SetForcedLodModel(1);C=P;
        }
        C->ComponentTags.Add(PartTag);
        C->SetupAttachment(Root);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCanEverAffectNavigation(false);
        C->RegisterComponentWithWorld(Root->GetWorld());return C;
    };
    auto Material=[&](UMeshComponent* C,const TCHAR* Slot)
    {if(auto* M=Cast<UMaterialInterface>(FSoftObjectPath(Text(I,Slot,TEXT("material"))).ResolveObject()))for(int32 N=0;N<C->GetNumMaterials();++N)C->SetMaterial(N,M);};
    Material(Cast<USkeletalMesh>(Body)?NewPart(Body):Root,TEXT("riser"));
    for(const TCHAR* Slot:Slots)
    {
        if(FCString::Strcmp(Slot,TEXT("riser"))==0)continue;
        if(auto* Asset=Mesh(Slot))
        {
            auto* C=NewPart(Asset);const FVector R=Vector(I,*Field(Slot,TEXT("rotation_deg")));
            C->SetRelativeTransform(FTransform(FRotator(R.X,R.Y,R.Z),Vector(I,*Field(Slot,TEXT("location_cm"))),FVector(ColdSteelInventory::Number(I,*Field(Slot,TEXT("scale")),1))));Material(C,Slot);
        }
    }
    if(!Mesh(TEXT("string")))
    {
        const FVector Nock=Vector(I,TEXT("brace_nock_cm"),FVector(-24,0,1.5));
        const double Radius=ColdSteelInventory::Number(I,TEXT("bow_part_string_radius_cm"),.09);
        for(const TCHAR* Tip:{TEXT("nock_upper_cm"),TEXT("nock_lower_cm")})
        {
            const FVector End=Vector(I,Tip),D=End-Nock;auto* C=NewPart(Cast<UStaticMesh>(FSoftObjectPath(Cylinder).ResolveObject()));
            C->SetRelativeTransform(FTransform(FQuat::FindBetweenNormals(FVector::UpVector,D.GetSafeNormal()),(End+Nock)*.5,FVector(Radius/50,Radius/50,D.Size()/100)));
            Material(C,TEXT("string"));
        }
    }
    return true;
}
