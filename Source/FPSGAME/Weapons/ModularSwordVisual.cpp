#include "ModularSwordVisual.h"
#include "MeleeRuneVisual.h"
#include "FrostSwordRunes.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Crc.h"

namespace
{
const FName PartTag(TEXT("FrostSwordModule"));
const FString KeyPrefix=TEXT("FrostSwordVisual=");
TSharedPtr<FJsonObject> Catalog(const FColdSteelItem& Item)
{
    FString File=ColdSteelInventory::Text(Item,TEXT("modular_sword_catalog"));
    if(File.IsEmpty())File=Item.Definition==TEXT("ue_frost_crystal_sword")?TEXT("frost-sword-modules.json"):
        Item.Definition==TEXT("ue_rune_sword")?TEXT("rune-sword-modules.json"):FString();
    if(File.IsEmpty())return nullptr;
    // The resolved catalog combines shared models with each host's fitting profile.
    static TMap<FString,TSharedPtr<FJsonObject>> SharedSixPartCatalogs;
    if(const auto* Existing=SharedSixPartCatalogs.Find(File))return *Existing;
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/File))||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)return nullptr;
    const TSharedPtr<FJsonObject>* Profile=nullptr;
    if(Root->TryGetObjectField(TEXT("pommel_profile"),Profile))
    {
        FString LibraryFile,Finish;(*Profile)->TryGetStringField(TEXT("library"),LibraryFile);(*Profile)->TryGetStringField(TEXT("finish"),Finish);
        FString LibraryText;TSharedPtr<FJsonObject> Library;
        if(!FFileHelper::LoadFileToString(LibraryText,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/LibraryFile))||
            !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(LibraryText),Library)||!Library)return nullptr;
        const auto Choices=Root->GetObjectField(TEXT("slots"))->GetObjectField(TEXT("pommel"));
        const TSharedPtr<FJsonObject>* Finishes=nullptr,*Theme=nullptr;
        if(Library->TryGetObjectField(TEXT("finishes"),Finishes))(*Finishes)->TryGetObjectField(Finish,Theme);
        for(const auto& Pair:Library->GetObjectField(TEXT("options"))->Values)
        {
            auto Spec=MakeShared<FJsonObject>();Spec->Values=Pair.Value->AsObject()->Values;
            const TSharedPtr<FJsonObject>* Interfaces=nullptr,*Fitting=nullptr;
            FString Interface;Spec->TryGetStringField(TEXT("interface"),Interface);
            if((*Profile)->TryGetObjectField(TEXT("interfaces"),Interfaces))
                (*Interfaces)->TryGetObjectField(Interface,Fitting);
            for(const TCHAR* Field:{TEXT("location_cm"),TEXT("rotation_deg"),TEXT("scale"),TEXT("adapter")})
            {
                if(const auto* Value=(*Profile)->Values.Find(Field))Spec->Values.Add(Field,*Value);
                if(Fitting)if(const auto* Value=(*Fitting)->Values.Find(Field))Spec->Values.Add(Field,*Value);
            }
            const TSharedPtr<FJsonObject>* FinishSpec=nullptr;
            if(Theme&&(*Theme)->TryGetObjectField(Pair.Key,FinishSpec))
                for(const auto& Value:(*FinishSpec)->Values)Spec->Values.Add(Value.Key,Value.Value);
            Choices->SetObjectField(Pair.Key,Spec);
        }
    }
    SharedSixPartCatalogs.Add(File,Root);
    return Root;
}
FVector Vector(const TSharedPtr<FJsonObject>& Obj,const TCHAR* Field,const FVector& Default=FVector::ZeroVector)
{
    const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
    return Obj&&Obj->TryGetArrayField(Field,Values)&&Values->Num()==3?
        FVector((*Values)[0]->AsNumber(),(*Values)[1]->AsNumber(),(*Values)[2]->AsNumber()):Default;
}
FGunsmithParts Installed(const FColdSteelItem& Item,const FGunsmithParts* Draft)
{
    FGunsmithParts Result;TSharedPtr<FJsonObject> Root;const TSharedPtr<FJsonObject>* Parts=nullptr;
    if(Draft)Result=*Draft;
    else if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Root)&&Root&&Root->TryGetObjectField(TEXT("gunsmith_parts"),Parts))
        for(const auto& Pair:(*Parts)->Values){FString Value;if(Pair.Value->TryGetString(Value))Result.Add(FString(*Pair.Key),Value);}
    if(auto* Rune=Result.Find(TEXT("blade_2")))*Rune=ColdSteelFrostRunes::Upgrade(Item.Definition,*Rune);
    return Result;
}
TSharedPtr<FJsonObject> Part(const FColdSteelItem& Item,const TCHAR* Slot,const FGunsmithParts& Parts)
{
    const auto Root=Catalog(Item);const TSharedPtr<FJsonObject>* Slots=nullptr,*Choices=nullptr,*Spec=nullptr;
    if(!Root||!Root->TryGetObjectField(TEXT("slots"),Slots)||!(*Slots)->TryGetObjectField(Slot,Choices))return nullptr;
    const FString Selected=Parts.FindRef(Slot);
    if(!(*Choices)->TryGetObjectField(Selected,Spec)&&!(*Choices)->TryGetObjectField(TEXT("factory"),Spec))return nullptr;
    return *Spec;
}
}

bool ColdSteelModularSword::Supports(const FColdSteelItem& Item)
{return Catalog(Item).IsValid();}

FString ColdSteelModularSword::ArmsMesh(const FColdSteelItem& Item)
{
    FString Path;if(const auto Root=Catalog(Item))Root->TryGetStringField(TEXT("arms_mesh"),Path);return Path;
}

FString ColdSteelModularSword::AnimationFolder(const FColdSteelItem& Item)
{
    FString Path;
    if(Supports(Item))
        if(const auto Grip=Part(Item,TEXT("grip"),Installed(Item,nullptr)))Grip->TryGetStringField(TEXT("animation_folder"),Path);
    return Path.IsEmpty()?ColdSteelInventory::Text(Item,TEXT("animation_folder")):Path;
}

FString ColdSteelModularSword::Key(const FColdSteelItem& Item,const FGunsmithParts* Draft,bool IncludeRune)
{
    if(!Supports(Item))return {};
    const auto Parts=Installed(Item,Draft);FString Result=Item.Definition+TEXT("|")+Catalog(Item)->GetStringField(TEXT("interface"));
    for(const TCHAR* Slot:{TEXT("blade_1"),TEXT("guard"),TEXT("grip"),TEXT("pommel")})
        if(const auto Spec=Part(Item,Slot,Parts))
        {
            FString Settings;FJsonSerializer::Serialize(Spec.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Settings));
            Result+=FString(TEXT("|"))+Slot+TEXT("=")+Parts.FindRef(Slot)+FString::Printf(TEXT(":%08x"),FCrc::StrCrc32(*Settings));
        }
    if(IncludeRune)Result+=TEXT("|rune=")+Parts.FindRef(TEXT("blade_2"));
    if(Item.Definition==ColdSteelFrostRunes::Definition)Result+=TEXT("|innateErosion=spirit20260922");
    if(IncludeRune&&Item.Definition==TEXT("ue_rune_sword")&&Parts.FindRef(TEXT("blade_2"))==TEXT("golden_glow_rune"))
        Result+=TEXT("|nativeInk=20260922-root2");
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
    if(!Blade||!Supports(Item))return false;
    const FString VisualKey=Key(Item,Draft,IncludeRune);
    if(Blade->ComponentHasTag(FName(*(KeyPrefix+VisualKey))))return true;
    const auto Parts=Installed(Item,Draft);
    const FVector PommelOffset=Vector(Part(Item,TEXT("grip"),Parts),TEXT("pommel_offset_cm"));
    struct FInstall {FString Slot;TSharedPtr<FJsonObject> Spec;UStaticMesh* Asset;TMap<FName,UMaterialInterface*> Materials;};
    TArray<FInstall> Plan;
    for(const TCHAR* Slot:{TEXT("blade_1"),TEXT("guard"),TEXT("grip"),TEXT("pommel")})
    {
        const auto Spec=Part(Item,Slot,Parts);if(!Spec)return false;
        auto* Asset=LoadObject<UStaticMesh>(nullptr,*Spec->GetStringField(TEXT("mesh")));if(!Asset)return false;
        Plan.Add({Slot,Spec,Asset,{}});
        const TSharedPtr<FJsonObject>* Adapter=nullptr;
        if(FCString::Strcmp(Slot,TEXT("pommel"))==0&&Spec->TryGetObjectField(TEXT("adapter"),Adapter))
        {
            auto* Mount=LoadObject<UStaticMesh>(nullptr,*(*Adapter)->GetStringField(TEXT("mesh")));if(!Mount)return false;
            Plan.Add({TEXT("pommel_mount"),*Adapter,Mount,{}});
        }
    }
    for(auto& Entry:Plan)
    {
        const TSharedPtr<FJsonObject>* Materials=nullptr;
        if(Entry.Spec->TryGetObjectField(TEXT("materials"),Materials))for(const auto& Pair:(*Materials)->Values)
        {
            auto* Material=LoadObject<UMaterialInterface>(nullptr,*Pair.Value->AsString());if(!Material)return false;
            Entry.Materials.Add(FName(*Pair.Key),Material);
        }
    }
    // Factory parts have no adapter; remove the previous fitting when reverting.
    for(auto* Mesh:Components(Blade))if(Mesh!=Blade&&!Plan.ContainsByPredicate([&](const FInstall& Entry)
        {return Mesh->ComponentHasTag(FName(*(TEXT("SwordSlot=")+Entry.Slot)));}))
    {
        if(auto* Owner=Mesh->GetOwner())Owner->RemoveInstanceComponent(Mesh);
        Mesh->DestroyComponent();
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
            const bool AtPommel=Entry.Slot==TEXT("pommel")||Entry.Slot==TEXT("pommel_mount");
            Mesh->SetRelativeLocation(Vector(Entry.Spec,TEXT("location_cm"))+(AtPommel?PommelOffset:FVector::ZeroVector));
            const FVector Rotation=Vector(Entry.Spec,TEXT("rotation_deg"));
            Mesh->SetRelativeRotation(FRotator(Rotation.X,Rotation.Y,Rotation.Z));
            Mesh->SetRelativeScale3D(Vector(Entry.Spec,TEXT("scale"),FVector(1)));
            Mesh->SetVisibility(Blade->IsVisible());Mesh->SetHiddenInGame(Blade->bHiddenInGame);
        }
        if(Mesh->GetStaticMesh()!=Entry.Asset){Mesh->EmptyOverrideMaterials();Mesh->SetStaticMesh(Entry.Asset);}
        if(Entry.Slot==TEXT("pommel")||!Entry.Materials.IsEmpty())Mesh->EmptyOverrideMaterials();
        for(const auto& Pair:Entry.Materials)
        {
            const int32 Index=Mesh->GetMaterialIndex(Pair.Key);
            if(Index!=INDEX_NONE)Mesh->SetMaterial(Index,Pair.Value);
        }
    }
    ColdSteelMeleeRune::Apply(Blade,IncludeRune?Parts.FindRef(TEXT("blade_2")):FString(),Item.Definition);
    if(Item.Definition==TEXT("ue_rune_sword"))
        for(auto* Module:Components(Blade))if(Module->ComponentHasTag(TEXT("SwordSlot=guard")))
            ColdSteelMeleeRune::Apply(Module,IncludeRune&&Parts.FindRef(TEXT("blade_2"))==TEXT("golden_glow_rune")?
                TEXT("golden_glow_rune"):FString(),Item.Definition);
    bool TraceFromAnimation=false;Catalog(Item)->TryGetBoolField(TEXT("trace_from_animation"),TraceFromAnimation);
    const FName TraceTag(TEXT("SwordTraceFromAnimation"));
    if(TraceFromAnimation)Blade->ComponentTags.AddUnique(TraceTag);else Blade->ComponentTags.Remove(TraceTag);
    const auto Spec=Part(Item,TEXT("blade_1"),Parts);
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

FTransform ColdSteelModularSword::BoneMount(const FColdSteelItem& Item)
{
    const TSharedPtr<FJsonObject>* Mount=nullptr;const TArray<TSharedPtr<FJsonValue>>* Q=nullptr;
    const auto Root=Catalog(Item);
    if(!Root||!Root->TryGetObjectField(TEXT("bone_mount"),Mount)||!(*Mount)->TryGetArrayField(TEXT("rotation_xyzw"),Q)||Q->Num()!=4)return FTransform::Identity;
    return FTransform(FQuat((*Q)[0]->AsNumber(),(*Q)[1]->AsNumber(),(*Q)[2]->AsNumber(),(*Q)[3]->AsNumber()).GetNormalized(),Vector(*Mount,TEXT("location_cm")),Vector(*Mount,TEXT("scale"),FVector(1)));
}

FVector ColdSteelModularSword::BladePoint(const FColdSteelItem& Item,bool Tip)
{return Vector(Part(Item,TEXT("blade_1"),Installed(Item,nullptr)),Tip?TEXT("trace_tip_cm"):TEXT("trace_base_cm"),FVector(0,0,Tip?80.6:3));}

FString ColdSteelModularSword::Appearance(const FColdSteelItem& Item,const FString& Slot,const FString& Option)
{
    if(!Supports(Item))return {};
    const bool Factory=Option.IsEmpty()||Option==TEXT("false")||Option==TEXT("factory");
    if(Slot==TEXT("blade_2"))return Factory?TEXT("保留原有刃面纹样"):TEXT("剑刃表面符文");
    const TSharedPtr<FJsonObject>* Slots=nullptr,*Choices=nullptr,*Spec=nullptr;
    const auto Root=Catalog(Item);
    const bool HasMesh=Root->TryGetObjectField(TEXT("slots"),Slots)&&(*Slots)->TryGetObjectField(Slot,Choices)&&
        (*Choices)->TryGetObjectField(Factory?TEXT("factory"):Option,Spec);
    if(!HasMesh)return TEXT("原装外形 · 数值改造");
    FString Label;if((*Spec)->TryGetStringField(TEXT("appearance"),Label))return Label;
    return Factory?TEXT("原装独立部件"):TEXT("可替换独立部件");
}
