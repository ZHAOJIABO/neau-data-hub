from __future__ import annotations

from typing import Any

import numpy as np
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize
from pymoo.termination import get_termination
from pymoo.util.ref_dirs import get_reference_directions

from utils.log_util import logger


class WaterFertilizerOptimizationProblem(ElementwiseProblem):
    """
    水肥调控多目标优化问题。
    """

    def __init__(self, regulation_data: dict[str, Any], optimization_params: dict[str, float]):
        self.T = int(regulation_data['T'])
        self.P = np.asarray(regulation_data['P'], dtype=float)
        self.ET_MAXT = np.asarray(regulation_data['ET_MAXT'], dtype=float)
        self.ET_MINT = np.asarray(regulation_data['ET_MINT'], dtype=float)
        self.H_P = np.asarray(regulation_data['H_P'], dtype=float)
        self.H_MAX = np.asarray(regulation_data['H_MAX'], dtype=float)
        self.H_MIN = np.asarray(regulation_data['H_MIN'], dtype=float)

        self.Y_M = float(optimization_params['yield_max'])
        self.Q = float(optimization_params['max_irrigation'])
        self.YITA = float(optimization_params['water_efficiency'])
        self.W = float(optimization_params['paddy_water'])
        self.L = np.full(self.T, float(optimization_params['leakage']))

        self.b0 = float(optimization_params['b0'])
        self.b1 = float(optimization_params['b1'])
        self.b2 = float(optimization_params['b2'])
        self.c = float(optimization_params['c'])
        self.NF_0 = float(optimization_params['nitrogen_base'])
        self.NF_M = float(optimization_params['nitrogen_optimal'])
        self.NF_MAX = float(optimization_params['nitrogen_max'])
        self.NF_MIN = float(optimization_params['nitrogen_min'])

        self.stage_idx = self._build_stage_indexes(self.T)
        self.K_Y = np.array([0.109, 0.109, 0.143, 0.102, 0.235, 0.244, 0.119, 0.119, 0.0359])

        n_var = self.T + 1
        n_obj = 4
        n_constr = 3 * self.T + 2
        xl = np.zeros(n_var)
        xu = np.hstack([np.full(self.T, self.Q), self.NF_MAX])

        super().__init__(n_var=n_var, n_obj=n_obj, n_constr=n_constr, xl=xl, xu=xu)

    @staticmethod
    def _build_stage_indexes(t_len: int) -> dict[int, list[int]]:
        if t_len >= 135:
            ranges = {
                1: range(1, 11),
                2: range(11, 37),
                3: range(37, 47),
                4: range(47, 65),
                5: range(65, 74),
                6: range(74, 104),
                7: range(104, 119),
                8: range(119, 128),
                9: range(128, 136),
            }
        else:
            cuts = [0, 10, 36, 46, 64, 73, 103, 118, 127, 135]
            scaled = [min(t_len, max(0, round(cut * t_len / 135.0))) for cut in cuts]
            scaled[0] = 0
            scaled[-1] = t_len
            for idx in range(1, len(scaled)):
                if scaled[idx] <= scaled[idx - 1] and scaled[idx - 1] < t_len:
                    scaled[idx] = scaled[idx - 1] + 1
            ranges = {idx: range(scaled[idx - 1] + 1, min(scaled[idx], t_len) + 1) for idx in range(1, 10)}
        return {stage: [day - 1 for day in day_range if 0 <= day - 1 < t_len] for stage, day_range in ranges.items()}

    def _evaluate(self, x: np.ndarray, out: dict[str, np.ndarray], *args: Any, **kwargs: Any) -> None:
        try:
            IW = x[:-1]
            NF = x[-1]
            NF_ALL = NF + self.c * self.NF_0

            H = np.zeros(self.T)
            D = np.zeros(self.T)
            ET_AT = np.zeros(self.T)
            H[0] = self.H_P[0]

            for t_idx in range(self.T):
                if H[t_idx] <= self.H_MIN[t_idx]:
                    ET_AT[t_idx] = self.ET_MINT[t_idx]
                elif H[t_idx] >= self.H_MAX[t_idx]:
                    ET_AT[t_idx] = self.ET_MAXT[t_idx]
                else:
                    denom = self.H_MAX[t_idx] - self.H_MIN[t_idx]
                    gamma = (H[t_idx] - self.H_MIN[t_idx]) / (denom if denom else 1e-12)
                    ET_AT[t_idx] = (1.0 - gamma) * self.ET_MINT[t_idx] + gamma * self.ET_MAXT[t_idx]

                D[t_idx] = max(H[t_idx] - self.H_P[t_idx], 0.0)
                if t_idx < self.T - 1:
                    H[t_idx + 1] = H[t_idx] + IW[t_idx] + self.P[t_idx] - ET_AT[t_idx] - self.L[t_idx] - D[t_idx]

            ET_AN = np.array([ET_AT[self.stage_idx[n]].sum() if self.stage_idx[n] else 0.0 for n in range(1, 10)])
            ET_MAXN = np.array(
                [self.ET_MAXT[self.stage_idx[n]].sum() if self.stage_idx[n] else 1e-12 for n in range(1, 10)]
            )
            ET_MAXN = np.where(ET_MAXN == 0, 1e-12, ET_MAXN)

            ratio = NF_ALL / (self.NF_M + self.c * self.NF_0)
            bN = self.b0 + self.b1 * ratio + self.b2 * ratio**2
            yield_value = self.Y_M * bN * (1 - (self.K_Y * (1 - ET_AN / ET_MAXN)).sum())
            iwa = 10 * (self.W / self.YITA + IW.sum() / self.YITA)
            giwp = yield_value / iwa if iwa > 0 else 0.0
            cex = yield_value / NF_ALL if NF_ALL > 0 else 0.0
            gwp = (35.2031 + 25 * 2.75951 + 298 * 0.00545456) * NF_ALL * 0.88

            out['F'] = np.array([-yield_value, -giwp, -cex, gwp])
            constraints = []
            constraints += list(IW - self.Q)
            constraints += list(H - self.H_P)
            constraints += list(self.H_MIN - H)
            constraints.append(NF_ALL - self.NF_MAX)
            constraints.append(self.NF_MIN - NF_ALL)
            out['G'] = np.array(constraints)
        except Exception as exc:
            logger.error('水肥调控个体评估失败: {}', exc)
            out['F'] = np.array([1e6, 1e6, 1e6, 1e6])
            out['G'] = np.array([1e6] * self.n_constr)


class NSGA3WaterFertilizerOptimizer:
    """
    NSGA-III 水肥调控优化器。
    """

    def __init__(self, population_size: int = 80, generations: int = 60, seed: int = 123):
        self.population_size = int(population_size)
        self.generations = int(generations)
        self.seed = int(seed)

    def optimize(self, problem: WaterFertilizerOptimizationProblem) -> dict[str, Any]:
        ref_dirs = self._build_reference_directions()
        algorithm = NSGA3(ref_dirs=ref_dirs, pop_size=self.population_size)
        result = minimize(problem, algorithm, get_termination('n_gen', self.generations), seed=self.seed, verbose=False)
        if result is None:
            raise RuntimeError('优化结果为空')

        f_matrix = result.F
        x_matrix = result.X
        cv_matrix = result.CV
        if (f_matrix is None or x_matrix is None) and getattr(result, 'pop', None) is not None:
            f_matrix = result.pop.get('F')
            x_matrix = result.pop.get('X')
            cv_matrix = result.pop.get('CV')
        if f_matrix is None or x_matrix is None:
            raise RuntimeError('优化结果为空')

        f_matrix = np.asarray(f_matrix)
        x_matrix = np.asarray(x_matrix)
        if f_matrix.ndim == 1:
            f_matrix = f_matrix.reshape(1, -1)
        if x_matrix.ndim == 1:
            x_matrix = x_matrix.reshape(1, -1)

        n_all = len(f_matrix)
        if cv_matrix is not None:
            cv_values = np.asarray(cv_matrix).reshape(-1)
            feasible_mask = cv_values == 0
        else:
            cv_values = np.zeros(n_all)
            feasible_mask = np.ones(n_all, dtype=bool)
        n_feasible = int(np.sum(feasible_mask))

        candidate_mask = feasible_mask if n_feasible > 0 else np.ones(n_all, dtype=bool)
        candidate_f = f_matrix[candidate_mask]
        candidate_x = x_matrix[candidate_mask]
        candidate_cv = cv_values[candidate_mask]
        best_solution = self._select_best_solution_topsis(candidate_f, candidate_x)
        if n_feasible == 0:
            best_solution['constraintViolation'] = float(np.min(candidate_cv)) if len(candidate_cv) else None
        pareto_solutions = [
            {
                'yield': float(-f_val[0]),
                'giwp': float(-f_val[1]),
                'cex': float(-f_val[2]),
                'gwp': float(f_val[3]),
                'nitrogen': float(x_val[-1]),
                'totalIrrigation': float(x_val[:-1].sum()),
                'constraintViolation': float(cv_val) if n_feasible == 0 else 0.0,
            }
            for f_val, x_val, cv_val in zip(candidate_f[:50], candidate_x[:50], candidate_cv[:50])
        ]
        return {
            'bestSolution': best_solution,
            'paretoSolutions': pareto_solutions,
            'optimizationInfo': {
                'totalSolutions': int(n_all),
                'feasibleSolutions': n_feasible,
                'minConstraintViolation': float(np.min(cv_values)) if len(cv_values) else 0.0,
                'algorithm': 'NSGA-III',
                'populationSize': self.population_size,
                'generations': self.generations,
                'referenceDirections': int(len(ref_dirs)),
            },
        }

    def _build_reference_directions(self) -> np.ndarray:
        selected = get_reference_directions('das-dennis', 4, n_partitions=3)
        for n_partitions in range(4, 13):
            candidate = get_reference_directions('das-dennis', 4, n_partitions=n_partitions)
            if len(candidate) > self.population_size:
                break
            selected = candidate
        return selected

    @staticmethod
    def _select_best_solution_topsis(f_matrix: np.ndarray, x_matrix: np.ndarray) -> dict[str, Any]:
        objectives = np.array([[-f[0], -f[1], -f[2], f[3]] for f in f_matrix])
        normalized = np.zeros_like(objectives)
        for col_idx in range(objectives.shape[1]):
            if col_idx < 3:
                denom = np.sqrt(np.sum(objectives[:, col_idx] ** 2))
                normalized[:, col_idx] = objectives[:, col_idx] / (denom if denom else 1e-12)
            else:
                inv_obj = 1.0 / (objectives[:, col_idx] + 1e-10)
                denom = np.sqrt(np.sum(inv_obj**2))
                normalized[:, col_idx] = inv_obj / (denom if denom else 1e-12)

        weighted = normalized * np.array([0.25, 0.25, 0.25, 0.25])
        positive_ideal = np.max(weighted, axis=0)
        negative_ideal = np.min(weighted, axis=0)
        dist_positive = np.sqrt(np.sum((weighted - positive_ideal) ** 2, axis=1))
        dist_negative = np.sqrt(np.sum((weighted - negative_ideal) ** 2, axis=1))
        scores = dist_negative / (dist_positive + dist_negative + 1e-10)
        best_idx = int(np.argmax(scores))
        best_x = x_matrix[best_idx]
        return {
            'yield': float(objectives[best_idx, 0]),
            'giwp': float(objectives[best_idx, 1]),
            'cex': float(objectives[best_idx, 2]),
            'gwp': float(objectives[best_idx, 3]),
            'nitrogen': float(best_x[-1]),
            'totalIrrigation': float(best_x[:-1].sum()),
            'topsisScore': float(scores[best_idx]),
            'decisionVariables': {
                'irrigation': [float(v) for v in best_x[:-1]],
                'nitrogen': float(best_x[-1]),
            },
        }
