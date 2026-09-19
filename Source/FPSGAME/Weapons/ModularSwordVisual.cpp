#include "ModularSwordVisual.h"
#include "MeleeRuneVisual.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
const FName PartTag(TEXT("FrostSwordModule"));
const FString KeyPrefix=TEXT("FrostSwordVisual=");
const TSharedPtr<FJsonObject>& Catalog()
{
    static const TSharedPtr<FJsonObject> Data=[](){
        FString Text;TSharedPtr<FJsonObject> Root;
        if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/frost-sword-modules.json"))))
            FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root);
        return Root;
    }();
    return Data;
}
FVector Vector(const TSharedPtr<FJsonObject>& Obj,const TCHAR* Field,const FVector& Default=FVector::ZeroVector)
{
    const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
    return Obj&&Obj->TryGetArrayField(Field,Values)&&Values->Num()==3?
        FVector((*Values)[0]->AsNumber(),(*Values)[1]->AsNumber(),(*Values)[2]->AsNumber()):Default;
}
FGunsmithParts Installed(const FColdSteelItem& Item,const FGunsmithParts* Draft)
{
    if(Draft)return *Draft;
    FGunsmithParts Result;TSharedPtr<FJsonObject> Root;const TSharedPtr<FJsonObject>* Parts=nullptr;
    if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Root)&&Root&&Root->TryGetObjectField(TEXT("gunsmith_parts"),Parts))
        for(const auto& Pair:(*Parts)->Values){FString Value;if(Pair.Value->TryGetString(Value))Result.Add(FString(*Pair.Key),Value);}
    return Result;
}
TSharedPtr<FJsonObject> Part(const TCHAR* Slot,const FGunsmithParts& Parts)
{
    const auto& Root=Catalog();const TSharedPtr<FJsonObject>* Slots=nullptr,*Choices=nullptr,*Spec=nullptr;
    if(!Root||!Root->TryGetObjectField(TEXT("slots"),Slots)||!(*Slots)->TryGetObjectField(Slot,Choices))return nullptr;
    const FString Selected=Parts.FindRef(Slot);
    if(!(*Choices)->TryGetObjectField(Selected,Spec)&&!(*Choices)->TryGetObjectField(TEXT("factory"),Spec))return nullptr;
    return *Spec;
}
}

bool ColdSteelModularSword::Supports(const FColdSteelItem& Item)
{return Item.Definition==TEXT("ue_frost_crystal_sword");}

FString ColdSteelModularSword::ArmsMesh(const FColdSteelItem& Item)
{
    FString Path;if(Supports(Item)&&Catalog())Catalog()->TryGetStringField(TEXT("arms_mesh"),Path);return Path;
}

FString ColdSteelModularSword::AnimationFolder(const FColdSteelItem& Item)
{
    FString Path;
    if(Supports(Item))
        if(const auto Grip=Part(TEXT("grip"),Installed(Item,nullptr)))Grip->TryGetStringField(TEXT("animation_folder"),Path);
    return Path.IsEmpty()?ColdSteelInventory::Text(Item,TEXT("animation_folder")):Path;
}

FString ColdSteelModularSword::Key(const FColdSteelItem& Item,const FGunsmithParts* Draft,bool IncludeRune)
{
    if(!Supports(Item))return {};
    const auto Parts=Installed(Item,Draft);FString Result=TEXT("frost_hilt_v1");
    for(const TCHAR* Slot:{TEXT("blade_1"),TEXT("guard"),TEXT("grip"),TEXT("pommel")})
        if(const auto Spec=Part(Slot,Parts))Result+=FString(TEXT("|"))+Slot+TEXT("=")+Spec->GetStringField(TEXT("mesh"));
    if(IncludeRune)Result+=TEXT("|rune=")+Parts.FindRef(TEXT("blade_2"));
    return Result;
}

TArray<UStaticMeshComponent*> ColdSteelModularSword::Components(UStaticMeshComponent* Blade)
{
    TArray<UStaticMeshComponent*> Result;if(!Blade)return Result;Result.Add(Blade);
    for(const auto& Child:Blade->GetAttachChildren())
        if(auto* Mesh=Cast<UStaticMeshComponent>(Child.Get());Mesh&&Mesh->ComponentHasTag(PartTag))Result.Add(Mesh);
    return Result;
}

void ColdSteelModularSword::Clear(UStaticMeshComponent* Blade)
{
    if(!Blade)return;
    for(auto* Mesh:Components(Blade))if(Mesh!=Blade){if(auto* Owner=Mesh->GetOwner())Owner->RemoveInstanceComponent(Mesh);Mesh->DestroyComponent();}
    Blade->ComponentTags.RemoveAll([](FName Tag){return Tag.ToString().StartsWith(KeyPrefix);});
}

bool ColdSteelModularSword::Apply(UStaticMeshComponent* Blade,const FColdSteelItem& Item,const FGunsmithParts* Draft,bool IncludeRune)
{
    if(!Blade||!Supports(Item)||!Catalog())return false;
    const FString VisualKey=Key(Item,Draft,IncludeRune);
    if(Blade->ComponentHasTag(FName(*(KeyPrefix+VisualKey))))return true;
    const auto Parts=Installed(Item,Draft);
    const FVector PommelOffset=Vector(Part(TEXT("grip"),Parts),TEXT("pommel_offset_cm"));
    struct FInstall {FString Slot;TSharedPtr<FJsonObject> Spec;UStaticMesh* Asset;};
    TArray<FInstall> Plan;
    for(const TCHAR* Slot:{TEXT("blade_1"),TEXT("guard"),TEXT("grip"),TEXT("pommel")})
    {
        const auto Spec=Part(Slot,Parts);if(!Spec)return false;
        auto* Asset=LoadObject<UStaticMesh>(nullptr,*Spec->GetStringField(TEXT("mesh")));if(!Asset)return false;
        Plan.Add({Slot,Spec,Asset});
    }
    for(const auto& Entry:Plan)
    {
        UStaticMeshComponent* Mesh=Blade;
        if(Entry.Slot!=TEXT("blade_1"))
        {
            const FName SlotTag(*(TEXT("SwordSlot=")+Entry.Slot));Mesh=nullptr;
            for(auto* Child:Components(Blade))if(Child!=Blade&&Child->ComponentHasTag(SlotTag)){Mesh=Child;break;}
            if(!Mesh)
            {
                Mesh=NewObject<UStaticMeshComponent>(Blade,NAME_None,RF_Transient);
                if(auto* Owner=Mesh->GetOwner())Owner->AddInstanceComponent(Mesh);
                Mesh->ComponentTags.Add(PartTag);Mesh->ComponentTags.Add(SlotTag);
                Mesh->SetupAttachment(Blade);Mesh->SetMobility(EComponentMobility::Movable);
                Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCanEverAffectNavigation(false);
                Mesh->SetOnlyOwnerSee(Blade->bOnlyOwnerSee);Mesh->SetOwnerNoSee(Blade->bOwnerNoSee);
                Mesh->SetCastShadow(Blade->CastShadow);Mesh->bReceivesDecals=Blade->bReceivesDecals;
                Mesh->SetForcedLodModel(Blade->GetForcedLodModel());
                Mesh->RegisterComponentWithWorld(Blade->GetWorld());
            }
            Mesh->SetRelativeLocation(Vector(Entry.Spec,TEXT("location_cm"))+(Entry.Slot==TEXT("pommel")?PommelOffset:FVector::ZeroVector));
            Mesh->SetRelativeRotation(FRotator::ZeroRotator);Mesh->SetRelativeScale3D(FVector(1));
            Mesh->SetVisibility(Blade->IsVisible());Mesh->SetHiddenInGame(Blade->bHiddenInGame);
        }
        if(Mesh->GetStaticMesh()!=Entry.Asset){Mesh->EmptyOverrideMaterials();Mesh->SetStaticMesh(Entry.Asset);}
    }
    ColdSteelMeleeRune::Apply(Blade,IncludeRune?Parts.FindRef(TEXT("blade_2")):FString());
    const auto Spec=Part(TEXT("blade_1"),Parts);
    for(int32 Slot=0;Slot<Blade->GetNumMaterials();++Slot)
        if(auto* M=Cast<UMaterialInstanceDynamic>(Blade->GetOverlayMaterial(true,Slot)))
        {const FVector D=Vector(Spec,TEXT("rune_dimensions_cm"),FVector(12,10,63));M->SetVectorParameterValue(TEXT("Dimensions"),FLinearColor(D.X,D.Y,D.Z,0));}
    Blade->ComponentTags.RemoveAll([](FName Tag){return Tag.ToString().StartsWith(KeyPrefix);});
    Blade->ComponentTags.Add(FName(*(KeyPrefix+VisualKey)));return true;
}

FBox ColdSteelModularSword::LocalBounds(UStaticMeshComponent* Blade)
{
    FBox Bounds(ForceInit);
    for(auto* M:Components(Blade))if(M->GetStaticMesh())
        Bounds+=M->GetStaticMesh()->GetBoundingBox().TransformBy(M==Blade?FTransform::Identity:M->GetRelativeTransform());
    return Bounds;
}

FTransform ColdSteelModularSword::BoneMount()
{
    const TSharedPtr<FJsonObject>* Mount=nullptr;const TArray<TSharedPtr<FJsonValue>>* Q=nullptr;
    if(!Catalog()||!Catalog()->TryGetObjectField(TEXT("bone_mount"),Mount)||!(*Mount)->TryGetArrayField(TEXT("rotation_xyzw"),Q)||Q->Num()!=4)return FTransform::Identity;
    return FTransform(FQuat((*Q)[0]->AsNumber(),(*Q)[1]->AsNumber(),(*Q)[2]->AsNumber(),(*Q)[3]->AsNumber()).GetNormalized(),Vector(*Mount,TEXT("location_cm")),Vector(*Mount,TEXT("scale"),FVector(1)));
}

FVector ColdSteelModularSword::BladePoint(const FColdSteelItem& Item,bool Tip)
{return Vector(Part(TEXT("blade_1"),Installed(Item,nullptr)),Tip?TEXT("trace_tip_cm"):TEXT("trace_base_cm"),FVector(0,0,Tip?80.6:3));}
