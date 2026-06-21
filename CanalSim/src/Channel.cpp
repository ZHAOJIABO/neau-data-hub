#include "Channel.h"
#include <cmath>
#include <algorithm>

namespace CanalSim {

Channel::Channel(const ChannelConfig& cfg_) : nx(cfg_.nx), cfg(cfg_) {
    cfg.dx = cfg.L / (nx - 1);
    cfg.n_steps = static_cast<int>(cfg.tf / cfg.dt) + 1;
    cells.resize(nx);
    x_positions.resize(nx);
}

void Channel::initialize() {
    // 用上游边界流量 Q_upstream 计算全场均匀初始条件
    // 确保 A_0 与 Q_upstream 一开始就满足 Manning 关系
    double Q_init = (cfg.Q_initial > 0.0) ? cfg.Q_initial : cfg.Q_upstream;
    double y0 = normalDepth(Q_init);
    if (y0 <= 0) y0 = 1.0;

    for (int i = 0; i < nx; ++i) {
        cells[i].x = i * cfg.dx;
        x_positions[i] = cells[i].x;
        cells[i].z = cfg.S0 * (cfg.L - cells[i].x);
        cells[i].y = y0;
        cells[i].A = getA(y0);
        cells[i].Q = Q_init;
    }
    computeGeometry();

    // 确保上游格点的 A 与 Q_in 一致（避免边界不一致）
    cells[0].Q = cfg.Q_upstream;
    cells[0].y = normalDepth(cfg.Q_upstream);
    cells[0].A = getA(cells[0].y);
}

void Channel::computeGeometry() {
    for (int i = 0; i < nx; ++i) {
        double y = cells[i].y;
        if (y <= 0) y = 0.001;

        cells[i].y = y;
        cells[i].A  = getA(y);
        cells[i].B  = getTopWidth(y);
        cells[i].P  = getWettedPerimeter(y);
        cells[i].R  = cells[i].A / cells[i].P;
        cells[i].V  = (cells[i].A > 1e-6) ? cells[i].Q / cells[i].A : 0.0;
        cells[i].Fr = (cells[i].A > 1e-6)
            ? std::abs(cells[i].V) / std::sqrt(cfg.g * cells[i].A / cells[i].B)
            : 0.0;
    }
}

double Channel::getA(double y) const {
    if (y <= 0) return 0.0;
    return (cfg.b + cfg.m * y) * y;
}

double Channel::getB(double y) const {
    if (y <= 0) return cfg.b;
    return cfg.b + 2.0 * cfg.m * y;
}

double Channel::getTopWidth(double y) const {
    return getB(y);
}

double Channel::getWettedPerimeter(double y) const {
    if (y <= 0) return 0.0;
    return cfg.b + 2.0 * y * std::sqrt(1.0 + cfg.m * cfg.m);
}

double Channel::solveYfromA(double A_target) const {
    double y_low = 0.001;
    double y_high = 50.0;
    for (int iter = 0; iter < 50; ++iter) {
        double y_mid = 0.5 * (y_low + y_high);
        double A_mid = getA(y_mid);
        if (A_mid < A_target)
            y_low = y_mid;
        else
            y_high = y_mid;
        if (y_high - y_low < 1e-7) break;
    }
    return 0.5 * (y_low + y_high);
}

void Channel::applyBoundaryConditions(double t) {
    (void)t;
    // 上游: Q 固定为 Q_upstream, A 从 Manning 反算保持一致
    cells[0].Q = cfg.Q_upstream;
    cells[0].y = normalDepth(cfg.Q_upstream);
    cells[0].A = getA(cells[0].y);

    // 下游: 零流量出流, A 从 Manning 反算 (Q ≈ 0 → 小面积)
    cells[nx - 1].Q = 0.0;
    cells[nx - 1].y = normalDepth(0.0);
    cells[nx - 1].A = getA(cells[nx - 1].y);
}

double Channel::normalDepth(double Q) const {
    double y_low = 0.01, y_high = 50.0;
    for (int iter = 0; iter < 100; ++iter) {
        double y_mid = 0.5 * (y_low + y_high);
        double A = getA(y_mid);
        double P = getWettedPerimeter(y_mid);
        double R = (P > 1e-6) ? A / P : 0.0;
        double Q_calc = (cfg.S0 > 0)
            ? std::sqrt(cfg.S0) / cfg.n_Manning * A * std::pow(R, 2.0 / 3.0)
            : 0.0;
        if (Q_calc < Q)
            y_low = y_mid;
        else
            y_high = y_mid;
        if (y_high - y_low < 1e-8) break;
    }
    double y_star = 0.5 * (y_low + y_high);
    if (std::abs(y_star) < 1e-6) y_star = 1.0;
    return y_star;
}

} // namespace CanalSim
