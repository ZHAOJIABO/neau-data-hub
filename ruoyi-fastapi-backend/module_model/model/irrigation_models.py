import torch
from torch import nn


class LSTMModel(nn.Module):
    """LSTM 代理模型：输入10维特征，输出2维（土壤含水量+植被蒸腾）"""

    def __init__(self) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size=10, hidden_size=64, batch_first=True)
        self.fc = nn.Linear(64, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        return self.fc(out)


class SACActor(nn.Module):
    """SAC 强化学习 Actor：12维状态输入，1维灌溉动作输出"""

    def __init__(self, state_dim: int = 12, action_dim: int = 1, hidden_dim: int = 256) -> None:
        super().__init__()
        self.latent_pi = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.mu = nn.Linear(hidden_dim, action_dim)
        self.log_std = nn.Linear(hidden_dim, action_dim)

    def forward(self, state: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.latent_pi(state)
        mean = self.mu(x)
        log_std = self.log_std(x)
        log_std = torch.clamp(log_std, -20, 2)
        return mean, log_std

    def predict_batch(self, state: torch.Tensor, deterministic: bool = True) -> torch.Tensor:
        with torch.no_grad():
            mean, log_std = self.forward(state)
            if deterministic:
                action = torch.tanh(mean)
            else:
                std = torch.exp(log_std)
                noise = torch.randn_like(mean)
                action = torch.tanh(mean + std * noise)
        return action
