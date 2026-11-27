#pragma once

#include "CoreMinimal.h"
#include "Algo/BinarySearch.h"
#include "TemperateVillageSite.h"

/**
 * Canonical road centerline connecting the restored Lumber Mill courtyard
 * (15400, 6200) along the R49 contour-matched logging road, through the
 * village gate approach, and into the village central plaza along the main street.
 *
 * Single source of truth shared by:
 *  - M-key world map golden supply route & flowing light VFX
 *  - Future 17:00 timber transport wagon route in L_ForestPathVillage
 */
namespace LumberMillSupplyRoute
{
    // Sampled directly from LumberMill-R49 Terrain/lumber-road.csv & gate-road.csv (world XY cm).
    inline const FVector2D ExteriorKnotsCm[] = {
        {15400.0, 6200.0},
        {15400.0, 6750.0},
        {15400.0, 7300.0},
        {15356.1, 7748.3},
        {15330.4, 8197.8},
        {15342.9, 8647.9},
        {15368.7, 9097.6},
        {15377.5, 9547.9},
        {15373.4, 9998.3},
        {15419.4, 10445.5},
        {15560.0, 10872.9},
        {15709.5, 11297.5},
        {15833.1, 11730.6},
        {15979.6, 12156.5},
        {16100.9, 12590.0},
        {16183.1, 13032.8},
        {16245.4, 13478.8},
        {16266.3, 13928.5},
        {16220.2, 14375.9},
        {16107.6, 14811.8},
        {15962.4, 15238.1},
        {15824.2, 15666.7},
        {15708.7, 16102.0},
        {15616.5, 16542.9},
        {15536.6, 16986.1},
        {15428.1, 17423.1},
        {15286.0, 17850.4},
        {15139.0, 18276.2},
        {15007.5, 18706.9},
        {14887.2, 19141.0},
        {14758.8, 19572.7},
        {14618.8, 20000.8},
        {14482.2, 20429.9},
        {14378.4, 20867.9},
        {14343.2, 21316.5},
        {14353.1, 21766.7},
        {14349.3, 22217.0},
        {14294.7, 22663.7},
        {14186.5, 23100.8},
        {14053.0, 23530.9},
        {13899.6, 23954.4},
        {13731.7, 24372.3},
        {13547.4, 24783.3},
        {13353.4, 25189.7},
        {13167.9, 25600.2},
        {12985.7, 26012.1},
        {12831.2, 26435.0},
        {12694.2, 26864.1},
        {12530.7, 27283.4},
        {12297.0, 27667.8},
        {12040.7, 28038.2},
        {11791.1, 28413.0},
        {11514.0, 28768.0},
        {11224.5, 29113.1},
        {10940.7, 29462.7},
        {10667.1, 29820.6},
        {10374.0, 30162.2},
        {10036.7, 30460.1},
        {9677.1, 30731.4},
        {9323.0, 31009.7},
        {8989.9, 31312.6},
        {8885.0, 31420.0},
        {8892.7, 31483.6},
        {8899.9, 31876.3},
        {8900.0, 32271.6},
        {8900.0, 32700.0},
    };

    // Village-local street knots (cm) from East Gate along main street, turning north along the 5.6 m Tavern road
    // and pulling smoothly into the flat EAST (+X) forecourt bay (Tavern local (+470, -825), opposite the West Hitching Rail
    // / 三马位 X=[-675..-10], leaving the entire 2.5+ m Tavern front doorway corridor 100% clear!).
    inline const FVector2D VillageStreetLocalCm[] = {
        {5550.0, 500.0},
        {4600.0, 500.0},
        {4500.0, 500.0},
        {4200.0, 620.0},
        {3900.0, 820.0},
        {2800.0, 800.0},
        {1500.0, 800.0},
        {400.0, 750.0},
        {-300.0, 550.0},
        {-1075.0, 200.0},
        {-1205.0, 615.0},
        {-1335.0, 1165.0},
        {-1317.5, 1347.0},
        {-1204.5, 1656.9},
        {-1065.8, 1923.9},
        {-931.3, 2055.5},
        {-796.8, 2091.7},
        {-617.3, 2077.8},
        {-438.3, 2059.0},
    };

    inline void BuildWorldPolyline(const FTemperateVillageSite& Village, TArray<FVector2D>& OutPoints,
        TArray<double>& OutCumulativeCm, double& OutTotalCm)
    {
        OutPoints.Reset(UE_ARRAY_COUNT(ExteriorKnotsCm) + UE_ARRAY_COUNT(VillageStreetLocalCm));
        OutCumulativeCm.Reset(UE_ARRAY_COUNT(ExteriorKnotsCm) + UE_ARRAY_COUNT(VillageStreetLocalCm));
        OutTotalCm = 0.0;

        auto AppendPoint = [&](const FVector2D& Pt)
        {
            if (!OutPoints.IsEmpty())
            {
                const double Seg = FVector2D::Distance(OutPoints.Last(), Pt);
                if (Seg < 1.0) return;
                OutTotalCm += Seg;
            }
            OutPoints.Add(Pt);
            OutCumulativeCm.Add(OutTotalCm);
        };

        for (const FVector2D& Pt : ExteriorKnotsCm)
        {
            AppendPoint(Pt);
        }
        if (Village.bPlaced)
        {
            for (const FVector2D& Local : VillageStreetLocalCm)
            {
                AppendPoint(Village.World(Local.X, Local.Y));
            }
        }
    }

    inline bool SampleAtDistance(const TArray<FVector2D>& Points, const TArray<double>& CumulativeCm,
        double DistanceCm, FVector2D& OutPos, FVector2D& OutTangent)
    {
        const int32 Count = Points.Num();
        if (Count < 2 || CumulativeCm.Num() != Count) return false;
        const double Total = CumulativeCm.Last();
        const double Clamped = FMath::Clamp(DistanceCm, 0.0, Total);
        int32 Hi = Algo::LowerBound(CumulativeCm, Clamped);
        Hi = FMath::Clamp(Hi, 1, Count - 1);
        const int32 Lo = Hi - 1;
        const double Span = FMath::Max(1e-4, CumulativeCm[Hi] - CumulativeCm[Lo]);
        const double Alpha = FMath::Clamp((Clamped - CumulativeCm[Lo]) / Span, 0.0, 1.0);
        OutPos = FMath::Lerp(Points[Lo], Points[Hi], Alpha);
        OutTangent = (Points[Hi] - Points[Lo]).GetSafeNormal();
        return true;
    }
}
