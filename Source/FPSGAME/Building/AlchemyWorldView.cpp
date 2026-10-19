#include "AlchemyWorldView.h"
#include "AlchemyInteractionAssets.h"
#include "Materials/MaterialInterface.h"
#include "PotionWorkbenchVisualComponent.h"
#include "VoxelBuildPrefabActor.h"
#include "ForgeArmsMeshComponent.h"
#include "WorkstationViewRestore.h"
#include "AlchemyWorkbenchLayout.h"
#include "Camera/CameraComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/SkeletalMesh.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
namespace {const FSoftObjectPath ArmPath(TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7"));
// Keep the working hands inside this fraction of the reach clamp, so the clamp
// in Solve() can never fire and teleport the shoulder onto the bench.
constexpr float AlchemyReachSafety=.9f;}
AAlchemyWorldView::AAlchemyWorldView()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=false;SetReplicates(false);
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Camera=CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));Camera->SetupAttachment(RootComponent);Camera->FieldOfView=AlchemyTabletop::FieldOfView;
    Arms=CreateDefaultSubobject<UForgeArmsMeshComponent>(TEXT("V7Hands"));Arms->SetupAttachment(RootComponent);
    Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);Arms->SetCanEverAffectNavigation(false);Arms->SetCastShadow(false);Arms->SetComponentTickEnabled(false);Arms->SetVisibility(false);
}
void AAlchemyWorldView::Configure(AVoxelBuildPrefabActor* B,APlayerController* P)
{
    Station=B;Player=P;SetOwner(P);WorkingPawn=P?P->GetPawn():nullptr;if(!B)return;
    Visual=B->FindComponentByClass<UPotionWorkbenchVisualComponent>();SetActorTransform(B->Body()->GetComponentTransform());
    if(Visual.IsValid())AddTickPrerequisiteComponent(Visual.Get());
    Loading=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{ArmPath,AlchemyInteraction::Asset(TEXT("M_AlchemyHoverOutline"))},FStreamableDelegate::CreateUObject(this,&ThisClass::Loaded));
}
void AAlchemyWorldView::Loaded()
{
    bLoadFinished=true;
    auto* Outline=Cast<UMaterialInterface>(AlchemyInteraction::Asset(TEXT("M_AlchemyHoverOutline")).ResolveObject());if(!Outline)return;
    Camera->AddOrUpdateBlendable(Outline,1.f);
    auto* Mesh=Cast<USkeletalMesh>(ArmPath.ResolveObject());if(!Mesh)return;Arms->SetSkinnedAssetAndUpdate(Mesh);
    const auto& Ref=Mesh->GetRefSkeleton();LocalReference=Ref.GetRefBonePose();Reference=LocalReference;
    for(int32 I=0;I<Reference.Num();++I)if(Ref.GetParentIndex(I)>=0)Reference[I]*=Reference[Ref.GetParentIndex(I)];
    Pose=Reference;
    FString Raw;TSharedPtr<FJsonObject> Json;
    if(!FFileHelper::LoadFileToString(Raw,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/forge-grip.json")))||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Raw),Json)||!Json)return;
    auto Quat=[](const TArray<TSharedPtr<FJsonValue>>& A){return FQuat(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber(),A[3]->AsNumber()).GetNormalized();};
    for(int32 Side=0;Side<2;++Side)
    {
        const FString S=Side?TEXT("r"):TEXT("l");auto& H=Hands[Side];
        H.Clavicle=Ref.FindBoneIndex(*(TEXT("clavicle_")+S));H.Upper=Ref.FindBoneIndex(*(TEXT("upperarm_")+S));
        H.Lower=Ref.FindBoneIndex(*(TEXT("lowerarm_")+S));H.Hand=Ref.FindBoneIndex(*(TEXT("hand_")+S));
        if(H.Clavicle<0||H.Upper<0||H.Lower<0||H.Hand<0)return;
        for(int32 I=0;I<Reference.Num();++I)if(I==H.Clavicle||Ref.BoneIsChildOf(I,H.Clavicle)){H.Bones.Add(I);ArmBones.Add(I);}
        const auto& J=Json->GetObjectField(TEXT("hands"))->GetObjectField(S);const auto& P=J->GetArrayField(TEXT("p"));
        H.Grip=FTransform(Quat(J->GetArrayField(TEXT("q"))),FVector(P[0]->AsNumber(),P[1]->AsNumber(),P[2]->AsNumber()));
    }
    for(const auto& Pair:Json->GetObjectField(TEXT("finger_rotations"))->Values)
    {const int32 I=Ref.FindBoneIndex(*Pair.Key);if(I>=0)Fingers.Add(I,Quat(Pair.Value->AsArray()));}
    bReady=true;
}
bool AAlchemyWorldView::Ready() const {return bReady&&Visual.IsValid()&&Visual->Ready();}
bool AAlchemyWorldView::Failed() const {return (bLoadFinished&&!bReady)||(Visual.IsValid()&&Visual->Failed());}
void AAlchemyWorldView::Enter()
{
    if(bEntered||!Ready()||!Player.IsValid())return;bEntered=true;PreviousView=Player->GetViewTarget();
    if(WorkingPawn.IsValid()&&!Player->HiddenActors.Contains(WorkingPawn.Get())){Player->HiddenActors.Add(WorkingPawn.Get());bHidPawn=true;}
    Tick(0);SetActorTickEnabled(true);Arms->SetVisibility(true);Player->SetViewTargetWithBlend(this,.35f,VTBlend_Cubic);
}
void AAlchemyWorldView::Leave()
{
    if(Visual.IsValid())Visual->SetHoverTarget({},false);
    if(!bEntered)return;bEntered=false;SetActorTickEnabled(false);Arms->SetVisibility(false);
    if(bHidPawn&&Player.IsValid()){Player->HiddenActors.Remove(WorkingPawn.Get());bHidPawn=false;}
    ColdSteelWorkstationView::Restore(Player.Get(),this,WorkingPawn.Get(),PreviousView.Get(),.25f);
}
void AAlchemyWorldView::Tick(float Dt)
{
    Super::Tick(Dt);if(!Ready()||!Station.IsValid())return;SetActorTransform(Station->Body()->GetComponentTransform());
    const auto ToolMode=Visual->HandTool();const bool Grind=ToolMode==EAlchemyOp::Grind;
    const bool Timer=ToolMode==EAlchemyOp::Timer;
    // A stable tabletop view keeps every physical control visible and mouse arcs stationary.
    Eye=AlchemyTabletop::Eye;Aim=AlchemyTabletop::Aim;
    Camera->SetRelativeLocationAndRotation(Eye,(Aim-Eye).Rotation());
    FTransform Tool=Visual->ToolGrip().GetRelativeTransform(GetActorTransform());
    const bool Bottle=ToolMode==EAlchemyOp::Bottle;
    const bool Acting=ToolMode==EAlchemyOp::Pour||Grind||ToolMode==EAlchemyOp::Stir||Bottle||Timer;
    FTransform Right=Hands[1].Grip*Tool;
    if(!Acting)Right=FTransform(Hands[1].Grip.GetRotation(),Eye+FVector(25,40,-51));
    const FTransform Left=(Bottle||ToolMode==EAlchemyOp::Pour)?Hands[0].Grip*Visual->BottleGrip().GetRelativeTransform(GetActorTransform()):FTransform(Hands[0].Grip.GetRotation(),Grind?FVector(39,-58,101):FVector(195,-133,113));
    // The torso has to sit within arm's reach of the wrist targets. Pinned behind
    // the lens it was 82-122 cm from them against a ~50 cm arm, so the reach
    // clamp fired every frame, teleported the shoulder to the bench and
    // stretched the shoulder skin into a hairline across the screen. Slide the
    // anchor from its shipped camera-side spot toward the working hands, and
    // take the FIRST position that brings those hands inside the safety band:
    // that keeps as much of the original framing as possible while removing the
    // stretch. Idle keeps the old anchor so the resting hands do not move.
    const FQuat BodyRotation(FVector::UpVector,PI*.5f);
    const FVector Base=Eye+FVector(0,-13,-35);
    const float ArmSpan=FVector::Distance(Reference[Hands[1].Upper].GetLocation(),Reference[Hands[1].Hand].GetLocation());
    const float Reaches=FMath::Max(1.f,ArmSpan);
    const float Limit=Reaches-.2f;
    const float SafeLimit=Limit*AlchemyReachSafety;
    // Only the hands that actually hold a tool steer the torso. Stir and Timer
    // park the left hand at a fixed spot on the far side of the bench; letting
    // that parked hand vote makes the two demands mutually unsatisfiable.
    const bool LeftWorks=Bottle||ToolMode==EAlchemyOp::Pour||Grind;
    FVector Anchor=Base;
    if(Acting)
    {
        const FVector Working[2]={Right.GetLocation(),Left.GetLocation()};
        const int32 WorkingCount=LeftWorks?2:1;
        FVector Center=FVector::ZeroVector;
        for(int32 I=0;I<WorkingCount;++I)Center+=Working[I];
        Center/=float(WorkingCount);
        const auto WorstReach=[&](const FVector& At)
        {
            float Worst=0.f;
            for(int32 I=0;I<WorkingCount;++I)Worst=FMath::Max(Worst,float(FVector::Distance(Working[I],At)));
            return Worst;
        };
        // Smallest slide that satisfies the working hands. 64 steps of ~1/64
        // of the span resolves the position far finer than a pixel.
        Anchor=Base;
        for(int32 Step=0;Step<=64;++Step)
        {
            const float T=Step/64.f;
            const FVector Candidate=FMath::Lerp(Base,Center,T);
            Anchor=Candidate;
            if(WorstReach(Candidate)<=SafeLimit)break;
        }
    }
    const FTransform Torso(BodyRotation,Anchor);Arms->SetRelativeTransform(Torso);
    for(int32 I=0;I<Reference.Num();++I)Pose[I]=Reference[I]*Torso;
    Solve(0,Left,Torso);Solve(1,Right,Torso);Arms->CommitStationPose(Pose,ArmBones);
}
void AAlchemyWorldView::Solve(int32 Side,const FTransform& Target,const FTransform& Torso)
{
    auto& H=Hands[Side];const auto& Ref=Arms->GetSkinnedAsset()->GetRefSkeleton();
    const float L1=FVector::Distance(Reference[H.Upper].GetLocation(),Reference[H.Lower].GetLocation());
    const float L2=FVector::Distance(Reference[H.Lower].GetLocation(),Reference[H.Hand].GetLocation());
    FVector Shoulder=Pose[H.Upper].GetLocation(),Wrist=Target.GetLocation();
    const FVector Axis=(Wrist-Shoulder).GetSafeNormal();const float D=FMath::Clamp(float(FVector::Distance(Wrist,Shoulder)),FMath::Abs(L1-L2)+.1f,L1+L2-.2f);
    // Keep the grasp on the actual tool; shoulder movement absorbs camera transitions.
    Shoulder=Wrist-Axis*D;
    FVector Pole=FVector(Side?1:-1,-.35,-.7);Pole=(Pole-Axis*(Pole|Axis)).GetSafeNormal();
    const float Along=(L1*L1-L2*L2+D*D)/(2*D);const FVector Elbow=Shoulder+Axis*Along+Pole*FMath::Sqrt(FMath::Max(0.f,L1*L1-Along*Along));
    const FVector RefUpper=Reference[H.Lower].GetLocation()-Reference[H.Upper].GetLocation();
    const FVector RefLower=Reference[H.Hand].GetLocation()-Reference[H.Lower].GetLocation();
    const FQuat Upper=FQuat::FindBetweenNormals(RefUpper.GetSafeNormal(),(Elbow-Shoulder).GetSafeNormal());
    const FQuat Lower=FQuat::FindBetweenNormals(RefLower.GetSafeNormal(),(Wrist-Elbow).GetSafeNormal());
    Pose[H.Clavicle]=FTransform(Upper*Reference[H.Clavicle].GetRotation(),Shoulder+Upper.RotateVector(Reference[H.Clavicle].GetLocation()-Reference[H.Upper].GetLocation()));
    Pose[H.Upper]=FTransform(Upper*Reference[H.Upper].GetRotation(),Shoulder);Pose[H.Lower]=FTransform(Lower*Reference[H.Lower].GetRotation(),Elbow);Pose[H.Hand]=Target;
    for(int32 I:H.Bones)
    {
        if(I==H.Clavicle||I==H.Upper||I==H.Lower||I==H.Hand)continue;
        FTransform Local=LocalReference[I];if(const auto* Q=Fingers.Find(I))
        {
            const auto Tool=Visual->HandTool();
            const bool Wide=(Side==1&&(Tool==EAlchemyOp::Pour||Tool==EAlchemyOp::Timer))||(Side==0&&Tool==EAlchemyOp::Bottle);
            Local.SetRotation(FQuat::Slerp(Local.GetRotation(),*Q,Wide?.72f:1.f).GetNormalized());
        }
        Pose[I]=Local*Pose[Ref.GetParentIndex(I)];
    }
}
void AAlchemyWorldView::EndPlay(const EEndPlayReason::Type R)
{Leave();if(Loading)Loading->CancelHandle();Super::EndPlay(R);}
