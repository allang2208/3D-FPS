#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"

namespace ASH12Attachments
{
    inline FString MeshPath(const FString& Key)
    {
        return FString::Printf(TEXT("/Game/Weapons/ASH12/UniversalAttachments20260919/Meshes/SM_ASH12_%s.SM_ASH12_%s"), *Key, *Key);
    }

    inline UStaticMeshComponent* Configure(AActor* Owner, USkeletalMeshComponent* Rifle,
        UStaticMeshComponent* Part, const TCHAR* Family, bool bEnabled)
    {
        if (Part) Part->SetVisibility(false);
        if (!bEnabled || !Rifle || !Rifle->GetSkeletalMeshAsset()) return Part;
        auto* Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath(Family));
        if (!Mesh) return Part;
        const auto& Ref = Rifle->GetSkeletalMeshAsset()->GetRefSkeleton();
        auto Bone = [&](const TCHAR* Name)
        {
            FTransform T = FTransform::Identity;
            for (int32 Index = Ref.FindBoneIndex(Name); Index != INDEX_NONE; Index = Ref.GetParentIndex(Index))
                T = T * Ref.GetRefBonePose()[Index];
            return T;
        };
        const FTransform Root = Bone(TEXT("WPN_root")), Rear = Bone(TEXT("WPN_RearSight"));
        const FVector Forward = (Bone(TEXT("WPN_FrontSight")).GetLocation() - Rear.GetLocation()).GetSafeNormal();
        const FQuat Rotation = FRotationMatrix::MakeFromXZ(Forward, Rear.GetRotation().GetAxisZ()).ToQuat();
        // ASH lower rail crown, measured in its authored sight frame (cm).
        // Shared body dimensions stay intact; each exported shoe seats at Z=0.
        const float Along = FCString::Strcmp(Family, TEXT("angled")) == 0 ? 32.f : 30.f;
        const FTransform Mount(Rotation, Rear.GetLocation() + Rotation.RotateVector(FVector(Along, -.0439f, -14.0265f)));
        if (!Part)
        {
            Part = NewObject<UStaticMeshComponent>(Owner);
            Part->SetupAttachment(Rifle, TEXT("WPN_root"));
            Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Part->SetCastShadow(false);
            Part->bReceivesDecals = false;
            Part->RegisterComponent();
        }
        if (Part->GetStaticMesh() != Mesh) Part->EmptyOverrideMaterials();
        Part->SetStaticMesh(Mesh);
        Part->SetRelativeTransform(Mount.GetRelativeTransform(Root));
        Part->SetVisibility(true);
        return Part;
    }
}
