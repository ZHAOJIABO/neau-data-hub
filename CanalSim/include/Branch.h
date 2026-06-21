#pragma once
#include <vector>
#include <algorithm>
#include <cmath>

namespace CanalSim {

struct BranchConfig {
    double x_position;        // 支渠分水口里程 (m)
    double Q_offtake;         // 恒定取水流量 (m^3/s), 正值 = 出水
    double spread_cells = 2;  // 影响网格半径 (默认 ±2 网格)
};

class BranchNetwork {
public:
    void addBranch(const BranchConfig& bc) { branches_.push_back(bc); }

    const std::vector<BranchConfig>& branches() const { return branches_; }

    // 返回与该支渠配置最近的网格索引 (假定网格在 [0, L] 内等距分布)
    int findCellIndex(double x, double dx) const {
        int idx = static_cast<int>(std::round(x / dx));
        return idx;
    }

    // 第 i 网格处单位长度上的等效出流 q_L (m^3/s/m)
    // 把每条支渠的 Q_offtake 在其中心网格 ± spread_cells 范围内按三角形分布
    // 三角形权重: 中心为 (s+1), 边缘为 1, 总权重 sum = (s+1)^2
    // 实际 qL = w_i * Q_offtake / ((s+1)^2 * dx), 累加后正好等于 Q_offtake
    double offtakeAt(int cellIndex, double dx, int nx) const {
        double q = 0.0;
        for (const auto& br : branches_) {
            int c = findCellIndex(br.x_position, dx);
            if (c < 0 || c >= nx) continue;
            int s = std::max(1, static_cast<int>(br.spread_cells));
            int d = cellIndex - c;
            if (std::abs(d) > s) continue;
            // 三角形权重: 中心最大, 两侧线性递减
            double w = (s + 1) - std::abs(d);
            if (w < 0) w = 0;
            // sum(w) = (s+1)^2; qL * dx 在所有节点上求和 = Q_offtake
            q += w * br.Q_offtake / (static_cast<double>(s + 1) * (s + 1) * dx);
        }
        return q;
    }

    // 累计从上游到 i 的总取水流量
    double cumulativeOfftake(int cellIndex, double dx, int nx) const {
        double sum = 0.0;
        for (int k = 0; k <= cellIndex; ++k) {
            sum += offtakeAt(k, dx, nx) * dx;
        }
        return sum;
    }

    double totalOfftake() const {
        double sum = 0.0;
        for (const auto& br : branches_) sum += br.Q_offtake;
        return sum;
    }

private:
    std::vector<BranchConfig> branches_;
};

}
