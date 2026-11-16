#include "UnknownHumanoid.h"
#include "UnknownHumanoidAnimInstance.h"
#include "../Characters/FPSModularOutfitComponent.h"
#include "../Characters/FPSPlayerBodyGrip.h"
#include "../Characters/FPSBodyStaffGrip.h"
#include "../Characters/FPSBodyKukriGripData.h"
#include "../Characters/FPSBodyKukriDualGripData.h"
#include "../Weapons/Bow/BowAssembly.h"
#include "../Weapons/Bow/BowFlexMeshComponent.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/FPSBallisticsComponent.h"
#include "../Weapons/FPSWeaponFXComponent.h"
#include "../Combat/RangedAttackQuery.h"
#include "Animation/Skeleton.h"
#include "Components/CapsuleComponent.h"
#include "../Characters/FPSPlayerHeadAnimInstance.h"
#include "../Characters/FPSBodyHeadGrooms.h"
#include "../Skills/FPSFireballComponent.h"
#include "../UI/ColdSteelPickup.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/Staff/StaffAssembly.h"
#include "../Weapons/Staff/StaffGripPose.h"
#include "../Weapons/Spellbook/SpellbookBookOrientation.h"
#include "Animation/AnimSequence.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "PhysicsEngine/PhysicsAsset.h"

namespace UnknownAppearance
{
    using FObject = TSharedPtr<FJsonObject>;
    constexpr const TCHAR* FlashPath=TEXT("/Game/Weapons/GunplayFX/NS_FPS_MuzzleFlashV10.NS_FPS_MuzzleFlashV10");
    const FObject& PlayerRecipe()
    {
        static const FObject Recipe = [] {
            FString Text;
            FObject Root;
            if (FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json"))))
                FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root);
            return Root;
        }();
        return Recipe;
    }

    FObject Object(const FObject& Parent,const FString& Key)
    {
        const FObject* Value = nullptr;
        return Parent && Parent->TryGetObjectField(Key,Value) ? *Value : nullptr;
    }
    FString String(const FObject& Parent,const FString& Key)
    {
        FString Out;
        if (Parent) Parent->TryGetStringField(Key,Out);
        return Out;
    }
    FVector Vector(const FObject& Parent,const TCHAR* Key,FVector Fallback)
    {
        const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
        if (Parent && Parent->TryGetArrayField(Key,Values) && Values->Num()==3)
            return FVector((*Values)[0]->AsNumber(),(*Values)[1]->AsNumber(),(*Values)[2]->AsNumber());
        return Fallback;
    }
    template<class T> T* Asset(const FString& Path)
    {
        return Path.IsEmpty() ? nullptr : Cast<T>(FSoftObjectPath(Path).ResolveObject());
    }
    struct FAppearance
    {
        FObject Head, Headwear;
        TArray<FObject> Grooms;
        int32 ScalpStart=0;
        TMap<FName,FString> Animations;
        FString Body, Weapon, HeldRig, HeldIdle, BookMesh,BladeRig,BladeMesh;
        TArray<FSoftObjectPath> Paths;
        void Add(const FString& Path)
        {
            if (!Path.IsEmpty()) Paths.AddUnique(FSoftObjectPath(Path));
        }
        void AddGrooms(const FObject& Parent)
        {
            const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
            if (!Parent || !Parent->TryGetArrayField(TEXT("grooms"),Rows)) return;
            for (const auto& Value : *Rows)
            {
                const auto Groom = Value->AsObject();
                if (!Groom) continue;
                Grooms.Add(Groom);
                Add(String(Groom,TEXT("asset")));
                Add(String(Groom,TEXT("binding")));
                const TArray<TSharedPtr<FJsonValue>>* Materials = nullptr;
                if (Groom->TryGetArrayField(TEXT("materials"),Materials))
                    for (const auto& Material : *Materials) Add(Material->AsString());
            }
        }
        FAppearance(const FUnknownLoadout& Gear,const FColdSteelItem& Item,const FColdSteelItem& Offhand)
        {
            const auto& Root = PlayerRecipe();
            const auto Variant = Object(Object(Root,TEXT("body_variants")),Gear.Body.ToString());
            const auto Selected = Variant ? Variant : Root;
            Body = String(Selected,TEXT("body_mesh"));
            Head = Object(Object(Selected,TEXT("heads")),Gear.Body.ToString());
            Add(Body);
            Add(String(Head,TEXT("mesh")));
            if (const auto Materials=Object(Head,TEXT("materials")))
                for (const auto& Pair : Materials->Values) Add(Pair.Value->AsString());
            for (const auto& Slot : Gear.Outfit)
                if (Slot.Slot==1) Headwear=Object(Object(Selected,TEXT("head_equipment")),Slot.Definition.ToString());
            Add(String(Headwear,TEXT("static_mesh")));
            Add(String(Headwear,TEXT("skeletal_mesh")));
            bool CoversHair = false;
            if (Headwear) Headwear->TryGetBoolField(TEXT("covers_scalp_hair"),CoversHair);
            AddGrooms(Head);
            ScalpStart=Grooms.Num();
            if (!CoversHair) AddGrooms(Object(Object(Head,TEXT("hair_styles")),String(Head,TEXT("default_hair"))));
            Weapon = ColdSteelInventory::Text(Item,TEXT("world_mesh"));
            Add(Weapon);
            if (Gear.Role==EUnknownRole::Bow)
            {
                ColdSteelBowAssembly::GatherResources(Item,Paths);
                Add(ColdSteelInventory::Text(Item,TEXT("bow_part_arrow_mesh")));
                Add(ColdSteelInventory::Text(Item,TEXT("bow_release_sound")));
                Add(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
                BladeRig=ColdSteelInventory::Text(Offhand,TEXT("viewmodel_mesh"));
                BladeMesh=ColdSteelInventory::Text(Offhand,TEXT("world_mesh"));
                Add(BladeRig); Add(BladeMesh);
            }
            if (Gear.Role==EUnknownRole::Melee)
            {
                HeldRig=ColdSteelInventory::Text(Item,TEXT("viewmodel_mesh"));
                Add(HeldRig);
                if (ColdSteelInventory::IsTwoHandedSword(Item))
                {
                    const FString Folder=ColdSteelModularSword::AnimationFolder(Item);
                    if (!Folder.IsEmpty()) { HeldIdle=Folder+TEXT("/A_RuneSword_Idle.A_RuneSword_Idle"); Add(HeldIdle); }
                }
                else if (ColdSteelInventory::IsTwoHandedBlunt(Item))
                {
                    // Match ProductionTool's frozen equipment pose. The body
                    // clips were authored against this palm-to-haft relation.
                    const FString Prefix=ColdSteelInventory::Text(Item,TEXT("tool_animation_prefix"));
                    if (!Prefix.IsEmpty())
                    {
                        const FString Package=Prefix+TEXT("Idle");
                        HeldIdle=Package+TEXT(".")+FPaths::GetCleanFilename(Package);
                        Add(HeldIdle);
                    }
                }
                if (ColdSteelModularSword::Supports(Item)) ColdSteelModularSword::GatherVisualResources(Item,Paths);
            }
            if (Gear.Role==EUnknownRole::Magic)
            {
                ColdSteelStaffAssembly::Gather(Item,Paths);
                HeldRig=TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7");
                BookMesh=ColdSteelInventory::Text(Offhand,TEXT("world_mesh"));
                Add(HeldRig);
                Add(BookMesh);
            }

            const auto Bank = Object(Selected,TEXT("clips"));
            const bool Hammer = ColdSteelInventory::IsTwoHandedBlunt(Item);
            const bool Blade = ColdSteelInventory::IsOneHandedBlade(Item);
            const FString Family = Gear.Role==EUnknownRole::Gun ?
                (ColdSteelInventory::Text(Item,TEXT("weaponType"))==TEXT("pistol")?TEXT("Pistol"):TEXT("Rifle")) :
                (Hammer?TEXT("Warhammer"):TEXT("Unarmed"));
            const auto Clip = [&](FName Name,const FString& Id)
            {
                const FString Path = String(Bank,Id);
                if (!Path.IsEmpty()) { Animations.Add(Name,Path); Add(Path); }
            };
            Clip(TEXT("Idle"),Gear.Role==EUnknownRole::Melee && !Hammer ?
                (Blade?TEXT("Kukri.FullBody.Idle"):TEXT("Melee.FullBody.Idle")) : Family+TEXT(".Idle"));
            Clip(TEXT("Walk"),Family+TEXT(".Walk.Fwd"));
            Clip(TEXT("Run"),Family+TEXT(".Jog.Fwd"));
            for (const TCHAR* Direction : {TEXT("Fwd"), TEXT("Fwd_Right"), TEXT("Right"), TEXT("Bwd_Right"),
                TEXT("Bwd"), TEXT("Bwd_Left"), TEXT("Left"), TEXT("Fwd_Left")})
            {
                Clip(FName(*(FString(TEXT("Walk.")) + Direction)), Family + TEXT(".Walk.") + Direction);
                Clip(FName(*(FString(TEXT("Run.")) + Direction)), Family + TEXT(".Jog.") + Direction);
            }
            if (Gear.Role==EUnknownRole::Melee)
            {
                Clip(TEXT("Swing"),Hammer?TEXT("Warhammer.FullBody.Slash1"):Blade?TEXT("Kukri.FullBody.Slash1"):TEXT("Melee.FullBody.Slash1"));
                if (Blade && Animations.Contains(TEXT("Swing"))) Animations.Add(TEXT("BladeSwing"),Animations.FindRef(TEXT("Swing")));
                if (Hammer && Animations.Contains(TEXT("Swing"))) Animations.Add(TEXT("HammerSwing"),Animations.FindRef(TEXT("Swing")));
            }
            if (Gear.Role==EUnknownRole::Gun)
            {
                Clip(TEXT("Reload"),Family+TEXT(".Reload")); Add(FlashPath);
                Clip(TEXT("CrouchIdle"),TEXT("Crouch.Idle"));
                for(const TCHAR* Direction:{TEXT("Fwd"),TEXT("Fwd_Right"),TEXT("Right"),TEXT("Bwd_Right"),
                    TEXT("Bwd"),TEXT("Bwd_Left"),TEXT("Left"),TEXT("Fwd_Left")})
                    Clip(FName(*(FString(TEXT("Crouch."))+Direction)),FString(TEXT("Crouch.Walk."))+Direction);
            }
            if (Gear.Role==EUnknownRole::Bow)
            {
                Clip(TEXT("Idle"),TEXT("Bow.Sparrow.Carry"));
                Clip(TEXT("BowDraw"),TEXT("Bow.Sparrow.Draw"));
                Clip(TEXT("BowHold"),TEXT("Bow.Sparrow.Hold"));
                Clip(TEXT("BowRelease"),TEXT("Bow.Sparrow.Release"));
                Clip(TEXT("DualIdle"),TEXT("Kukri.FullBody.Dual.Idle"));
                Clip(TEXT("DualSwing"),TEXT("Kukri.FullBody.Dual.Slash1"));
            }
            if (Gear.Role==EUnknownRole::Magic)
            {
                Clip(TEXT("StaffCarry"),TEXT("Staff.NativeArm.Carry"));
                if (!BookMesh.IsEmpty()) Clip(TEXT("BookCarry"),TEXT("Staff.BookCarry"));
                Clip(TEXT("Gather"),TEXT("Staff.FullBody.CastGather"));
                Clip(TEXT("Release"),TEXT("Staff.FullBody.CastRelease"));
            }
            Clip(TEXT("Stagger"),TEXT("Melee.FullBody.GuardHit"));
            Clip(TEXT("Dead"),TEXT("Dead"));
        }
    };
    void FitMageImplements(AActor& Owner,USkeletalMeshComponent& Body,UStaticMeshComponent& Staff,
        const FAppearance& Look,const FColdSteelItem& Item,TArray<TPair<int32,FQuat>>& Fingers)
    {
        auto* Rig=Asset<USkeletalMesh>(Look.HeldRig);
        if (!Rig) return;
        const auto& Source=Rig->GetRefSkeleton();
        const auto& Target=Body.GetSkeletalMeshAsset()->GetRefSkeleton();
        const auto ToComponentPose=[&Source](TArray<FTransform> Pose)
        {
            for (int32 I=1; I<Pose.Num(); ++I)
                if (const int32 Parent=Source.GetParentIndex(I); Parent!=INDEX_NONE) Pose[I]*=Pose[Parent];
            return Pose;
        };
        TArray<FTransform> TargetPose;
        auto StoreFingers=[&](const FFPSBodyGripRig& Grip)
        {
            for (int32 I:Grip.Descendants) Fingers.Emplace(I,TargetPose[I].GetRotation());
        };

        const FName Right(TEXT("hand_r")), Left(TEXT("hand_l"));
        FFPSBodyGripRig RightGrip;
        RightGrip.Initialize(Source,Target,Right,Right);
        if (RightGrip.IsValid())
        {
            const int32 Variant=StaffGripPose::VariantForMesh(ColdSteelInventory::Text(Item,TEXT("staff_part_grip_lining_mesh")));
            const auto& Hold=StaffGripPose::Get(Rig,RightGrip.SourceBind,Variant);
            const auto Pose=ToComponentPose(Hold.Local[0]);
            FPSBodyStaffGrip::AdaptMount(RightGrip,Variant);
            if (!FPSBodyStaffGrip::Transfer(RightGrip,Source,Pose,TargetPose,Variant)) RightGrip.Transfer(Pose,TargetPose);
            StoreFingers(RightGrip);
            Staff.SetRelativeTransform(FTransform(-StaffGripPose::HoldPoint())*Hold.HandInGrip.Inverse()*RightGrip.Mount);
        }
        auto* BookMesh=Asset<UStaticMesh>(Look.BookMesh);
        if (!BookMesh) return;
        FFPSBodyGripRig LeftGrip;
        LeftGrip.Initialize(Source,Target,Left,Left);
        if (!LeftGrip.IsValid()) return;
        auto BookPose=Source.GetRefBonePose();
        for (const auto& Finger:SpellbookAuthoredGrip::Fingers)
            if (int32 I=Source.FindBoneIndex(Finger.Name); I!=INDEX_NONE) BookPose[I].SetRotation(Finger.Rotation.GetNormalized());
        LeftGrip.Transfer(ToComponentPose(MoveTemp(BookPose)),TargetPose);
        StoreFingers(LeftGrip);

        auto* Book=NewObject<UStaticMeshComponent>(&Owner,TEXT("HeldSpellbook"));
        Owner.AddInstanceComponent(Book);
        Book->SetStaticMesh(BookMesh);
        Book->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Book->SetGenerateOverlapEvents(false);
        Book->SetCanEverAffectNavigation(false);
        Book->SetupAttachment(&Body,Left);
        Book->SetRelativeTransform(SpellbookBookOrientation::InHand()*LeftGrip.Mount);
        Book->RegisterComponent();
    }
    FTransform SampleChain(const UAnimSequence& Idle,FName Bone)
    {
        const auto& Ref=Idle.GetSkeleton()->GetReferenceSkeleton();
        FTransform Result=FTransform::Identity;
        for (int32 Index=Ref.FindBoneIndex(Bone);Index!=INDEX_NONE;Index=Ref.GetParentIndex(Index))
        {
            FTransform Local;
            Idle.GetBoneTransform(Local,FSkeletonPoseBoneIndex(Index),FAnimExtractContext(0.,false),false);
            Result=Result*Local;
        }
        return Result;
    }
    bool FitHeldMelee(UStaticMeshComponent& Held,const FAppearance& Look,const FColdSteelItem& Item,const USkeletalMesh& Body,
        FTransform* SupportGrip=nullptr,TArray<TPair<int32,FQuat>>* Fingers=nullptr)
    {
        auto* Rig=Asset<USkeletalMesh>(Look.HeldRig);
        if (!Rig) return false;
        const FName Palm(TEXT("hand_r")), WeaponBone(TEXT("WPN_root"));
        FFPSBodyGripRig Retarget;
        Retarget.Initialize(Rig->GetRefSkeleton(),Body.GetRefSkeleton(),Palm,Palm);
        if (!Retarget.IsValid()) return false;
        FTransform WeaponFrame=FTransform::Identity, HandFrame=FTransform::Identity;
        FTransform Mount=ColdSteelModularSword::BoneMount(Item);
        if (ColdSteelInventory::UsesKukriMoveset(Item))
        {
            for (const auto& Bone : FPSBodyKukriGripData::Bones)
            {
                if (Bone.Name==Palm) HandFrame=Bone.Transform;
                else if (Bone.Name==WeaponBone) WeaponFrame=Bone.Transform;
            }
            Mount=FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01));
        }
        else if (auto* Idle=Asset<UAnimSequence>(Look.HeldIdle); Idle && Idle->GetSkeleton()
            && Idle->GetSkeleton()->GetReferenceSkeleton().FindBoneIndex(WeaponBone)!=INDEX_NONE)
        {
            HandFrame=SampleChain(*Idle,Palm);
            WeaponFrame=SampleChain(*Idle,WeaponBone);
            if (!ColdSteelModularSword::Supports(Item)) WeaponFrame.SetScale3D(FVector::OneVector);
        }
        else return false;
        HandFrame.SetScale3D(FVector::OneVector);
        if (SupportGrip)
        {
            auto* Idle=Asset<UAnimSequence>(Look.HeldIdle);
            FFPSBodyGripRig Support;
            Support.Initialize(Rig->GetRefSkeleton(),Body.GetRefSkeleton(),TEXT("hand_l"),TEXT("hand_l"));
            if (!Idle || !Support.IsValid()) return false;
            FTransform Left=SampleChain(*Idle,TEXT("hand_l"));
            Left.SetScale3D(FVector::OneVector);
            // Same source-palm -> fitted world-palm conversion as the player.
            *SupportGrip=Support.Mount.Inverse()*Left.GetRelativeTransform(HandFrame)*Retarget.Mount;
            SupportGrip->SetScale3D(FVector::OneVector);
        }
        if (Fingers)
        {
            TArray<FTransform> SourcePose=Retarget.SourceBind;
            if (ColdSteelInventory::UsesKukriMoveset(Item))
            {
                for (const auto& Bone:FPSBodyKukriGripData::Bones)
                    if (const int32 I=Rig->GetRefSkeleton().FindBoneIndex(Bone.Name);I!=INDEX_NONE) SourcePose[I]=Bone.Transform;
            }
            else if (auto* Idle=Asset<UAnimSequence>(Look.HeldIdle))
                for (int32 I=0;I<SourcePose.Num();++I) SourcePose[I]=SampleChain(*Idle,Rig->GetRefSkeleton().GetBoneName(I));
            auto Store=[&](const FFPSBodyGripRig& Grip)
            {
                TArray<FTransform> Fitted;
                Grip.Transfer(SourcePose,Fitted);
                for (int32 I:Grip.Descendants) Fingers->Emplace(I,Fitted[I].GetRotation());
            };
            Store(Retarget);
            if (SupportGrip)
            {
                FFPSBodyGripRig Support;
                Support.Initialize(Rig->GetRefSkeleton(),Body.GetRefSkeleton(),TEXT("hand_l"),TEXT("hand_l"));
                Store(Support);
            }
        }
        Held.SetRelativeTransform((Mount*WeaponFrame).GetRelativeTransform(HandFrame)*Retarget.Mount);
        return true;
    }
    void DressHead(AActor& Owner,USkeletalMeshComponent& Body,const FAppearance& Look,FName BodyType)
    {
        if (auto* AssetMesh=Asset<USkeletalMesh>(String(Look.Head,TEXT("mesh"))))
        {
            auto* Head = NewObject<USkeletalMeshComponent>(&Owner);
            Owner.AddInstanceComponent(Head);
            Head->SetupAttachment(&Body);
            Head->SetSkeletalMeshAsset(AssetMesh);
            Head->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Head->SetGenerateOverlapEvents(false);
            if (const auto Materials=Object(Look.Head,TEXT("materials")))
                for (const auto& Pair : Materials->Values)
                    if (auto* Mat=Asset<UMaterialInterface>(Pair.Value->AsString())) Head->SetMaterialByName(FName(*Pair.Key),Mat);
            Head->SetAnimInstanceClass(UFPSPlayerHeadAnimInstance::StaticClass());
            Head->RegisterComponent();
            Head->AddTickPrerequisiteComponent(&Body);
            TArray<TObjectPtr<UGroomComponent>> Grooms;
            FPSBodyAppearance::AssembleHeadGrooms(Body,*Head,Look.Grooms,Look.ScalpStart,Grooms);
        }
        UMeshComponent* Hat = nullptr;
        if (auto* Static=Asset<UStaticMesh>(String(Look.Headwear,TEXT("static_mesh"))))
        {
            auto* Part = NewObject<UStaticMeshComponent>(&Owner);
            Part->SetStaticMesh(Static);
            Hat = Part;
        }
        else if (auto* Skinned=Asset<USkeletalMesh>(String(Look.Headwear,TEXT("skeletal_mesh"))))
        {
            auto* Part = NewObject<USkeletalMeshComponent>(&Owner);
            Part->SetSkeletalMeshAsset(Skinned);
            Hat = Part;
        }
        if (!Hat) return;
        const auto Fit = Object(Object(Look.Headwear,TEXT("fits")),BodyType.ToString());
        const auto Rotation = Vector(Fit,TEXT("rotation"),FVector::ZeroVector);
        Owner.AddInstanceComponent(Hat);
        Hat->SetupAttachment(&Body,FName(*String(Look.Headwear,TEXT("attach_bone"))));
        Hat->SetRelativeTransform(FTransform(FRotator(Rotation.X,Rotation.Y,Rotation.Z),Vector(Fit,TEXT("location"),FVector::ZeroVector),Vector(Fit,TEXT("scale"),FVector::OneVector)));
        Hat->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Hat->SetGenerateOverlapEvents(false);
        Hat->RegisterComponent();
    }
}

void AUnknownHumanoid::PrepareWeaponAudio(const FColdSteelItem& Item)
{
    if (GetNetMode()==NM_DedicatedServer || Loadout.Role==EUnknownRole::Magic || MeleeAttenuation) return;
    auto MakeAttenuation=[this](float Inner,float Falloff)
    {
        auto* Settings=NewObject<USoundAttenuation>(this);
        Settings->Attenuation.bAttenuate=true;
        Settings->Attenuation.bSpatialize=true;
        Settings->Attenuation.AttenuationShapeExtents=FVector(Inner);
        Settings->Attenuation.FalloffDistance=Falloff;
        return Settings;
    };
    MeleeAttenuation=MakeAttenuation(80.f,1600.f);
    FString Swing,Impact;
    TArray<FSoftObjectPath> Paths;
    if (Loadout.Role==EUnknownRole::Gun)
    {
        ShotAttenuation=MakeAttenuation(150.f,12000.f);
        FireSound=FSoftObjectPath(ColdSteelInventory::Text(Item,TEXT("fire_sound")));
        if (!FireSound.IsNull()) Paths.Add(FireSound.ToSoftObjectPath());
    }
    else
    {
        Swing=ColdSteelInventory::Text(Item,TEXT("swing_sound"));
        if (Swing.IsEmpty() && ColdSteelInventory::IsTwoHandedBlunt(Item))
            Swing=TEXT("/Game/Weapons/SteelWarhammer20261014/NormalSwingAudioV1/S_Warhammer_NormalSwing.S_Warhammer_NormalSwing");
        Impact=ColdSteelInventory::Text(Item,TEXT("hit_sound"));
    }
    // Empty guns use the player quick-melee pair. It also covers a weapon without authored melee audio.
    if (Swing.IsEmpty()) Swing=TEXT("/Game/Audio/QuickCombat20260918/S_QuickCombatSwing.S_QuickCombatSwing");
    if (Impact.IsEmpty()) Impact=TEXT("/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick");
    SwingSound=FSoftObjectPath(Swing);
    ImpactSound=FSoftObjectPath(Impact);
    Paths.Add(SwingSound.ToSoftObjectPath());
    Paths.Add(ImpactSound.ToSoftObjectPath());
    WeaponAudioLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths);
}

void AUnknownHumanoid::MulticastMeleeSound_Implementation(bool bImpact,FVector_NetQuantize Location)
{
    if (GetNetMode()==NM_DedicatedServer) return;
    if (auto* Sound=(bImpact?ImpactSound:SwingSound).LoadSynchronous())
        UGameplayStatics::PlaySoundAtLocation(this,Sound,Location,bImpact?.8f:.85f,1.f,0.f,MeleeAttenuation);
}

void AUnknownHumanoid::OnRep_Loadout()
{
    if (Loadout.Body.IsNone() || !GetGameInstance() || (!HasActorBegunPlay() && !IsActorBeginningPlay())) return;
    if (Loadout.Role==EUnknownRole::Magic && !Fireball)
    {
        Fireball=NewObject<UFPSFireballComponent>(this,TEXT("UnknownFireball"));
        AddInstanceComponent(Fireball);
        Fireball->RegisterComponent();
        PrepareMagic();
    }
    if (bVisualReady || AppearanceLoad) return;
    auto* Catalog=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Catalog) return;
    FColdSteelItem Item;
    Item.Definition=Loadout.Weapon;
    Item.Data=Catalog->ItemDefinitions().FindRef(Loadout.Weapon);
    if (Loadout.Role==EUnknownRole::Bow)
    {
        PrepareArchery();
        Item=GetGameInstance()->GetSubsystem<UGunsmithSystem>()->ResolveBowVisual(Item);
        BowReleaseSound=FSoftObjectPath(ColdSteelInventory::Text(Item,TEXT("bow_release_sound")));
    }
    if (Loadout.Role==EUnknownRole::Gun && GetNetMode()!=NM_DedicatedServer)
        GetOrCreateGunTracers()->bWorldPistol=ColdSteelInventory::Text(Item,TEXT("weaponType"))==TEXT("pistol");
    FColdSteelItem Offhand;
    if (!Loadout.Offhand.IsEmpty())
    {
        Offhand.Definition=Loadout.Offhand;
        Offhand.Data=Catalog->ItemDefinitions().FindRef(Offhand.Definition);
    }
    if (Loadout.Role==EUnknownRole::Bow)
    {
        Offhand.Definition=Loadout.BackupBlade;
        Offhand.Data=Catalog->ItemDefinitions().FindRef(Offhand.Definition);
    }
    HammerBaseContact=ColdSteelInventory::IsTwoHandedBlunt(Item)?ColdSteelInventory::Number(Item,TEXT("contact_seconds"),.6):0.f;
    PrepareWeaponAudio(Loadout.Role==EUnknownRole::Bow?Offhand:Item);
    auto Look=MakeShared<UnknownAppearance::FAppearance>(Loadout,Item,Offhand);
    if (Look->Paths.IsEmpty()) return;
    const bool Dedicated=GetNetMode()==NM_DedicatedServer;
    if (Dedicated)
    {
        Look->Paths.Reset();
        Look->Add(Look->Body);
        if (Loadout.Role==EUnknownRole::Bow) Look->Add(ColdSteelInventory::Text(Item,TEXT("bow_part_arrow_mesh")));
        for (const auto& Clip:Look->Animations) Look->Add(Clip.Value);
    }
    AppearanceLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Look->Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Look,Item,Offhand,Dedicated]()
    {
        using namespace UnknownAppearance;
        auto* Body=GetMesh();
        auto* Mesh=Asset<USkeletalMesh>(Look->Body);
        if (!Mesh) return;
        Body->SetSkeletalMeshAsset(Mesh);
        if (const auto* Physics=Body->GetPhysicsAsset(); Physics && Physics->FindBodyIndex(TEXT("head"))!=INDEX_NONE && Physics->SkeletalBodySetups.Num()>1 && !Dead())
        {
            GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
            if (HasAuthority()) Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        }
        for (const auto& Pair : Look->Animations)
            if (auto* Clip=Asset<UAnimSequence>(Pair.Value)) Clips.Add(Pair.Key,Clip);
        bVisualReady=true;
        Body->SetAnimInstanceClass(UUnknownHumanoidAnimInstance::StaticClass());
        if (Dedicated) return;
        Clothing->SetExternalWorldBody(Body);
        Clothing->SetBodyType(Loadout.Body);
        Clothing->SetWorldOutfit(Loadout.Outfit);
        DressHead(*this,*Body,*Look,Loadout.Body);
        const FName Hand(TEXT("hand_r"));
        if (Loadout.Role==EUnknownRole::Bow)
        {
            HeldWeapon->AttachToComponent(Body,FAttachmentTransformRules::SnapToTargetNotIncludingScale,TEXT("hand_l"));
            ColdSteelBowAssembly::Apply(HeldWeapon,Item);
            const auto RiserParts=HeldWeapon->GetAttachChildren();
            for(USceneComponent* Part:RiserParts)if(auto* Skin=Cast<UPoseableMeshComponent>(Part))
            {
                auto* AssetMesh=Cast<USkeletalMesh>(Skin->GetSkinnedAsset());
                if(AssetMesh!=Asset<USkeletalMesh>(ColdSteelInventory::Text(Item,TEXT("bow_part_riser_mesh"))))continue;
                BowFlex=NewObject<UBowFlexMeshComponent>(this); AddInstanceComponent(BowFlex);
                BowFlex->SetupAttachment(HeldWeapon); BowFlex->SetRelativeTransform(Skin->GetRelativeTransform());
                BowFlex->SetFlexMesh(AssetMesh);
                for(int32 I=0;I<Skin->GetNumMaterials();++I)BowFlex->SetMaterial(I,Skin->GetMaterial(I));
                BowFlex->SetCollisionEnabled(ECollisionEnabled::NoCollision);BowFlex->SetCanEverAffectNavigation(false);
                BowFlex->RegisterComponent();Skin->DestroyComponent();break;
            }
            BowScale=ColdSteelInventory::Number(Item,TEXT("bow_part_riser_scale"),1.f);
            BowFlexDistribution=ColdSteelInventory::Number(Item,TEXT("bow_flex_distribution"),1.15f);
            auto ReadVector=[&](const TCHAR* Key,FVector Default)
            {
                TArray<FString> Parts; ColdSteelInventory::Text(Item,Key).ParseIntoArray(Parts,TEXT(","));
                return Parts.Num()==3?FVector(FCString::Atod(*Parts[0]),FCString::Atod(*Parts[1]),FCString::Atod(*Parts[2])):Default;
            };
            BowTips[0]=ReadVector(TEXT("nock_upper_cm"),FVector(-21.46,-.935,64.11));
            BowTips[1]=ReadVector(TEXT("nock_lower_cm"),FVector(-21.46,-.935,-64.04));
            BowBrace=ReadVector(TEXT("brace_nock_cm"),FVector(-21.46,-.935,1.5));
            BowStringRadius=ColdSteelInventory::Number(Item,TEXT("bow_part_string_radius_cm"),.09);
            // Replace the assembly's resting string with two live segments.
            const auto Children=HeldWeapon->GetAttachChildren();
            for (USceneComponent* Child:Children) if (auto* Static=Cast<UStaticMeshComponent>(Child))
                if (Static->ComponentHasTag(TEXT("BowAssemblyPart")) && Static->GetStaticMesh()==Asset<UStaticMesh>(TEXT("/Engine/BasicShapes/Cylinder.Cylinder")))
                    Static->DestroyComponent();
            for (int32 I=0; I<2; ++I)
            {
                BowStrings[I]=NewObject<UStaticMeshComponent>(this); AddInstanceComponent(BowStrings[I]);
                BowStrings[I]->SetStaticMesh(Asset<UStaticMesh>(TEXT("/Engine/BasicShapes/Cylinder.Cylinder")));
                BowStrings[I]->SetupAttachment(HeldWeapon); BowStrings[I]->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                BowStrings[I]->SetCanEverAffectNavigation(false); BowStrings[I]->RegisterComponent();
                if(auto* Material=Asset<UMaterialInterface>(ColdSteelInventory::Text(Item,TEXT("bow_part_string_material"))))BowStrings[I]->SetMaterial(0,Material);
            }
            NockedArrow=NewObject<UStaticMeshComponent>(this); AddInstanceComponent(NockedArrow);
            NockedArrow->SetStaticMesh(Asset<UStaticMesh>(ColdSteelInventory::Text(Item,TEXT("bow_part_arrow_mesh"))));
            NockedArrow->SetupAttachment(HeldWeapon); NockedArrow->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            NockedArrow->SetCanEverAffectNavigation(false); NockedArrow->RegisterComponent();
            if(UStaticMesh* Arrow=NockedArrow->GetStaticMesh())
            {
                const auto Bounds=Arrow->GetBounds(); const bool AlongX=Bounds.BoxExtent.X>Bounds.BoxExtent.Z;
                const float Length=ColdSteelInventory::Number(Item,TEXT("arrow_length_cm"),76.f);
                const float Scale=Length/FMath::Max(.01f,2.f*float(AlongX?Bounds.BoxExtent.X:Bounds.BoxExtent.Z));
                const FVector Axis=AlongX?FVector::XAxisVector:FVector::ZAxisVector;
                const FVector Stretch=AlongX?FVector(Scale,1,1):FVector(1,1,Scale);
                const FQuat Frame=FQuat::FindBetweenNormals(Axis,FVector::XAxisVector);
                ArrowFromNock=FTransform(Frame,FVector(Length*.5f,0,0)-Frame.RotateVector(Axis*FVector::DotProduct(Bounds.Origin,Axis)*Stretch),Stretch);
            }
            auto* Rig=Asset<USkeletalMesh>(Look->BladeRig);
            for (int32 Side=0; Side<2; ++Side)
            {
                auto* Blade=NewObject<UStaticMeshComponent>(this); AddInstanceComponent(Blade);
                Blade->SetStaticMesh(Asset<UStaticMesh>(Look->BladeMesh));
                Blade->SetupAttachment(Body,Side?TEXT("hand_l"):TEXT("hand_r"));
                Blade->SetCollisionEnabled(ECollisionEnabled::NoCollision); Blade->SetCanEverAffectNavigation(false); Blade->RegisterComponent();
                if (Side) BackupLeft=Blade; else BackupRight=Blade;
                if (!Rig) continue;
                const auto& Ref=Rig->GetRefSkeleton(); auto Pose=Ref.GetRefBonePose();
                for(int32 I=1; I<Pose.Num(); ++I) if(Ref.GetParentIndex(I)>=0)Pose[I]*=Pose[Ref.GetParentIndex(I)];
                if(Side) { for(const auto& Bone:FPSBodyKukriDualGripData::Bones)if(int32 I=Ref.FindBoneIndex(Bone.Name);I!=INDEX_NONE)Pose[I]=Bone.Transform; }
                else { for(const auto& Bone:FPSBodyKukriGripData::Bones)if(int32 I=Ref.FindBoneIndex(Bone.Name);I!=INDEX_NONE)Pose[I]=Bone.Transform; }
                const FName Palm=Side?TEXT("hand_l"):TEXT("hand_r"); FFPSBodyGripRig Grip;
                Grip.Initialize(Ref,Mesh->GetRefSkeleton(),Palm,Palm); if(!Grip.IsValid())continue;
                TArray<FTransform> TargetPose; Grip.Transfer(Pose,TargetPose);
                for(int32 I:Grip.Descendants) ImplementFingers.Emplace(I,TargetPose[I].GetRotation());
                if(Side) Blade->SetRelativeTransform(FPSBodyKukriDualGripData::BladeInHand*Grip.Mount);
                else { auto BladeLook=*Look; BladeLook.HeldRig=Look->BladeRig; FitHeldMelee(*Blade,BladeLook,Offhand,*Mesh); }
            }
            BowPoseFinalized=Body->RegisterOnBoneTransformsFinalizedDelegate(
                FOnBoneTransformsFinalizedMultiCast::FDelegate::CreateUObject(this,&AUnknownHumanoid::UpdateBowPresentation));
            OnRep_BowMode(); UpdateBowPresentation();
            return;
        }
        if (Loadout.Role==EUnknownRole::Gun)
        {
            MuzzleFlash=Asset<UNiagaraSystem>(FlashPath);
            HeldGun=NewObject<UPoseableMeshComponent>(this,TEXT("HeldGun"));
            AddInstanceComponent(HeldGun);
            HeldGun->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            HeldGun->SetGenerateOverlapEvents(false);
            HeldGun->SetCanEverAffectNavigation(false);
            // The posed first-person source can have bounds far from its grip. Cull the held gun with its wearer.
            HeldGun->bUseAttachParentBound=true;
            HeldGun->SetupAttachment(Body,Hand);
            HeldGun->RegisterComponent();
            if (!AColdSteelPickup::AssembleWorldGun(Item,*GetGameInstance(),*HeldGun,nullptr,&GunMuzzleInMesh))
            {
                UE_LOG(LogTemp,Warning,TEXT("Unknown humanoid could not assemble held gun %s"),*Item.Definition);
                HeldGun->DestroyComponent();
                HeldGun=nullptr;
                return;
            }
            FFPSBodyGripRig Grip;
            const auto* Source=CastChecked<USkeletalMesh>(HeldGun->GetSkinnedAsset());
            Grip.Initialize(Source->GetRefSkeleton(),Mesh->GetRefSkeleton(),Hand,Hand);
            FTransform Palm=HeldGun->GetSocketTransform(Hand,RTS_Component);
            Palm.SetScale3D(FVector::OneVector);
            GunMount=Palm.Inverse()*Grip.Mount;
            HeldGun->SetRelativeTransform(GunMount);
            GunAimFrame=FPSBodyGunAim::FromMuzzle(GunMuzzleInMesh,GunMount);
            // Use this gun's posed palms and finger chains, including fitted
            // front grips; the generic body donor cannot know its grip spacing.
            FFPSBodyGripRig Support;
            Support.Initialize(Source->GetRefSkeleton(),Mesh->GetRefSkeleton(),TEXT("hand_l"),TEXT("hand_l"));
            bHasGunSupport=Grip.IsValid()&&Support.IsValid();
            if(bHasGunSupport)
            {
                FTransform Left=HeldGun->GetSocketTransform(TEXT("hand_l"),RTS_Component);
                Left.SetScale3D(FVector::OneVector);
                GunSupportGrip=Support.Mount.Inverse()*Left.GetRelativeTransform(Palm)*Grip.Mount;
                TArray<FTransform> SourcePose,TargetPose;
                for(int32 I=0;I<Source->GetRefSkeleton().GetNum();++I)
                    SourcePose.Add(HeldGun->GetSocketTransform(Source->GetRefSkeleton().GetBoneName(I),RTS_Component));
                for(const auto* Rig:{&Grip,&Support})
                {
                    Rig->Transfer(SourcePose,TargetPose);
                    for(int32 I:Rig->Descendants)ImplementFingers.Emplace(I,TargetPose[I].GetRotation());
                }
            }
            return;
        }
        HeldWeapon->AttachToComponent(Body,FAttachmentTransformRules::SnapToTargetNotIncludingScale,Hand);
        const auto& Ref = Mesh->GetRefSkeleton();
        FTransform HandBind = FTransform::Identity;
        for (int32 Bone=Ref.FindBoneIndex(Hand); Bone!=INDEX_NONE; Bone=Ref.GetParentIndex(Bone))
            HandBind=HandBind*Ref.GetRefBonePose()[Bone];
        const FQuat Rotation=HandBind.GetRotation().Inverse()*FRotator(0,90,0).Quaternion();
        if (Loadout.Role==EUnknownRole::Magic)
        {
            ColdSteelStaffAssembly::Apply(HeldWeapon,Item);
            HeldWeapon->SetRelativeTransform(FTransform(Rotation,-Rotation.RotateVector(StaffGripPose::HoldPoint())));
            FitMageImplements(*this,*Body,*HeldWeapon,*Look,Item,ImplementFingers);
        }
        else if (auto* Static=Asset<UStaticMesh>(Look->Weapon))
        {
            HeldWeapon->SetStaticMesh(Static);
            if (ColdSteelModularSword::Supports(Item)) ColdSteelModularSword::Apply(HeldWeapon,Item);
            bHasMeleeSupport=false;
            if (ColdSteelInventory::IsTwoHandedSword(Item))
            {
                bHasMeleeSupport=FitHeldMelee(*HeldWeapon,*Look,Item,*Mesh,&MeleeSupportGrip,&ImplementFingers);
                if (bHasMeleeSupport) return;
            }
            else if (FitHeldMelee(*HeldWeapon,*Look,Item,*Mesh,nullptr,
                ColdSteelInventory::UsesKukriMoveset(Item)?&ImplementFingers:nullptr)) return;
            HeldWeapon->SetRelativeTransform(FTransform(Rotation));
            for (FName Socket : {FName(TEXT("Grip_R")),FName(TEXT("Grip")),FName(TEXT("Hand_R"))})
                if (Static->FindSocket(Socket))
                {
                    HeldWeapon->SetRelativeTransform(HeldWeapon->GetSocketTransform(Socket,RTS_Component).Inverse());
                    break;
                }
        }
    }));
}

void AUnknownHumanoid::UpdateGunRecoil()
{
    if (HeldGun && LastShotTime>=0.f)
    {
        const float Kick=FMath::Clamp(1.f-(ServerTime()-LastShotTime)/.1f,0.f,1.f);
        // Recoil is now carried by the complete aimed upper-body chain. A local
        // pitch on the imported gun mesh uses different axes on each firearm
        // and detaches the weapon from the supporting palms.
        HeldGun->SetRelativeTransform(GunMount);
        if (Kick<=0.f) LastShotTime=-10.f;
    }
}

void AUnknownHumanoid::MulticastMagicReleaseSound_Implementation(FName Skill,FVector_NetQuantize Location)
{
    if(GetNetMode()!=NM_Client)return; // Authority already played the native sound once.
    TArray<FSoftObjectPath> Sounds;
    if(Skill==TEXT("holyLight"))Sounds.Emplace(TEXT("/Game/Skills/HolyLight/S_HolyLightCast.S_HolyLightCast"));
    else if(Skill==TEXT("lightningStrike"))
    {
        Sounds.Emplace(TEXT("/Game/Skills/Lightning/S_LightningCast1.S_LightningCast1"));
        Sounds.Emplace(TEXT("/Game/Skills/Lightning/S_LightningCast2.S_LightningCast2"));
    }
    if(Sounds.IsEmpty())return;
    const float Received=GetWorld()->GetTimeSeconds();
    auto Play=FSimpleDelegate::CreateWeakLambda(this,[this,Sounds,Location,Received]()
    {
        // An old cast must not sound later when a late asset finishes loading.
        if(GetWorld()->GetTimeSeconds()-Received>.25f)return;
        for(const auto& Path:Sounds)if(auto* Sound=Cast<USoundBase>(Path.ResolveObject()))
            UGameplayStatics::PlaySoundAtLocation(this,Sound,Location,1.f,1.f,0.f,MeleeAttenuation);
    });
    if(Sounds.ContainsByPredicate([](const FSoftObjectPath& Path){return !Path.ResolveObject();}))
        UAssetManager::GetStreamableManager().RequestAsyncLoad(Sounds,MoveTemp(Play));
    else Play.Execute();
}

UFPSWeaponFXComponent* AUnknownHumanoid::GetOrCreateGunTracers()
{
    if (!GunTracers)
    {
        GunTracers=NewObject<UFPSWeaponFXComponent>(this,TEXT("GunTracers"));
        AddInstanceComponent(GunTracers);
        GunTracers->RegisterComponent();
        GunTracers->InitializeWorldTracers();
        GunTracers->AddTickPrerequisiteComponent(Ballistics);
    }
    return GunTracers;
}

FVector AUnknownHumanoid::GunMuzzle(const FVector& LaunchStart) const
{
    return HeldGun&&GunAimFrame.bValid?HeldGun->GetComponentTransform().TransformPosition(GunMuzzleInMesh.GetLocation()):LaunchStart;
}

FVector AUnknownHumanoid::TracerMuzzle(const FVector& LaunchStart,const FVector& Muzzle) const
{
    if (LaunchStart.Equals(Muzzle)) return LaunchStart;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(UnknownMuzzleCover),true,this);
    return RangedAttackQuery::LineTraceTest(GetWorld(),this,LaunchStart,Muzzle,ECC_Visibility,Query)?LaunchStart:Muzzle;
}

void AUnknownHumanoid::MulticastShot_Implementation(FVector_NetQuantize Start,FVector_NetQuantizeNormal Direction,
    float FlightSpeed,float RangeCM,APawn* MissedTarget)
{
    if (GetNetMode()==NM_DedicatedServer) return;
    LastShotTime=ServerTime();
    const FVector Muzzle=GunMuzzle(Start);
    if (!HasAuthority())
        Ballistics->LaunchHostile(Start,Direction,FlightSpeed,RangeCM,0.f,0.f,0.f,MissedTarget,GetOrCreateGunTracers(),TracerMuzzle(Start,Muzzle));
    if (auto* Sound=FireSound.LoadSynchronous())
        UGameplayStatics::PlaySoundAtLocation(this,Sound,Muzzle,1.f,1.f,0.f,ShotAttenuation);
    if (MuzzleFlash)
        if (auto* Burst=UNiagaraFunctionLibrary::SpawnSystemAtLocation(this,MuzzleFlash,Muzzle,Direction.Rotation(),FVector::OneVector,true,false,ENCPoolMethod::AutoRelease))
        {
            Burst->SetVariableBool(TEXT("User.Use Bullet Shell"),false);
            Burst->SetVariableBool(TEXT("User.Use Smoke"),false);
            Burst->SetVariableBool(TEXT("User.Use Sparks"),false);
            Burst->Activate(true);
        }
}
