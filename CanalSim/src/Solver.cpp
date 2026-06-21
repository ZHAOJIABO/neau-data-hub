#include "Solver.h"
#include "Channel.h"
#include <cmath>
#include <algorithm>

namespace CanalSim {

// ---------------------------------------------------------------------------
//  Kinematic Wave 隐式线性化求解器
//
//  求解方程:
//    连续方程:  dA/dt + dQ/dx = -qL(x)          (1)
//    Manning:   Q = (1/n) A R^{2/3} sqrt(S0)   (2)
//
//  离散格式（迎风格式）:
//
//  内部格点 i = 1 .. N-2:
//
//    dA_i/dt + (Q_i - Q_{i-1})/dx = -qL_i    [迎风格式, 物理一致]
//    Q_i^{n+1} = Manning(A_i^{n+1})
//
//  线性化后得到三对角方程组，用 Thomas 算法求解。
//  通过 Newton/Picard 迭代处理 Manning 公式的非线性。
// ---------------------------------------------------------------------------

Solver::Solver(const SolverConfig& cfg) : nx_(0), cfg_(cfg) {
    // 注意: SolverConfig 中的 theta 字段在本求解器中不使用（Kinematic Wave
    // 为纯隐式格式，无 Preissmann 权重参数），保留该字段仅为兼容 JSON 配置。
    if (cfg_.tolerance <= 0) cfg_.tolerance = 1e-6;
    if (cfg_.max_iterations <= 0) cfg_.max_iterations = 50;
}

namespace {
inline double solveYfromA_local(double A, double b, double m) {
    if (A <= 0) return 0;
    double lo = 0.001, hi = 50.0;
    for (int k = 0; k < 50; ++k) {
        double mid = 0.5 * (lo + hi);
        double Am = (b + m * mid) * mid;
        if (Am < A) lo = mid; else hi = mid;
        if (hi - lo < 1e-7) break;
    }
    return 0.5 * (lo + hi);
}

inline double ManningQ(double A, double b, double m, double n, double S0) {
    if (A <= 0 || S0 <= 0 || n <= 0) return 0.0;
    double y = solveYfromA_local(A, b, m);
    if (y <= 0) return 0.0;
    double P = b + 2.0 * y * std::sqrt(1.0 + m * m);
    double R = A / std::max(P, 1e-6);
    return (1.0 / n) * A * std::pow(R, 2.0 / 3.0) * std::sqrt(S0);
}
}

// ---------------------------------------------------------------------------
//  solveStep: 隐式线性化 Kinematic Wave 一步推进
//
//  算法:
//  1.  Picard 迭代处理非线性 (Manning 公式)
//     对每个迭代 k:
//       - 用当前 A^k 构建三对角 Jacobian 矩阵 (dQ/dA)
//       - 右端项包含时间项、空间通量差分、旁侧取水
//       - Thomas 算法求解 deltaA
//       - A^{k+1} = A^k + deltaA
//  2.  收敛后用 Manning 公式计算 Q
//  3.  更新 Channel 的全部几何量
// ---------------------------------------------------------------------------
bool Solver::solveStep(Channel& ch, double dt) {
    int N = ch.nx;
    nx_ = N;
    if (N < 3) {
        lastError_ = "Grid too small";
        return false;
    }

    const double dx = ch.cfg.dx;
    const double n  = ch.cfg.n_Manning;
    const double S0 = ch.cfg.S0;
    const double b  = ch.cfg.b;
    const double m  = ch.cfg.m;
    const double Q_in = ch.cfg.Q_upstream;

    std::vector<double> A_old(N), A_new(N);
    for (int i = 0; i < N; ++i) A_old[i] = ch.cells[i].A;
    A_new = A_old;

    for (int iter = 0; iter < cfg_.max_iterations; ++iter) {
        std::vector<double> aa(N, 0.0), bb(N, 0.0), cc(N, 0.0), rhs(N, 0.0);

        // -------------------------------------------------------------------
        // 内部格点 i = 1 .. N-2: 迎风差分
        //   (A_i - A_i^old)/dt + (Q_i - Q_{i-1})/dx = -qL_i
        //   Q = Manning(A), 线性化: Q^{k+1} ≈ Q^k + dQ/dA * deltaA
        // -------------------------------------------------------------------
        for (int i = 1; i < N - 1; ++i) {
            double A_i   = A_new[i];
            double A_im1 = A_new[i - 1];

            double Q_i   = ManningQ(A_i,   b, m, n, S0);
            double Q_im1 = ManningQ(A_im1, b, m, n, S0);

            // 数值微分 dQ/dA
            double eps = std::max(A_i * 1e-5, 1e-8);
            double dQdA_i   = (ManningQ(A_i   + eps, b, m, n, S0) - Q_i)   / eps;
            double dQdA_im1 = (ManningQ(A_im1 + eps, b, m, n, S0) - Q_im1) / eps;

            // 旁侧取水: 单位长度等效流量 (m³/s/m)
            double qL = ch.cfg.branches.offtakeAt(i, dx, N);

            // 迎风格式残差: (A_i - A_old_i)/dt + (Q_i - Q_im1)/dx + qL = 0
            rhs[i] = -((A_i - A_old[i]) / dt + (Q_i - Q_im1) / dx + qL);

            // Jacobian: aa = d(res)/d(A_{i-1}), bb = d(res)/d(A_i), cc = 0
            aa[i] = -(dQdA_im1 / dx);      // 迎风格式只涉及 i-1
            bb[i] = 1.0 / dt + dQdA_i / dx;
            cc[i] = 0.0;                    // 迎风格式不涉及 i+1
        }

        // -------------------------------------------------------------------
        // 上游边界: Q_0 = Q_in (Dirichlet)
        // 格点 i=1 的方程: (A_1 - A_old_1)/dt + (Q_1 - Q_in)/dx = -qL_1
        // Q_1 由 Manning(A_1) 决定，Q_in 为常数。
        // -------------------------------------------------------------------
        {
            int i = 1;
            double A_1   = A_new[1];
            double Q_1   = ManningQ(A_1, b, m, n, S0);
            double eps    = std::max(A_1 * 1e-5, 1e-8);
            double dQdA_1 = (ManningQ(A_1 + eps, b, m, n, S0) - Q_1) / eps;
            double qL     = ch.cfg.branches.offtakeAt(1, dx, N);

            rhs[i] = -((A_1 - A_old[1]) / dt + (Q_1 - Q_in) / dx + qL);
            aa[i]  = 0.0;                       // Q_in 为常数，不依赖 A_0
            bb[i]  = 1.0 / dt + dQdA_1 / dx;
            cc[i]  = 0.0;
        }

        // -------------------------------------------------------------------
        // 下游边界: Q_{N-1} = 0 (零流量出流)
        // 格点 i = N-1 的方程: (A_{N-1} - A_old_{N-1})/dt + qL_{N-1} = 0
        // 解得 A_{N-1}^{new} = A_old_{N-1} - qL_{N-1} * dt
        // -------------------------------------------------------------------
        {
            int i = N - 1;
            double qL = ch.cfg.branches.offtakeAt(i, dx, N);
            rhs[i] = -((A_new[i] - A_old[i]) / dt + qL);
            aa[i]  = 0.0;
            bb[i]  = 1.0 / dt;
            cc[i]  = 0.0;
        }

        // -------------------------------------------------------------------
        // Thomas 算法求解三对角系统
        // aa[i]*deltaA[i-1] + bb[i]*deltaA[i] + cc[i]*deltaA[i+1] = rhs[i]
        // -------------------------------------------------------------------
        std::vector<double> cp(N, 0.0), dp(N, 0.0);
        for (int i = 0; i < N; ++i) {
            double denom = bb[i] - aa[i] * cp[i - 1];
            if (i == 0) denom = (std::abs(bb[i]) > 1e-20) ? bb[i] : 1.0;
            else if (std::abs(denom) < 1e-20) denom = 1e-20;
            cp[i] = (i < N - 1) ? cc[i] / denom : 0.0;
            dp[i] = (rhs[i] - aa[i] * dp[i - 1]) / denom;
        }

        std::vector<double> deltaA(N, 0.0);
        deltaA[N - 1] = dp[N - 1];
        for (int i = N - 2; i >= 0; --i) {
            deltaA[i] = dp[i] - cp[i] * deltaA[i + 1];
        }

        // -------------------------------------------------------------------
        // 更新面积 (带湿地储水下限)
        // maxDelta 必须在截断判断之前计算，保证条件判断准确
        // 仅在收敛迭代时（iter == max 或 maxDelta 已很小）才施加固值截断
        const double A_wet = ch.cfg.A_wet_min;
        double maxDelta = 0.0;
        for (int i = 0; i < N; ++i) {
            maxDelta = std::max(maxDelta, std::abs(deltaA[i]));
        }
        bool near_converged = (iter == cfg_.max_iterations - 1) || (maxDelta < cfg_.tolerance * 0.1);
        for (int i = 0; i < N; ++i) {
            A_new[i] += deltaA[i];
            if (near_converged && A_new[i] < A_wet) A_new[i] = A_wet;
        }

        if (maxDelta < cfg_.tolerance) break;
    }

    // -------------------------------------------------------------------
    // 后处理: 计算所有格点的 Q 和几何量
    // 上游格点 i=0: Q 固定为 Q_in, A 从 Manning 反算保持一致
    // 其他格点: Q = Manning(A), 与求解器中使用的公式一致
    // -------------------------------------------------------------------
    for (int i = 0; i < N; ++i) {
        ch.cells[i].A = A_new[i];
        ch.cells[i].y = solveYfromA_local(A_new[i], b, m);
        if (i == 0) {
            ch.cells[i].Q = Q_in;
            ch.cells[i].A = ch.getA(ch.cells[i].y);
        } else {
            ch.cells[i].Q = ManningQ(A_new[i], b, m, n, S0);
        }
    }
    ch.computeGeometry();
    return true;
}

} // namespace CanalSim
