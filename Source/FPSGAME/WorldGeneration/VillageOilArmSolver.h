#pragma once
#include "CoreMinimal.h"
#include "ReferenceSkeleton.h"
#include "TwoBoneIK.h"

namespace VillageOilArmSolver
{
	struct FWristMetrics
	{
		double ForeTwistDeg = 0.0;
		double WristSwingDeg = 0.0;
		double Twist01SeamGapDeg = 0.0;
	};

	/** Build component-space native bind pose from the skeleton reference pose. */
	inline void BuildBindPose(const FReferenceSkeleton& Ref, TArray<FTransform>& OutBind)
	{
		OutBind = Ref.GetRefBonePose();
		for (int32 I = 0; I < OutBind.Num(); ++I)
		{
			const int32 Parent = Ref.GetParentIndex(I);
			if (Parent != INDEX_NONE)
			{
				OutBind[I] *= OutBind[Parent];
			}
		}
	}

	inline FTransform Grip(int Side, double Tilt, double Load)
	{
		// Fore-and-aft wooden handles at (0, +-18.9, 5.6).
		// Symmetrical inward-cradled carry stance aligned with the natural straight wrist;
		// right palm pronates smoothly as the right elbow rises across pour tilt.
		const double Angle = Side
			? (-36.0 + 12.0 * Tilt - 3.0 * Load)
			: (36.0 - 24.0 * Tilt + 4.0 * Load);
		const FQuat PalmRoll(FVector::ForwardVector, FMath::DegreesToRadians(Angle));
		return FTransform(
			PalmRoll * FRotationMatrix::MakeFromZX(FVector::ForwardVector, FVector::UpVector).ToQuat(),
			FVector(0, Side ? -18.9 : 18.9, 5.6));
	}

	inline FQuat HingeFrame(const FVector& Direction, const FVector& PlaneNormal)
	{
		return FRotationMatrix::MakeFromXZ(Direction, PlaneNormal).ToQuat();
	}

	inline void ApplyClavicleArticulation(const FReferenceSkeleton& Ref, TArray<FTransform>& Pose,
		int Side, double Tilt, double Push, double Load)
	{
		const int32 ClavL = Ref.FindBoneIndex(TEXT("clavicle_l"));
		const int32 ClavR = Ref.FindBoneIndex(TEXT("clavicle_r"));
		const int32 Clav = Side ? ClavL : ClavR;
		const int32 Upper = Ref.FindBoneIndex(Side ? TEXT("upperarm_l") : TEXT("upperarm_r"));
		if (!Pose.IsValidIndex(Clav) || !Pose.IsValidIndex(Upper)) return;

		const FTransform OldClav = Pose[Clav];
		const FVector ArmDir = (Pose[Upper].GetLocation() - OldClav.GetLocation()).GetSafeNormal();
		if (ArmDir.IsNearlyZero()) return;

		const FVector RightAxis = (Pose.IsValidIndex(ClavL) && Pose.IsValidIndex(ClavR))
			? (Pose[ClavR].GetLocation() - Pose[ClavL].GetLocation()).GetSafeNormal()
			: FVector::RightVector;
		const FVector SafeRight = RightAxis.IsNearlyZero() ? FVector::RightVector : RightAxis;
		const FVector FwdAxis = FVector::CrossProduct(SafeRight, FVector::UpVector).GetSafeNormal();
		const FVector SafeFwd = FwdAxis.IsNearlyZero() ? FVector::ForwardVector : FwdAxis;

		// Right shoulder lifts and protracts to drive the pour; left shoulder braces evenly.
		const double LiftDeg = Side ? (-1.5 - 2.0 * Tilt - 1.5 * Load) : (1.5 + 7.5 * Tilt + 2.5 * Push);
		const double FwdDeg = (2.5 * Push - 1.5 * Load) + (Side ? 1.5 : 4.5 * Tilt);
		const FVector DesiredDir = (ArmDir
			+ FVector::UpVector * FMath::Sin(FMath::DegreesToRadians(LiftDeg))
			+ SafeFwd * FMath::Sin(FMath::DegreesToRadians(FwdDeg))).GetSafeNormal();
		if (DesiredDir.IsNearlyZero()) return;

		const FQuat DeltaRot = FQuat::FindBetweenNormals(ArmDir, DesiredDir);
		FTransform NewClav = OldClav;
		NewClav.SetRotation((DeltaRot * OldClav.GetRotation()).GetNormalized());
		for (int32 I = Clav + 1; I < Pose.Num(); ++I)
		{
			if (!Ref.BoneIsChildOf(I, Clav)) continue;
			Pose[I] = Pose[I].GetRelativeTransform(OldClav) * NewClav;
		}
		Pose[Clav] = NewClav;
	}

	/**
	 * Ergonomic 2-bone arm solver with zero-twist-stacking forearm distribution.
	 * Builds upperarm/lowerarm hinge frames strictly from Native BindPose (immune to stale carry/locomotion roll)
	 * and reconstructs twist helpers from BindPose with continuous graduation up to 100% at wrist twist_01.
	 */
	inline void SolveErgonomicArm(const FReferenceSkeleton& Ref, const TArray<FTransform>& BindPose,
		TArray<FTransform>& Pose, int Side, const FVector& Target, const FVector& Pole,
		const TOptional<FQuat>& Rotation, double Tilt, double Push, double Load)
	{
		ApplyClavicleArticulation(Ref, Pose, Side, Tilt, Push, Load);

		const TCHAR* Suf = Side ? TEXT("_l") : TEXT("_r");
		const int32 Clav = Ref.FindBoneIndex(FName(*(FString(TEXT("clavicle")) + Suf)));
		const int32 Upper = Ref.FindBoneIndex(FName(*(FString(TEXT("upperarm")) + Suf)));
		const int32 Lower = Ref.FindBoneIndex(FName(*(FString(TEXT("lowerarm")) + Suf)));
		const int32 Hand = Ref.FindBoneIndex(FName(*(FString(TEXT("hand")) + Suf)));
		if (!Pose.IsValidIndex(Upper) || !Pose.IsValidIndex(Lower) || !Pose.IsValidIndex(Hand)) return;

		const TArray<FTransform>& SafeBind = BindPose.Num() == Pose.Num() ? BindPose : Pose;
		const TArray<FTransform> SourcePose = Pose;

		const FVector RU = SafeBind[Lower].GetLocation() - SafeBind[Upper].GetLocation();
		const FVector RL = SafeBind[Hand].GetLocation() - SafeBind[Lower].GetLocation();
		const double L1 = RU.Size();
		const double L2 = RL.Size();
		if (L1 <= SMALL_NUMBER || L2 <= SMALL_NUMBER) return;

		FVector Shoulder = SourcePose[Upper].GetLocation();
		const FVector ReachVec = Target - Shoulder;
		const double ComfortReach = (L1 + L2) * 0.945;
		FVector ClavShift = FVector::ZeroVector;
		if (ReachVec.SizeSquared() > ComfortReach * ComfortReach)
		{
			ClavShift = ReachVec.GetSafeNormal() * (ReachVec.Size() - ComfortReach);
			Shoulder += ClavShift;
		}

		FVector ElbowPos, WristPos;
		AnimationCore::SolveTwoBoneIK(Shoulder, Shoulder + RU, Shoulder + RU + RL, Pole, Target,
			ElbowPos, WristPos, L1, L2, false, 1.0, 1.0);

		const FVector UD = (ElbowPos - Shoulder).GetSafeNormal();
		const FVector LD = (WristPos - ElbowPos).GetSafeNormal();
		FVector Plane = (UD ^ LD).GetSafeNormal();
		if (Plane.IsNearlyZero()) Plane = (UD ^ (Pole - Shoulder)).GetSafeNormal();
		if (Plane.IsNearlyZero()) Plane = FVector::UpVector;
		FVector RestPlane = (RU ^ RL).GetSafeNormal();
		if (RestPlane.IsNearlyZero()) RestPlane = FVector::UpVector;

		FTransform HandPose = SafeBind[Hand];
		HandPose.SetLocation(WristPos);
		const FQuat CanonicalLower = (HingeFrame(LD, Plane) * HingeFrame(RL, RestPlane).Inverse()).GetNormalized();
		HandPose.SetRotation(Rotation.IsSet() ? Rotation.GetValue().GetNormalized() : (CanonicalLower * SafeBind[Hand].GetRotation()).GetNormalized());

		// Align forearm and upperarm organically to the actual hand orientation (Super90SupportArmNode pattern)
		// instead of forcing a rigid bind-plane roll that can oppose the grip by ~180 deg and wring the forearm mesh.
		const FQuat HandDeform = (HandPose.GetRotation() * SafeBind[Hand].GetRotation().Inverse()).GetNormalized();
		const FQuat LowerDeform = (FQuat::FindBetweenNormals(HandDeform.RotateVector(RL.GetSafeNormal()), LD) * HandDeform).GetNormalized();
		const FQuat UpperDeform = (FQuat::FindBetweenNormals(LowerDeform.RotateVector(RU.GetSafeNormal()), UD) * LowerDeform).GetNormalized();

		FTransform UpperPose = SafeBind[Upper];
		UpperPose.SetLocation(Shoulder);
		UpperPose.SetRotation((UpperDeform * SafeBind[Upper].GetRotation()).GetNormalized());

		FTransform LowerPose = SafeBind[Lower];
		LowerPose.SetLocation(ElbowPos);
		LowerPose.SetRotation((LowerDeform * SafeBind[Lower].GetRotation()).GetNormalized());

		// Shortest-arc axial twist between hand and forearm around LD guarantees zero wrist-seam pinch (0 deg gap).
		FQuat SwingPart, ForeTwist;
		(HandDeform * LowerDeform.Inverse()).GetNormalized().ToSwingTwist(LD, SwingPart, ForeTwist);
		ForeTwist.Normalize();
		if (ForeTwist.W < 0.0) ForeTwist = ForeTwist * -1.0;

		const int32 Twist01Idx = Ref.FindBoneIndex(FName(*(FString(TEXT("lowerarm_twist_01")) + Suf)));
		const int32 Twist02Idx = Ref.FindBoneIndex(FName(*(FString(TEXT("lowerarm_twist_02")) + Suf)));
		const double RLSq = FMath::Max(1.0, RL.SizeSquared());
		double Twist01Along = 0.0, Twist02Along = 0.0;
		if (SafeBind.IsValidIndex(Twist01Idx))
		{
			Twist01Along = FVector::DotProduct(SafeBind[Twist01Idx].GetLocation() - SafeBind[Lower].GetLocation(), RL) / RLSq;
		}
		if (SafeBind.IsValidIndex(Twist02Idx))
		{
			Twist02Along = FVector::DotProduct(SafeBind[Twist02Idx].GetLocation() - SafeBind[Lower].GetLocation(), RL) / RLSq;
		}
		const bool bHasBothTwists = SafeBind.IsValidIndex(Twist01Idx) && SafeBind.IsValidIndex(Twist02Idx);
		const int32 DistalTwistIdx = (bHasBothTwists && Twist02Along > Twist01Along) ? Twist02Idx : Twist01Idx;
		const int32 ProximalTwistIdx = (bHasBothTwists && Twist02Along > Twist01Along) ? Twist01Idx : Twist02Idx;

		const FVector Segment = WristPos - ElbowPos;
		const double SegSq = FMath::Max(1.0, Segment.SizeSquared());

		if (Pose.IsValidIndex(Clav) && !ClavShift.IsNearlyZero())
		{
			Pose[Clav].AddToTranslation(ClavShift);
		}

		for (int32 I = Upper + 1; I < Pose.Num(); ++I)
		{
			if (I == Hand || I == Lower) continue;

			if (Ref.BoneIsChildOf(I, Hand))
			{
				// Fingers keep authored wooden handle grasp relative to the wrist.
				Pose[I] = SourcePose[I].GetRelativeTransform(SourcePose[Hand]) * HandPose;
			}
			else if (Ref.BoneIsChildOf(I, Lower))
			{
				// Reconstruct every forearm helper strictly from Native BindPose (no double twist).
				FTransform Helper = SafeBind[I].GetRelativeTransform(SafeBind[Lower]) * LowerPose;
				const FString Name = Ref.GetBoneName(I).ToString();
				if (Name.Contains(TEXT("aux"), ESearchCase::IgnoreCase))
				{
					const FQuat ElbowDriver = FQuat::Slerp(UpperDeform, LowerDeform, 0.5).GetNormalized();
					Helper.SetRotation((ElbowDriver * SafeBind[I].GetRotation()).GetNormalized());
				}
				else
				{
					const FVector Offset = Helper.GetLocation() - ElbowPos;
					const double Along = FMath::Clamp(FVector::DotProduct(Offset, Segment) / SegSq, 0.0, 1.0);
					double Share = Along;
					if (I == DistalTwistIdx) Share = 1.0;
					else if (I == ProximalTwistIdx) Share = 0.50;
					const FQuat Roll = FQuat::Slerp(FQuat::Identity, ForeTwist, Share);
					Helper.SetLocation(ElbowPos + Roll.RotateVector(Offset));
					Helper.SetRotation((Roll * Helper.GetRotation()).GetNormalized());
				}
				Pose[I] = Helper;
			}
			else if (Ref.BoneIsChildOf(I, Upper))
			{
				Pose[I] = SafeBind[I].GetRelativeTransform(SafeBind[Upper]) * UpperPose;
			}
		}

		Pose[Upper] = UpperPose;
		Pose[Lower] = LowerPose;
		Pose[Hand] = HandPose;
	}

	/** Quantitative wrist joint audit: forearm twist, wrist deviation swing, and distal twist seam gap (degrees). */
	inline FWristMetrics MeasureWristAngles(const FReferenceSkeleton& Ref, const TArray<FTransform>& BindPose,
		const TArray<FTransform>& Pose, int Side)
	{
		FWristMetrics Out;
		const TCHAR* Suf = Side ? TEXT("_l") : TEXT("_r");
		const int32 Lower = Ref.FindBoneIndex(FName(*(FString(TEXT("lowerarm")) + Suf)));
		const int32 Hand = Ref.FindBoneIndex(FName(*(FString(TEXT("hand")) + Suf)));
		const int32 Twist01 = Ref.FindBoneIndex(FName(*(FString(TEXT("lowerarm_twist_01")) + Suf)));
		const int32 Twist02 = Ref.FindBoneIndex(FName(*(FString(TEXT("lowerarm_twist_02")) + Suf)));
		if (!Pose.IsValidIndex(Lower) || !Pose.IsValidIndex(Hand) || BindPose.Num() != Pose.Num()) return Out;

		const FVector LD = (Pose[Hand].GetLocation() - Pose[Lower].GetLocation()).GetSafeNormal();
		if (LD.IsNearlyZero()) return Out;

		const FQuat LowerDeform = (Pose[Lower].GetRotation() * BindPose[Lower].GetRotation().Inverse()).GetNormalized();
		const FQuat HandDeform = (Pose[Hand].GetRotation() * BindPose[Hand].GetRotation().Inverse()).GetNormalized();
		const int32 Middle = Ref.FindBoneIndex(FName(*(FString(TEXT("middle_01")) + Suf)));
		FQuat Swing, Twist;
		(HandDeform * LowerDeform.Inverse()).GetNormalized().ToSwingTwist(LD, Swing, Twist);
		Twist.Normalize();
		if (Twist.W < 0.0) Twist = Twist * -1.0;
		Swing.Normalize();
		if (Swing.W < 0.0) Swing = Swing * -1.0;
		Out.ForeTwistDeg = FMath::RadiansToDegrees(Twist.GetAngle());
		if (Pose.IsValidIndex(Middle))
		{
			const FVector PalmDir = (Pose[Middle].GetLocation() - Pose[Hand].GetLocation()).GetSafeNormal();
			const FVector BindPalm = (BindPose[Middle].GetLocation() - BindPose[Hand].GetLocation()).GetSafeNormal();
			const FVector BindLD = (BindPose[Hand].GetLocation() - BindPose[Lower].GetLocation()).GetSafeNormal();
			const double CurDeg = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(LD, PalmDir), -1.0, 1.0)));
			const double BindDeg = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(BindLD, BindPalm), -1.0, 1.0)));
			Out.WristSwingDeg = FMath::Abs(CurDeg - BindDeg);
		}
		else
		{
			Out.WristSwingDeg = FMath::RadiansToDegrees(Swing.GetAngle());
		}

		// Pick whichever lowerarm_twist bone sits closest to the wrist in bind pose.
		int32 DistalIdx = Twist01;
		if (Pose.IsValidIndex(Twist01) && Pose.IsValidIndex(Twist02))
		{
			const FVector RL = BindPose[Hand].GetLocation() - BindPose[Lower].GetLocation();
			const double A1 = FVector::DotProduct(BindPose[Twist01].GetLocation() - BindPose[Lower].GetLocation(), RL);
			const double A2 = FVector::DotProduct(BindPose[Twist02].GetLocation() - BindPose[Lower].GetLocation(), RL);
			if (A2 > A1) DistalIdx = Twist02;
		}
		if (Pose.IsValidIndex(DistalIdx))
		{
			const FQuat DistalDeform = (Pose[DistalIdx].GetRotation() * BindPose[DistalIdx].GetRotation().Inverse()).GetNormalized();
			FQuat GapSwing, GapTwist;
			(HandDeform * DistalDeform.Inverse()).GetNormalized().ToSwingTwist(LD, GapSwing, GapTwist);
			GapTwist.Normalize();
			if (GapTwist.W < 0.0) GapTwist = GapTwist * -1.0;
			Out.Twist01SeamGapDeg = FMath::RadiansToDegrees(GapTwist.GetAngle());
		}
		return Out;
	}
}
