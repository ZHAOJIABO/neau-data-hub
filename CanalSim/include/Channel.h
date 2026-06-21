#pragma once
#include <vector>
#include <string>
#include "Branch.h"

namespace CanalSim {

struct ChannelConfig {
    double L = 5000.0;
    int nx = 100;
    double b = 10.0;
    double m = 1.5;
    double n_Manning = 0.013;
    double S0 = 0.0001;
    double Q_upstream = 50.0;
    double A_inflow = 0.0;
    double dx;
    double g = 9.81;
    double A_wet_min = 0.1;  // 湿地面积下限 (m²); 下游零流区域保持此最小底水深
    int max_iter = 100;
    double tolerance = 1e-6;
    double tf = 7200.0;
    double dt = 30.0;
    int n_steps;
    double Q_initial = 0.0;   // 初始流量; 0 = 用 Q_upstream 作为初值
    BranchNetwork branches;
};

struct Cell {
    double x;
    double z;
    double A;
    double Q;
    double y;
    double B;
    double P;
    double R;
    double V;
    double Fr;
};

class Channel {
public:
    explicit Channel(const ChannelConfig& cfg);
    void initialize();
    void applyBoundaryConditions(double t);
    void computeGeometry();

    double getA(double y) const;
    double getB(double y) const;
    double getTopWidth(double y) const;
    double getWettedPerimeter(double y) const;
    double solveYfromA(double A_target) const;
    double normalDepth(double Q) const;

    int nx;
    std::vector<Cell> cells;
    ChannelConfig cfg;
    std::vector<double> x_positions;
};

}
