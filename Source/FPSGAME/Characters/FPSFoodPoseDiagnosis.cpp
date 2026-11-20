#if WITH_EDITOR
// Explicit food-only diagnosis requested by the user. No play, asset saves or inventory transactions.
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyGrip.h"
#include "../Items/PotionArmPose.h"
#include "../Items/PotionUseMotion.h"
#include "../Items/CampfireFoodCatalog.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace FPSFoodPoseDiagnosis
{
static TSharedPtr<FJsonValue> Pack(const FTransform& T)
{
    const auto P=T.GetLocation();const auto Q=T.GetRotation();const auto S=T.GetScale3D();
    TArray<TSharedPtr<FJsonValue>> A;
    for(double V:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W,S.X,S.Y,S.Z})A.Add(MakeShared<FJsonValueNumber>(V));
    return MakeShared<FJsonValueArray>(A);
}
static void Run(const TArray<FString>& Args)
{
    if(Args.IsEmpty())return;
    FString Text;TSharedPtr<FJsonObject> Config;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json")))||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Config))return;
    const FString Variant=Args.Num()>1?Args[1].ToLower():TEXT("jason");
    if(Variant!=TEXT("jason"))
    {
        const TSharedPtr<FJsonObject>* Variants=nullptr;
        const TSharedPtr<FJsonObject>* Selected=nullptr;
        if(!Config->TryGetObjectField(TEXT("body_variants"),Variants)||!(*Variants)->TryGetObjectField(Variant,Selected))return;
        const TSharedPtr<FJsonObject> BodyConfig=*Selected;
        Config=BodyConfig;
    }
    const bool ContactsOnly=Args.Num()>2&&Args[2]==TEXT("contacts");
    auto* Asset=LoadObject<USkeletalMesh>(nullptr,*Config->GetStringField(TEXT("body_mesh")));
    auto* Native=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/Traversal/SK_Traversal_BareArmsV7"));
    if(!Asset||!Native)return;
    TMap<FName,TObjectPtr<UAnimSequence>> Clips;
    for(const auto& Pair:Config->GetObjectField(TEXT("clips"))->Values)
    {
        const FString Key=*Pair.Key;
        if(Key.StartsWith(TEXT("Consume."))||Key.StartsWith(TEXT("Unarmed."))||Key.StartsWith(TEXT("Rifle."))||
            Key.StartsWith(TEXT("Crouch."))||Key==TEXT("Staff.NativeArm.Carry"))
            if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*Pair.Value->AsString()))Clips.Add(*Pair.Key,Clip);
    }
    FAssetCompilingManager::Get().FinishAllCompilation();
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("FoodPoseDiagnosis"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    auto* SourceActor=World->SpawnActor<AActor>();
    auto* Camera=NewObject<UCameraComponent>(SourceActor);SourceActor->AddInstanceComponent(Camera);SourceActor->SetRootComponent(Camera);
    Camera->RegisterComponentWithWorld(World);Camera->SetWorldLocation(FVector(0,0,170));
    auto* Source=NewObject<USkeletalMeshComponent>(SourceActor);SourceActor->AddInstanceComponent(Source);
    Source->SetupAttachment(Camera);Source->SetRelativeRotation(FRotator(0,90,0));Source->SetSkeletalMeshAsset(Native);
    Source->RegisterComponentWithWorld(World);Source->RefreshBoneTransforms();
    const auto& Ref=Asset->GetRefSkeleton();auto Bind=Native->GetRefSkeleton().GetRefBonePose();
    for(int32 I=0;I<Bind.Num();++I)if(Native->GetRefSkeleton().GetParentIndex(I)>=0)Bind[I]=Bind[I]*Bind[Native->GetRefSkeleton().GetParentIndex(I)];
    FFPSBodyGripRig Rig[2];
    Rig[0].Initialize(Native->GetRefSkeleton(),Ref,TEXT("hand_r"),TEXT("hand_r"));
    Rig[1].Initialize(Native->GetRefSkeleton(),Ref,TEXT("hand_l"),TEXT("hand_l"));
    auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Cases,Names,Parents,Reference;
    for(int32 I=0;I<Ref.GetNum();++I){Names.Add(MakeShared<FJsonValueString>(Ref.GetBoneName(I).ToString()));Parents.Add(MakeShared<FJsonValueNumber>(Ref.GetParentIndex(I)));Reference.Add(Pack(Ref.GetRefBonePose()[I]));}
    Report->SetArrayField(TEXT("names"),Names);Report->SetArrayField(TEXT("parents"),Parents);Report->SetArrayField(TEXT("reference"),Reference);
    Report->SetStringField(TEXT("mesh"),Asset->GetPathName());Report->SetBoolField(TEXT("gameplay_started"),false);
    TArray<FString> Foods={TEXT("bread"),TEXT("baguette_bread")};
    for(const auto& Recipe:CampfireFood::Catalog())Foods.AddUnique(Recipe.Cooked);
    for(const FString& FoodId:Foods)for(int32 Case=0;Case<(FoodId==TEXT("roasted_large_lamb")?5:2);++Case)
    {
        const TCHAR* Food=*FoodId;
        const auto* Cooked=CampfireFood::Cooked(FoodId);
        FPotionUseMotion Motion;Motion.Load(false,Cooked?*Cooked->MotionProfile:Food);FPotionArmPose Left,Right;
        const bool PostOff=Case==4||(!Motion.bTwoHanded&&Case==1);
        auto* Actor=World->SpawnActor<AActor>();auto* Body=NewObject<USkeletalMeshComponent>(Actor);Actor->AddInstanceComponent(Body);
        Body->SetSkeletalMeshAsset(Asset);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Body->SetDisablePostProcessBlueprint(PostOff);
        Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Body->RegisterComponentWithWorld(World);Body->SetAnimationMode(EAnimationMode::AnimationBlueprint);Body->SetAnimInstanceClass(UFPSPlayerBodyAnimInstance::StaticClass());
        auto* Anim=CastChecked<UFPSPlayerBodyAnimInstance>(Body->GetAnimInstance());Anim->Clips=Clips;
        const auto& Scale=Config->GetArrayField(TEXT("pose_scale"));Anim->PoseScale=FVector(Scale[0]->AsNumber(),Scale[1]->AsNumber(),Scale[2]->AsNumber());
        const auto& MouthCoordinates=Config->GetArrayField(TEXT("consume_mouth_in_head"));Anim->ConsumeMouthInHead=FVector(MouthCoordinates[0]->AsNumber(),MouthCoordinates[1]->AsNumber(),MouthCoordinates[2]->AsNumber());
        Anim->ConsumePropContact=Motion.BiteInObject;Anim->bHasConsumeProp=true;
        if(Cooked&&!Motion.bTwoHanded&&!Motion.Keys.IsEmpty())
            Anim->CookedFoodTrajectory=MakeShared<FPotionUseMotion>(Motion);
        const TCHAR* FoodMesh=Cooked?*Cooked->CookedMesh:FoodId==TEXT("bread")
            ?TEXT("/Game/Items/Consumables/Bread20261003/SM_Bread"):TEXT("/Game/Items/Consumables/Baguette20261003/SM_Baguette");
        if(auto* PropMesh=LoadObject<UStaticMesh>(nullptr,FoodMesh))
        {
            const auto Bounds=PropMesh->GetBounds();
            const FVector Top=Bounds.Origin+FVector(0,0,Bounds.BoxExtent.Z);
            if(!Cooked)Anim->ConsumePropContact=Top;
            Motion.GripHeight=Bounds.Origin.Z;
            Motion.PrepareFirstPersonFood(Top);
        }
        Anim->BodyState.Family=Case==1&&!PostOff?TEXT("Rifle"):Case==2?TEXT("Staff"):TEXT("Unarmed");
        Anim->BodyState.Weapon=Case==2?FName(TEXT("ue_apprentice_staff")):NAME_None;
        Anim->BodyState.bCrouched=Case==3;Anim->Speed=Case==3?100.f:0.f;
        Anim->EquipmentFingers=Ref.GetRefBonePose();Anim->EquipmentGripHands=Case==2?1:Case==1&&!PostOff?3:0;
        constexpr float Step=1.f/60.f;
        const auto Tick=[&](){Anim->Clock+=Step;Body->TickAnimation(Step,false);Body->RefreshBoneTransforms();};
        for(int32 I=0;I<30;++I)Tick();
        auto Row=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Samples;
        Row->SetStringField(TEXT("food"),Food);Row->SetStringField(TEXT("case"),PostOff?TEXT("post_off"):Case==0?TEXT("unarmed"):Case==1?TEXT("rifle"):Case==2?TEXT("staff"):TEXT("crouch_walk"));
        for(int32 Frame=0;Frame<=FMath::CeilToInt((Motion.Duration+.2f)/Step);++Frame)
        {
            const float Time=Frame*Step;auto& Pose=Source->GetEditableComponentSpaceTransforms();Pose=Bind;
            FTransform Palm;Left.Apply(*Source,Motion,Time,Palm,false,nullptr,Motion.bTwoHanded);
            const FTransform Prop=Motion.ObjectFromPalm(Palm);
            if(Motion.bTwoHanded)
            {
                const auto Object=Prop.GetRelativeTransform(Camera->GetComponentTransform());
                const FQuat R=Object.GetRotation()*Motion.ObjectRotation.Inverse()*Motion.PalmBasis(true);
                const FTransform Goal(R,Object.TransformPosition(Motion.RightObjectGrip)-R.RotateVector(Motion.RightGripInPalm));
                FTransform Result;Right.Apply(*Source,Motion,Time,Result,true,&Goal,true);
            }
            Anim->ActionFingers=Ref.GetRefBonePose();
            for(int32 Side=0;Side<2;++Side)if(Side==1||Motion.bTwoHanded)
            {
                Rig[Side].Transfer(Pose,Anim->ActionFingers);
                auto Hand=Pose[Rig[Side].SourceHand];Hand.SetScale3D(FVector::OneVector);
                Anim->ActionHands[Side]=Rig[Side].Mount.Inverse()*Hand*Source->GetComponentTransform();
            }
            auto& State=Anim->BodyState;const bool Active=Time<Motion.Duration;
            State.Action=Active?EFPSBodyAction::Consume:EFPSBodyAction::None;State.ActionVariant=Active?FName(Food):NAME_None;
            State.bHasActionProgress=true;State.ActionProgress=FMath::Clamp(Time/Motion.Duration,0.f,1.f);State.ActionWeight=Active?Motion.Layer(Time):0.f;
            State.ActionDuration=Motion.Duration;State.ConsumeHands=Motion.bTwoHanded?3:2;
            State.ContactFraction=Motion.DrinkStart/Motion.Duration;State.ReleaseFraction=Motion.DrinkEnd/Motion.Duration;State.ActionEntryFraction=Motion.Grab/Motion.Duration;
            State.Contacts.Consumable=Food;State.Contacts.Wrists=Motion.bTwoHanded?3:2;
            FTransform SourceHandWorld=Pose[Rig[1].SourceHand]*Source->GetComponentTransform();SourceHandWorld.SetScale3D(FVector::OneVector);
            State.Contacts.Props[0]=Prop.GetRelativeTransform(SourceHandWorld)*Rig[1].Mount;
            Anim->ActionFingerMask=Active?(Motion.bTwoHanded?3:2):0;Anim->ActionWristMask=Anim->ActionFingerMask;
            Tick();
            if(Frame==FMath::RoundToInt(Motion.Contact/Step))
            {
                const FTransform Hand=Body->GetSocketTransform(TEXT("hand_l"),RTS_Component);
                const FTransform Head=Body->GetSocketTransform(TEXT("head"),RTS_Component);
                const FVector Bite=(State.Contacts.Props[0]*Hand).TransformPosition(Anim->ConsumePropContact);
                const FVector Mouth=Head.TransformPosition(Anim->ConsumeMouthInHead);
                Row->SetNumberField(TEXT("contact_time_sec"),Time);
                Row->SetNumberField(TEXT("bite_to_mouth_cm"),FVector::Distance(Bite,Mouth));
            }
            if(ContactsOnly||Frame%2!=0)continue;
            auto Sample=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Output;
            for(const FTransform& T:Body->GetComponentSpaceTransforms())Output.Add(Pack(T));
            Sample->SetNumberField(TEXT("time"),Time);Sample->SetNumberField(TEXT("weight"),State.ActionWeight);Sample->SetArrayField(TEXT("world"),Output);
            Sample->SetField(TEXT("prop_local"),Pack(State.Contacts.Props[0]));Samples.Add(MakeShared<FJsonValueObject>(Sample));
        }
        Row->SetArrayField(TEXT("samples"),Samples);Cases.Add(MakeShared<FJsonValueObject>(Row));Actor->Destroy();
    }
    Report->SetArrayField(TEXT("cases"),Cases);Text.Reset();FJsonSerializer::Serialize(Report,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
    FFileHelper::SaveStringToFile(Text,*Args[0],FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    World->DestroyWorld(false);UE_LOG(LogTemp,Display,TEXT("FOOD_POSE_DIAGNOSIS_SAVED %s"),*Args[0]);
}
static FAutoConsoleCommand Command(TEXT("fps.body.DiagnoseFood"),TEXT("Sample all edible solid foods: output.json [jason|kaitlin] [contacts]."),FConsoleCommandWithArgsDelegate::CreateStatic(&Run));
}
#endif
