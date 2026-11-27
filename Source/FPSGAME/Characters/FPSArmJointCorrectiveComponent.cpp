#include "FPSArmJointCorrectiveComponent.h"
#include "Animation/MorphTarget.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

namespace
{
TAutoConsoleVariable<int32> CVarArmCorrectives(TEXT("fps.Arms.JointCorrectives"),1,
    TEXT("1 = drive the JC_ elbow/wrist corrective morphs on first-person arms, 0 = plain linear skinning."));

// Key poses of correctives.py: elbow angles (deg between upper arm and forearm) and wrist swing keys.
constexpr float ElbowKeys[3]={75.f,110.f,135.f};
constexpr float ElbowExtensionKey=20.f;     // the extended elbow of the held rifle poses
constexpr float FlexKey=40.f,RadialKey=20.f,UlnarKey=35.f;
// Grip examples: radial basis width on the MCP angles past bind (grip_correctives.py SIGMA).
constexpr float GripSigma=12.f;
// Pose examples: widths of elbow, wrist flexion, deviation, hand roll and the four MCP angles (pose_examples.py).
constexpr float PoseSigma[8]={12.f,12.f,10.f,20.f,15.f,15.f,15.f,15.f};
// Radial-basis weights below this are dropped (removed from the active morphs; < 0.03 mm at the 2.5 cm reach).
constexpr float MinExampleWeight=1e-3f;
const TCHAR* Fingers[4]={TEXT("index"),TEXT("middle"),TEXT("ring"),TEXT("pinky")};

float ParseSigned(const FString& S)
{
    return S.StartsWith(TEXT("m"))?-FCString::Atof(*S.Mid(1)):FCString::Atof(*S);
}

float Angle(const FVector& A,const FVector& B)
{
    return FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(A.GetSafeNormal()|B.GetSafeNormal(),-1.f,1.f)));
}

float Tent(float X,float A,float B,float C)
{
    return X<=B?FMath::Clamp((X-A)/(B-A),0.f,1.f):FMath::Clamp((C-X)/(C-B),0.f,1.f);
}

void SetMorphCached(USkeletalMeshComponent* Mesh,FName Name,float& Cached,float Value)
{
    if(!FMath::IsNearlyEqual(Cached,Value,1e-4f))
    {
        Cached=Value;
        Mesh->SetMorphTarget(Name,Value,true);
    }
}
}

UFPSArmJointCorrectiveComponent::UFPSArmJointCorrectiveComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    // After the weapon pose has been sampled for this frame; the next evaluation applies the weights.
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

bool UFPSArmJointCorrectiveComponent::Build(USkeletalMeshComponent* Mesh,const TArray<const USkeletalMesh*>& Carriers,FRig& Out)
{
    const USkeletalMesh* Asset=Mesh?Mesh->GetSkeletalMeshAsset():nullptr;
    if(!Asset||Carriers.IsEmpty())return false;
    const FReferenceSkeleton& Ref=Asset->GetRefSkeleton();
    TArray<FTransform> Space=Ref.GetRefBonePose();
    for(int32 I=0;I<Space.Num();++I)if(const int32 P=Ref.GetParentIndex(I);P!=INDEX_NONE)Space[I]=Space[I]*Space[P];
    Out.Mesh=Mesh;Out.Asset=Asset;
    Out.Carriers.Reset(Carriers.Num());
    for(const USkeletalMesh* Carrier:Carriers)Out.Carriers.Add(Carrier);
    for(int32 S=0;S<2;++S)
    {
        const TCHAR* Suffix=S==0?TEXT("_l"):TEXT("_r");const TCHAR* Up=S==0?TEXT("_L"):TEXT("_R");
        const auto Find=[&](const TCHAR* Name){return Ref.FindBoneIndex(FName(FString(Name)+Suffix));};
        FSide& D=Out.Sides[S];
        D.Upper=Find(TEXT("upperarm"));D.Lower=Find(TEXT("lowerarm"));D.Hand=Find(TEXT("hand"));
        D.Twist=Find(TEXT("lowerarm_twist_01"));D.Middle=Find(TEXT("middle_01"));
        const int32 Index=Find(TEXT("index_metacarpal")),Pinky=Find(TEXT("pinky_metacarpal"));
        D.bValid=D.Upper!=INDEX_NONE&&D.Lower!=INDEX_NONE&&D.Hand!=INDEX_NONE&&D.Twist!=INDEX_NONE&&D.Middle!=INDEX_NONE
            &&Index!=INDEX_NONE&&Pinky!=INDEX_NONE;
        if(!D.bValid)continue;
        // Same wrist basis as the authoring script, stored in the reference lowerarm_twist_01 frame.
        const FVector F0=(Space[D.Middle].GetLocation()-Space[D.Hand].GetLocation()).GetSafeNormal();
        FVector R0=Space[Index].GetLocation()-Space[Pinky].GetLocation();R0=(R0-(R0|F0)*F0).GetSafeNormal();
        const FQuat Twist=Space[D.Twist].GetRotation();
        D.F0=Twist.UnrotateVector(F0);D.R0=Twist.UnrotateVector(R0);D.Z0=Twist.UnrotateVector(F0^R0);
        const FVector U=(Space[D.Lower].GetLocation()-Space[D.Upper].GetLocation()).GetSafeNormal();
        const FVector Fw=(Space[D.Hand].GetLocation()-Space[D.Lower].GetLocation()).GetSafeNormal();
        D.RestElbow=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(U|Fw,-1.f,1.f)));
        for(int32 K=0;K<3;++K)D.Elbow[K]=FName(FString::Printf(TEXT("JC_ElbowFlex%d%s"),FMath::RoundToInt(ElbowKeys[K]),Up));
        D.ElbowExtension=FName(FString::Printf(TEXT("JC_ElbowFlex%d%s"),FMath::RoundToInt(ElbowExtensionKey),Up));
        const TCHAR* Wrist[]={TEXT("JC_WristFlexA"),TEXT("JC_WristFlexB"),TEXT("JC_WristRadial"),TEXT("JC_WristUlnar")};
        for(int32 K=0;K<4;++K)D.Wrist[K]=FName(FString(Wrist[K])+Up);
        for(int32 K=0;K<4;++K)
        {
            D.Meta[K]=Find(*FString::Printf(TEXT("%s_metacarpal"),Fingers[K]));
            D.Prox[K]=Find(*FString::Printf(TEXT("%s_01"),Fingers[K]));D.Mid[K]=Find(*FString::Printf(TEXT("%s_02"),Fingers[K]));
            if(D.Meta[K]==INDEX_NONE||D.Prox[K]==INDEX_NONE||D.Mid[K]==INDEX_NONE)continue;
            D.RestMCP[K]=Angle(Space[D.Prox[K]].GetLocation()-Space[D.Meta[K]].GetLocation(),Space[D.Mid[K]].GetLocation()-Space[D.Prox[K]].GetLocation());
        }
        const FQuat LowerRef=Space[D.Lower].GetRotation();
        D.RelHand=LowerRef.Inverse()*Space[D.Hand].GetRotation();
        D.AxisL=LowerRef.UnrotateVector((Space[D.Hand].GetLocation()-Space[D.Lower].GetLocation()).GetSafeNormal());
        const FString GripPrefix=FString::Printf(TEXT("JC_Grip%s_"),Up),PosePrefix=FString::Printf(TEXT("JC_Pose%s_"),Up);
        for(const USkeletalMesh* Carrier:Carriers)for(const UMorphTarget* Morph:Carrier->GetMorphTargets())
        {
            const FString Name=Morph?Morph->GetName():FString();
            TArray<FString> Parts;Name.ParseIntoArray(Parts,TEXT("_"));
            if(Name.StartsWith(GripPrefix)&&Parts.Num()==7&&!D.Grips.ContainsByPredicate([&Name](const FSide::FGrip& G){return G.Name==FName(*Name);}))
            {
                FSide::FGrip& Grip=D.Grips.AddDefaulted_GetRef();Grip.Name=FName(*Name);
                for(int32 K=0;K<4;++K)Grip.Extra[K]=FCString::Atof(*Parts[3+K]);
            }
            else if(Name.StartsWith(PosePrefix)&&Parts.Num()==11&&!D.Poses.ContainsByPredicate([&Name](const FSide::FPoseEx& P){return P.Name==FName(*Name);}))
            {
                FSide::FPoseEx& Ex=D.Poses.AddDefaulted_GetRef();Ex.Name=FName(*Name);
                for(int32 K=0;K<8;++K)Ex.Sig[K]=ParseSigned(Parts[3+K]);
            }
        }
    }
    return Out.Sides[0].bValid||Out.Sides[1].bValid;
}

void UFPSArmJointCorrectiveComponent::Rescan()
{
    // Group every mesh that carries correctives under the component whose pose it shows.
    TMap<USkeletalMeshComponent*,TArray<const USkeletalMesh*>> Sources;
    TArray<USkeletalMeshComponent*> Meshes;GetOwner()->GetComponents(Meshes);
    for(USkeletalMeshComponent* Mesh:Meshes)
    {
        const USkeletalMesh* Asset=Mesh?Mesh->GetSkeletalMeshAsset():nullptr;
        if(!Asset||(!Asset->FindMorphTarget(TEXT("JC_ElbowFlex75_L"))&&!Asset->FindMorphTarget(TEXT("JC_ElbowFlex75_R"))))continue;
        USkeletalMeshComponent* Source=Cast<USkeletalMeshComponent>(Mesh->LeaderPoseComponent.Get());
        Sources.FindOrAdd(Source?Source:Mesh).AddUnique(Asset);
    }
    bool bSame=Rigs.Num()==Sources.Num();
    if(bSame)
    {
        for(const auto& Pair:Sources)
        {
            const USkeletalMesh* SourceAsset=Pair.Key?Pair.Key->GetSkeletalMeshAsset():nullptr;
            const FRig* Existing=Rigs.FindByPredicate([&](const FRig& Rig){return Rig.Mesh.Get()==Pair.Key&&Rig.Asset.Get()==SourceAsset;});
            if(!Existing||Existing->Carriers.Num()!=Pair.Value.Num()){bSame=false;break;}
            for(int32 I=0;I<Pair.Value.Num();++I)
                if(Existing->Carriers[I].Get()!=Pair.Value[I]){bSame=false;break;}
            if(!bSame)break;
        }
    }
    if(bSame)return;
    Rigs.Reset();
    for(const auto& Pair:Sources){FRig Rig;if(Build(Pair.Key,Pair.Value,Rig))Rigs.Add(MoveTemp(Rig));}
}

void UFPSArmJointCorrectiveComponent::Drive(USkeletalMeshComponent* Mesh,FSide& D)
{
    const TArray<FTransform>& Pose=Mesh->GetComponentSpaceTransforms();
    if(!D.bValid||!Pose.IsValidIndex(D.Middle)||!Pose.IsValidIndex(D.Twist))return;
    const FVector U=(Pose[D.Lower].GetLocation()-Pose[D.Upper].GetLocation()).GetSafeNormal();
    const FVector F=(Pose[D.Hand].GetLocation()-Pose[D.Lower].GetLocation()).GetSafeNormal();
    const float Elbow=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(U|F,-1.f,1.f)));
    SetMorphCached(Mesh,D.Elbow[0],D.LastElbow[0],Tent(Elbow,D.RestElbow,ElbowKeys[0],ElbowKeys[1]));
    SetMorphCached(Mesh,D.Elbow[1],D.LastElbow[1],Tent(Elbow,ElbowKeys[0],ElbowKeys[1],ElbowKeys[2]));
    SetMorphCached(Mesh,D.Elbow[2],D.LastElbow[2],FMath::Clamp((Elbow-ElbowKeys[1])/(ElbowKeys[2]-ElbowKeys[1]),0.f,1.f));
    if(D.RestElbow>ElbowExtensionKey+1.f)
        SetMorphCached(Mesh,D.ElbowExtension,D.LastElbowExtension,FMath::Clamp((D.RestElbow-Elbow)/(D.RestElbow-ElbowExtensionKey),0.f,1.f));
    const FVector H=Pose[D.Twist].GetRotation().UnrotateVector(Pose[D.Middle].GetLocation()-Pose[D.Hand].GetLocation()).GetSafeNormal();
    const float Along=H|D.F0;
    const float Flex=FMath::RadiansToDegrees(FMath::Atan2(-(H|D.Z0),Along));
    const float Dev=FMath::RadiansToDegrees(FMath::Atan2(H|D.R0,Along));
    // Unphysical swings (some sprint poses) fade the wrist keys out rather than apply a mismatched correction.
    const float Sane=1.f-FMath::SmoothStep(95.f,135.f,FMath::Max(FMath::Abs(Flex),FMath::Abs(Dev)));
    SetMorphCached(Mesh,D.Wrist[0],D.LastWrist[0],FMath::Clamp(Flex/FlexKey,0.f,1.f)*Sane);
    SetMorphCached(Mesh,D.Wrist[1],D.LastWrist[1],FMath::Clamp(-Flex/FlexKey,0.f,1.f)*Sane);
    SetMorphCached(Mesh,D.Wrist[2],D.LastWrist[2],FMath::Clamp(Dev/RadialKey,0.f,1.f)*Sane);
    SetMorphCached(Mesh,D.Wrist[3],D.LastWrist[3],FMath::Clamp(-Dev/UlnarKey,0.f,1.f)*Sane);
    if(D.Grips.IsEmpty()&&D.Poses.IsEmpty())return;
    float Extra[4];
    for(int32 K=0;K<4;++K)
    {
        if(!Pose.IsValidIndex(D.Meta[K])||!Pose.IsValidIndex(D.Prox[K])||!Pose.IsValidIndex(D.Mid[K]))return;
        Extra[K]=FMath::Max(0.f,Angle(Pose[D.Prox[K]].GetLocation()-Pose[D.Meta[K]].GetLocation(),Pose[D.Mid[K]].GetLocation()-Pose[D.Prox[K]].GetLocation())-D.RestMCP[K]);
    }
    FQuat Rel=Pose[D.Lower].GetRotation().Inverse()*Pose[D.Hand].GetRotation()*D.RelHand.Inverse();
    if(Rel.W<0.f)Rel=FQuat(-Rel.X,-Rel.Y,-Rel.Z,-Rel.W);
    const float Roll=(float)FMath::RadiansToDegrees(2.0*FMath::Atan2(FVector(Rel.X,Rel.Y,Rel.Z)|D.AxisL,(double)Rel.W));
    const float Sig[8]={Elbow,Flex,Dev,Roll,Extra[0],Extra[1],Extra[2],Extra[3]};
    if(D.bHasLastSig)
    {
        bool bPoseChanged=false;
        for(int32 K=0;K<8;++K)
        {
            const float Delta=K==3?FMath::Abs(FMath::UnwindDegrees(Sig[K]-D.LastSig[K])):FMath::Abs(Sig[K]-D.LastSig[K]);
            if(Delta>=0.05f){bPoseChanged=true;break;}
        }
        if(!bPoseChanged)return;
    }
    for(int32 K=0;K<8;++K)D.LastSig[K]=Sig[K];
    D.bHasLastSig=true;
    for(FSide::FGrip& Grip:D.Grips)
    {
        float Distance=0.f;
        for(int32 K=0;K<4;++K)Distance+=FMath::Square((Extra[K]-Grip.Extra[K])/GripSigma);
        const float Weight=FMath::Exp(-.5f*Distance);
        SetMorphCached(Mesh,Grip.Name,Grip.LastWeight,Weight<MinExampleWeight?0.f:Weight);
    }
    if(D.Poses.IsEmpty())return;
    for(FSide::FPoseEx& Ex:D.Poses)
    {
        float Distance=0.f;
        for(int32 K=0;K<8;++K)
        {
            float Delta=Sig[K]-Ex.Sig[K];
            if(K==3)Delta=FMath::UnwindDegrees(Delta);
            Distance+=FMath::Square(Delta/PoseSigma[K]);
        }
        const float Weight=FMath::Exp(-.5f*Distance);
        SetMorphCached(Mesh,Ex.Name,Ex.LastWeight,Weight<MinExampleWeight?0.f:Weight);
    }
}

void UFPSArmJointCorrectiveComponent::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()==NM_DedicatedServer)SetComponentTickEnabled(false);
}

bool UFPSArmJointCorrectiveComponent::IsShownLocally() const
{
    const AActor* Owner=GetOwner();
    if(const APawn* Pawn=Cast<APawn>(Owner);Pawn&&Pawn->IsLocallyControlled())return true;
    if(const UWorld* World=GetWorld())
        for(FConstPlayerControllerIterator It=World->GetPlayerControllerIterator();It;++It)
            if(const APlayerController* PC=It->Get();PC&&PC->IsLocalController()&&PC->GetViewTarget()==Owner)return true;
    return false;
}

void UFPSArmJointCorrectiveComponent::TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime,TickType,ThisTickFunction);
    if(!IsShownLocally())
    {
        // Remote players' first-person arms are never seen here; rebuild at once when this pawn is viewed.
        Rigs.Reset();RescanTimer=0.f;return;
    }
    if((RescanTimer-=DeltaTime)<=0.f){RescanTimer=.25f;Rescan();}
    const bool bEnabled=CVarArmCorrectives.GetValueOnGameThread()!=0;
    for(FRig& Rig:Rigs)
    {
        USkeletalMeshComponent* Mesh=Rig.Mesh.Get();
        if(!Mesh||!Mesh->IsRegistered()||Mesh->GetSkeletalMeshAsset()!=Rig.Asset.Get())continue;
        if(!bEnabled)
        {
            if(bWasEnabled)
            {
                for(FSide& D:Rig.Sides)
                {
                    for(int32 K=0;K<3;++K){D.LastElbow[K]=-1.f;Mesh->SetMorphTarget(D.Elbow[K],0.f,true);}
                    D.LastElbowExtension=-1.f;
                    Mesh->SetMorphTarget(D.ElbowExtension,0.f,true);
                    for(int32 K=0;K<4;++K){D.LastWrist[K]=-1.f;Mesh->SetMorphTarget(D.Wrist[K],0.f,true);}
                    for(FSide::FGrip& Grip:D.Grips){Grip.LastWeight=-1.f;Mesh->SetMorphTarget(Grip.Name,0.f,true);}
                    for(FSide::FPoseEx& Ex:D.Poses){Ex.LastWeight=-1.f;Mesh->SetMorphTarget(Ex.Name,0.f,true);}
                    D.bHasLastSig=false;
                }
            }
            continue;
        }
        // No visibility test: a leader whose own skin sections are hidden still poses visible followers.
        for(FSide& D:Rig.Sides)Drive(Mesh,D);
    }
    bWasEnabled=bEnabled;
}
