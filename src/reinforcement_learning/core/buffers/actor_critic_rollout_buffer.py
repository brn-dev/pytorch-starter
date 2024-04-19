from overrides import override

import numpy as np
import torch

from src.reinforcement_learning.core.buffers.basic_rollout_buffer import BasicRolloutBuffer
from src.reinforcement_learning.core.generalized_advantage_estimate import compute_gae_and_returns
from src.reinforcement_learning.core.normalization import NormalizationType, normalize_np_array


class ActorCriticRolloutBuffer(BasicRolloutBuffer):
    def __init__(self, buffer_size: int, num_envs: int, obs_shape: tuple[int, ...], detach_actions: bool = True):
        super().__init__(buffer_size, num_envs, obs_shape, detach_actions)

        self.value_estimates: list[torch.Tensor] = []

    @override
    def reset(self):
        super().reset()
        del self.value_estimates[:]

    @override
    def add(
            self,
            observations: np.ndarray,
            rewards: np.ndarray,
            episode_starts: np.ndarray,
            actions: torch.Tensor,
            action_log_probs: torch.Tensor,
            value_estimates: torch.Tensor = None,
            **extra_predictions: torch.Tensor
    ):
        assert value_estimates is not None
        self.value_estimates.append(value_estimates.squeeze(-1))
        super().add(
            observations=observations,
            rewards=rewards,
            episode_starts=episode_starts,
            actions=actions,
            action_log_probs=action_log_probs,
            **extra_predictions
        )

    # Adapted from
    # https://github.com/DLR-RM/stable-baselines3/blob/5623d98f9d6bcfd2ab450e850c3f7b090aef5642/stable_baselines3/common/buffers.py#L402
    def compute_gae_and_returns(
            self,
            last_values: torch.Tensor,
            last_dones: np.ndarray,
            gamma: float,
            gae_lambda: float,
            normalize_rewards: NormalizationType | None,
            normalize_advantages: NormalizationType | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        last_values = last_values.squeeze(-1).detach().clone().cpu().numpy()
        value_estimates = torch.stack(self.value_estimates).detach().cpu().numpy()

        return compute_gae_and_returns(
            value_estimates=value_estimates,
            rewards=self.rewards[:self.pos],
            episode_starts=self.episode_starts[:self.pos],
            last_values=last_values,
            last_dones=last_dones,
            gamma=gamma,
            gae_lambda=gae_lambda,
            normalize_rewards=normalize_rewards,
            normalize_advantages=normalize_advantages
        )
