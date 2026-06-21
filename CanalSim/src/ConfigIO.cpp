#include "ConfigIO.h"

#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <cmath>

#include <nlohmann/json.hpp>

namespace CanalSim {

using json = nlohmann::json;

namespace {

// 递归修约浮点数组：保留两位小数
void roundTo2dp(json& j) {
    if (j.is_array()) {
        for (auto& item : j) roundTo2dp(item);
    } else if (j.is_object()) {
        for (auto& [k, v] : j.items()) roundTo2dp(v);
    } else if (j.is_number_float()) {
        j = std::round(j.get<double>() * 100.0) / 100.0;
    }
}

// 安全读取带默认值的字段; 不存在则返回 default
double d(const json& j, const char* key, double dval) {
    auto it = j.find(key);
    if (it == j.end() || it->is_null()) return dval;
    return it->get<double>();
}
int i(const json& j, const char* key, int dval) {
    auto it = j.find(key);
    if (it == j.end() || it->is_null()) return dval;
    return it->get<int>();
}
bool b(const json& j, const char* key, bool dval) {
    auto it = j.find(key);
    if (it == j.end() || it->is_null()) return dval;
    if (it->is_boolean()) return it->get<bool>();
    return dval;
}
bool present(const json& j, const char* key) {
    return j.find(key) != j.end() && !j.at(key).is_null();
}

void require(const json& j, const char* key, const std::string& path) {
    if (!present(j, key)) {
        throw std::runtime_error("Missing required field '" + std::string(key) +
                                 "' in " + path);
    }
}

} // namespace

SimulationConfig ConfigIO::load(const std::string& path) {
    std::ifstream in(path);
    if (!in.is_open()) {
        throw std::runtime_error("Cannot open input file: " + path);
    }
    json j;
    try {
        in >> j;
    } catch (const std::exception& e) {
        throw std::runtime_error(std::string("Failed to parse JSON: ") + e.what());
    }

    SimulationConfig sc;

    // ---- channel ----
    if (!present(j, "channel")) {
        throw std::runtime_error("Missing required object 'channel' in " + path);
    }
    const json& jc = j["channel"];

    // 关键字段
    require(jc, "L",          path + "::channel");
    require(jc, "nx",         path + "::channel");
    require(jc, "tf",         path + "::channel");
    require(jc, "dt",         path + "::channel");

    sc.channel.L           = jc.at("L").get<double>();
    sc.channel.nx          = jc.at("nx").get<int>();
    sc.channel.b            = d(jc, "b",            sc.channel.b);
    sc.channel.m            = d(jc, "m",            sc.channel.m);
    sc.channel.n_Manning    = d(jc, "n_Manning",    sc.channel.n_Manning);
    sc.channel.S0           = d(jc, "S0",           sc.channel.S0);
    sc.channel.Q_upstream   = d(jc, "Q_upstream",   sc.channel.Q_upstream);
    sc.channel.A_inflow     = d(jc, "A_inflow",     sc.channel.A_inflow);
    sc.channel.use_rating_curve = b(jc, "use_rating_curve", sc.channel.use_rating_curve);
    sc.channel.g            = d(jc, "g",            sc.channel.g);
    sc.channel.A_wet_min   = d(jc, "A_wet_min",   sc.channel.A_wet_min);
    sc.channel.max_iter     = i(jc, "max_iter",     sc.channel.max_iter);
    sc.channel.tolerance    = d(jc, "tolerance",    sc.channel.tolerance);
    sc.channel.tf           = jc.at("tf").get<double>();
    sc.channel.dt           = jc.at("dt").get<double>();
    // 初始流量 (瞬态初值); 缺省 0 -> Channel::initialize 用 Q_upstream
    sc.channel.Q_initial    = d(jc, "Q_initial",    0.0);

    // 上游时序流量
    if (present(jc, "Q_upstream_series") && jc["Q_upstream_series"].is_array()) {
        for (const auto& v : jc["Q_upstream_series"]) {
            sc.channel.Q_upstream_series.push_back(v.get<double>());
        }
    }
    if (present(jc, "t_series") && jc["t_series"].is_array()) {
        for (const auto& v : jc["t_series"]) {
            sc.channel.t_series.push_back(v.get<double>());
        }
    }

    // 下游水位-流量关系曲线
    if (present(jc, "y_ds_curve") && jc["y_ds_curve"].is_array()) {
        for (const auto& v : jc["y_ds_curve"]) {
            sc.channel.y_ds_curve.push_back(v.get<double>());
        }
    }
    if (present(jc, "Q_ds_curve") && jc["Q_ds_curve"].is_array()) {
        for (const auto& v : jc["Q_ds_curve"]) {
            sc.channel.Q_ds_curve.push_back(v.get<double>());
        }
    }

    // ---- solver ----
    if (present(j, "solver")) {
        const json& js = j["solver"];
        sc.solver.theta         = d(js, "theta",         sc.solver.theta);
        sc.solver.tolerance     = d(js, "tolerance",     sc.solver.tolerance);
        sc.solver.max_iterations = i(js, "max_iterations", sc.solver.max_iterations);
    }

    // ---- branches ----
    if (present(j, "branches") && j["branches"].is_array()) {
        for (const auto& jb : j["branches"]) {
            BranchConfig bc;
            require(jb, "x_position", path + "::branches[]");
            require(jb, "Q_offtake",  path + "::branches[]");
            bc.x_position  = jb.at("x_position").get<double>();
            bc.Q_offtake   = jb.at("Q_offtake").get<double>();
            bc.spread_cells = d(jb, "spread_cells", 2.0);
            sc.branches.push_back(bc);
        }
    }

    return sc;
}

void ConfigIO::saveResult(const std::string& path,
                          const Channel& ch,
                          const std::vector<BranchConfig>& branches,
                          const TimeSeries& ts,
                          double elapsed_s,
                          const SpacetimeSnapshot& st) {
    json j;
    j["schema_version"] = "1.0.0";
    j["elapsed_seconds"] = elapsed_s;

    // channel
    j["channel"] = {
        {"L",       ch.cfg.L},
        {"nx",      ch.nx},
        {"dx",      ch.cfg.dx},
        {"b",       ch.cfg.b},
        {"m",       ch.cfg.m},
        {"n_Manning", ch.cfg.n_Manning},
        {"S0",      ch.cfg.S0},
        {"Q_upstream", ch.cfg.Q_upstream},
        {"g",       ch.cfg.g},
        {"tf",      ch.cfg.tf},
        {"dt",      ch.cfg.dt},
        {"n_steps", ch.cfg.n_steps}
    };

    // summary
    int last = ch.nx - 1;
    double total_offtake = 0.0;
    for (const auto& br : branches) total_offtake += br.Q_offtake;
    j["summary"] = {
        {"Q_upstream",          ch.cells[0].Q},
        {"Q_downstream_final",  ch.cells[last].Q},
        {"y_upstream_final",    ch.cells[0].y},
        {"y_downstream_final",  ch.cells[last].y},
        {"V_upstream_final",    ch.cells[0].V},
        {"V_downstream_final",  ch.cells[last].V},
        {"Fr_upstream_final",   ch.cells[0].Fr},
        {"Fr_downstream_final", ch.cells[last].Fr},
        {"total_offtake_m3s",   total_offtake},
        {"use_rating_curve",    ch.cfg.use_rating_curve}
    };

    // timeseries
    j["timeseries"] = {
        {"t",            ts.t},
        {"Q_upstream",   ts.Q_upstream},
        {"Q_downstream", ts.Q_downstream},
        {"y_upstream",   ts.y_upstream},
        {"y_downstream", ts.y_downstream}
    };

    // final_state (整条渠道最终断面)
    json jx  = json::array();
    json jy  = json::array();
    json jA  = json::array();
    json jQ  = json::array();
    json jV  = json::array();
    json jFr = json::array();
    for (const auto& c : ch.cells) {
        jx.push_back(c.x);
        jy.push_back(c.y);
        jA.push_back(c.A);
        jQ.push_back(c.Q);
        jV.push_back(c.V);
        jFr.push_back(c.Fr);
    }
    j["final_state"] = {
        {"x",  jx}, {"y",  jy}, {"A",  jA},
        {"Q",  jQ}, {"V",  jV}, {"Fr", jFr}
    };

    // branches
    json jb = json::array();
    for (size_t k = 0; k < branches.size(); ++k) {
        const auto& br = branches[k];
        jb.push_back({
            {"id",           static_cast<int>(k + 1)},
            {"x_position",   br.x_position},
            {"Q_offtake",    br.Q_offtake},
            {"spread_cells", br.spread_cells}
        });
    }
    j["branches"] = jb;

    // spacetime (时空快照矩阵; 缺省时为空对象)
    if (!st.waterLevelMatrix.empty() && st.nx > 0 && st.n_steps > 0) {
        j["spacetime"] = {
            {"times",              st.times},
            {"water_level_matrix", st.waterLevelMatrix},
            {"flow_rate_matrix",   st.flowRateMatrix},
            {"nx",                 st.nx},
            {"n_steps",            st.n_steps}
        };
    } else {
        j["spacetime"] = json::object();
    }

    roundTo2dp(j);
    std::ofstream out(path);
    if (!out.is_open()) {
        throw std::runtime_error("Cannot open output file: " + path);
    }
    out << j.dump(2) << "\n";
}

}
