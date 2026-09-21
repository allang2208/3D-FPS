#pragma once

// Shared joint-strength maths for the 20 cm voxel building system.
//
// Deliberately plain C++ with no Unreal headers: the game module uses it to print the building
// panel tooltip, and Tools/Building/voxel_stress_probe.cpp compiles the same code offline so the
// published span/load numbers can always be re-derived from the shipped solver.
//
// Model (mirrors VoxelSupportGraph.cpp::VoxelStress::Solve):
//   - nodes are 20 cm cells, positions in METRES, mass kg, inertia m*0.04/6, gravity -9.81
//   - bonds are face contacts (centroid at the shared face centre) plus one ground bond per
//     bottom cell into a massless world node
//   - failure stress: compression = max(0,-F.n/A)+bend, tension = max(0,F.n/A)+bend,
//     bend = |M_perp|*6/(A*min(w,h)) which is the 20x20 cm section modulus, plus shear
//   - a bond "breaks" when any stress exceeds its material limit

#include "FPSBlast.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <mutex>
#include <vector>

namespace VoxelJointStrength
{
    inline constexpr double CellM = 0.2;
    inline constexpr double AreaM2 = 0.04;      // full 20 x 20 cm face
    inline constexpr double LeverM = 0.2;
    inline constexpr double GravityMS2 = -9.81;

    /**
     * 过载到失效的秒数（2026-09-16 用户指定 30 s 上限）：刚好过线时约 GraceSeconds，越超载越快，
     * 最低 MinSeconds。时间与材质无关——材质只决定每秒损伤的数值（= 自身耐久 / 该秒数）。
     */
    inline double OverloadSecondsToFailure(double Ratio, double GraceSeconds = 30.0, double MinSeconds = 3.0)
    {
        if (Ratio <= 1.0) return GraceSeconds;
        return std::max(MinSeconds, std::min(GraceSeconds, GraceSeconds / Ratio));
    }

    struct FMaterial
    {
        double DensityKgM3 = 600.0;
        double CompressionPa = 350000.0;
        double TensionPa = 130000.0;
        double ShearPa = 60000.0;
        double MassPerCellKg() const { return DensityKgM3 * 0.008; }
        /** Static load a 1 m^2 cross section carries before compression failure, in tonnes. */
        double LoadPerSquareMeterT() const { return CompressionPa / 9.81 / 1000.0; }
    };

    struct FCell { int X = 0, Y = 0, Z = 0; };

    namespace Detail
    {
        /**
         * 格坐标 → 节点下标 的稀疏查找表（审计 P4 + C1 修复）。
         *
         * 原实现是 `static long long Lookup[64*64*64]`（**2 MB**）并**每次 Ratio() 调用**用
         * std::fill 整个清零。Room() 只写入约 (10 + 5*(SpanCells+2)) 个格键，按当前坐标范围
         * （X 0..4、Y 0..SpanCells+1、Z 0..5）算，写入的槽位不到表容量的 0.2%——也就是说
         * 每次调用有 99.8% 的清零是纯浪费。面板初始化要扫 3 材质 × 2 口径 × 25 跨 ≈ 150 次，
         * 合计约 300 MB 的内存写入，正是文档里"一次性 0.2–0.5 s"的真正来源。
         *
         * 换成开放寻址哈希表：容量固定（0x4000，远大于任何 Room() 的格数），但**不需要每次清零**
         * ——用「填充游标」判定槽位是否属于本次调用：槽位里存的代（generation）等于当前代
         * 才表示有效。代在每次 Clear() 时自增，因此上一次调用残留的数据不会命中。
         *
         * C1（数据竞争）：原 `static` 数组被游戏线程与线程池共享且无同步，是真实的数据竞争。
         * 容量不能像原来那样缩到栈上（稀疏键的哈希表需要上千槽），所以保留 `static` 并加锁
         * 串行化——这把原来"静默算错跨度"的竞争变成"正确但排队"。锁只在 Ratio() 期间持有。
         * 本 header 是纯 C++（与离线探针共用），故用 std::mutex 而非 UE 的临界区。
         */
        constexpr int32_t LookupCapacity = 0x4000;   // 16384 槽
        constexpr int32_t LookupMask = LookupCapacity - 1;

        inline uint32_t HashCell(const FCell& Cell)
        {
            // 与原来 64³ 线性键不同的混合哈希；用于哈希表的槽位选择。
            uint32_t H = uint32_t(Cell.X + 64) * 73856093u
                       ^ uint32_t(Cell.Y + 64) * 19349663u
                       ^ uint32_t(Cell.Z + 64) * 83492791u;
            H ^= H >> 15; H *= 0x2c1b3c6du; H ^= H >> 12;
            return H;
        }

        struct FLookupTable
        {
            struct FSlot { uint32_t Stamp; FCell Cell; long long Value; };
            FSlot Slots[LookupCapacity];
            uint32_t Generation = 0;
            std::mutex Mutex;
            /** 逻辑上清空（O(1)）：抬高代，旧数据自然失效。 */
            void Clear() { ++Generation; if (Generation == 0) { std::fill(Slots, Slots + LookupCapacity, FSlot{0u, FCell{}, -1}); Generation = 1; } }
            void Set(const FCell& Cell, long long Value)
            {
                uint32_t I = HashCell(Cell) & LookupMask;
                while (Slots[I].Stamp == Generation) I = (I + 1) & LookupMask;
                Slots[I] = {Generation, Cell, Value};
            }
            long long Get(const FCell& Cell) const
            {
                uint32_t I = HashCell(Cell) & LookupMask;
                while (Slots[I].Stamp == Generation)
                {
                    const FCell& C = Slots[I].Cell;
                    if (C.X == Cell.X && C.Y == Cell.Y && C.Z == Cell.Z) return Slots[I].Value;
                    I = (I + 1) & LookupMask;
                }
                return -1;
            }
        };

        inline void Centre(const FCell& Cell, float* Out)
        {
            Out[0] = float((Cell.X + 0.5) * CellM);
            Out[1] = float((Cell.Y + 0.5) * CellM);
            Out[2] = float((Cell.Z + 0.5) * CellM);
        }

        /** Two 5-high, 1-thick walls with a ceiling slab on top; SpanCells = clear span in cells. */
        inline void Room(int SpanCells, std::vector<FCell>& Out, FCell& LoadAt)
        {
            Out.clear();
            for (int Z = 0; Z < 5; ++Z)
            {
                for (int X = 0; X < 5; ++X) { Out.push_back({X, 0, Z}); Out.push_back({X, SpanCells + 1, Z}); }
            }
            for (int Y = 0; Y <= SpanCells + 1; ++Y)
            {
                for (int X = 0; X < 5; ++X) Out.push_back({X, Y, 5});
            }
            LoadAt = { 2, (SpanCells + 1) / 2, 5 };
        }
    }

    /** Worst bond utilisation (1.0 = first bond breaks) for one ceiling span. */
    inline double Ratio(const FMaterial& Material, int SpanCells, double ExtraLoadKg, int Iterations = 256)
    {
        std::vector<FCell> Cells; FCell LoadAt;
        Detail::Room(SpanCells, Cells, LoadAt);
        if (Cells.empty()) return 0.0;

        // 审计 P4 + C1：见 Detail::FLookupTable 的注释。取表即加锁（串行化并发调用），
        // Clear() 是 O(1) 的代自增，取代原来每次调用 2 MB 的 std::fill。
        static Detail::FLookupTable Lookup;
        const std::lock_guard<std::mutex> Lock(Lookup.Mutex);
        Lookup.Clear();
        const int Count = (int)Cells.size();
        int LoadCell = -1;
        for (int I = 0; I < Count; ++I)
        {
            if (Cells[I].X == LoadAt.X && Cells[I].Y == LoadAt.Y && Cells[I].Z == LoadAt.Z) LoadCell = I;
        }

        const double Mass = Material.MassPerCellKg();
        std::vector<FPSBlastNode> Nodes;
        Nodes.reserve(Count + 1);
        for (int I = 0; I < Count; ++I)
        {
            float P[3]; Detail::Centre(Cells[I], P);
            FPSBlastNode Node{};
            Node.position[0] = P[0]; Node.position[1] = P[1]; Node.position[2] = P[2];
            Node.mass = float(Mass + (I == LoadCell ? ExtraLoadKg : 0.0));
            Node.inertia = Node.mass * 0.04f / 6.f;
            Node.acceleration[2] = float(GravityMS2);
            Nodes.push_back(Node);
            Lookup.Set(Cells[I], I);
        }
        const int World = Count;
        FPSBlastNode Fixed{};
        Nodes.push_back(Fixed);

        struct FLink { int A = 0, B = 0; float Normal[3] = { 0, 0, 0 }; float Cx = 0, Cy = 0, Cz = 0; };
        std::vector<FLink> Links;
        for (int I = 0; I < Count; ++I)
        {
            const FCell& Cell = Cells[I];
            if (Cell.Z == 0)
            {
                FLink Ground; Ground.A = I; Ground.B = World; Ground.Normal[2] = -1;
                Ground.Cx = float((Cell.X + 0.5) * CellM); Ground.Cy = float((Cell.Y + 0.5) * CellM);
                Links.push_back(Ground);
            }
            const FCell Neighbours[3] = { {Cell.X + 1, Cell.Y, Cell.Z}, {Cell.X, Cell.Y + 1, Cell.Z}, {Cell.X, Cell.Y, Cell.Z + 1} };
            for (int Axis = 0; Axis < 3; ++Axis)
            {
                const int J = (int)Lookup.Get(Neighbours[Axis]);
                if (J < 0) continue;
                float A[3], B[3]; Detail::Centre(Cell, A); Detail::Centre(Neighbours[Axis], B);
                FLink Link; Link.A = I; Link.B = J; Link.Normal[Axis] = (B[Axis] - A[Axis]) > 0 ? 1.f : -1.f;
                Link.Cx = Axis == 2 ? A[0] : (A[0] + B[0]) * .5f;
                Link.Cy = Axis == 2 ? A[1] : (A[1] + B[1]) * .5f;
                Link.Cz = Axis == 2 ? (A[2] + B[2]) * .5f : A[2];
                Links.push_back(Link);
            }
        }

        std::vector<FPSBlastBond> Raw;
        for (const FLink& Link : Links)
        {
            FPSBlastBond Bond{};
            Bond.nodes[0] = Link.A; Bond.nodes[1] = Link.B;
            Bond.centroid[0] = Link.Cx; Bond.centroid[1] = Link.Cy; Bond.centroid[2] = Link.Cz;
            Raw.push_back(Bond);
        }
        std::vector<FPSBlastForce> Forces(Links.size());
        FPSBlastSolve(Nodes.data(), (unsigned)Nodes.size(), Raw.data(), (unsigned)Raw.size(), (unsigned)Iterations, Forces.data());

        double Worst = 0.0;
        for (size_t I = 0; I < Links.size(); ++I)
        {
            const float* F = Forces[I].linear;
            const float* M = Forces[I].angular;
            const float* N = Links[I].Normal;
            const double Normal = F[0] * N[0] + F[1] * N[1] + F[2] * N[2];
            const double Twist = M[0] * N[0] + M[1] * N[1] + M[2] * N[2];
            const double Bx = M[0] - N[0] * Twist, By = M[1] - N[1] * Twist, Bz = M[2] - N[2] * Twist;
            const double Bend = std::sqrt(Bx * Bx + By * By + Bz * Bz) * 6.0 / (AreaM2 * LeverM);
            const double Sx = F[0] - N[0] * Normal, Sy = F[1] - N[1] * Normal, Sz = F[2] - N[2] * Normal;
            const double Shear = std::sqrt(Sx * Sx + Sy * Sy + Sz * Sz) / AreaM2 + std::abs(Twist) * 3.0 / (AreaM2 * LeverM);
            const double Compression = std::max(0., -Normal / AreaM2) + Bend;
            const double Tension = std::max(0., Normal / AreaM2) + Bend;
            Worst = std::max(Worst, std::max(Compression / Material.CompressionPa,
                std::max(Tension / Material.TensionPa, Shear / Material.ShearPa)));
        }
        return Worst;
    }

    /**
     * Longest clear span (metres) whose worst bond stays under 1.0 for the given extra load.
     * Scans one cell at a time from 1 up, so it also reports "\~0" when even a single-cell
     * span fails, and MaxSpanCells when the search range is exhausted.
     */
    inline double MaxSpanMeters(const FMaterial& Material, double ExtraLoadKg, int MaxSpanCells = 25, int Iterations = 256)
    {
        double Best = 0.0;
        for (int Span = 1; Span <= MaxSpanCells; ++Span)
        {
            if (Ratio(Material, Span, ExtraLoadKg, Iterations) > 1.0) break;
            Best = Span * CellM;
        }
        return Best;
    }
}
