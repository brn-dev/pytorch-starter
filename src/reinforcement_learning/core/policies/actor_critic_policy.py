from typing import Callable

from overrides import override

import numpy as np
import torch
import torch.distributions as dist
from torch import nn

from src.reinforcement_learning.core.policies.base_policy import BasePolicy, TensorOrNpArray

VALUE_ESTIMATES_KEY = 'value_estimates'


class ActorCriticPolicy(BasePolicy):

    def __init__(self, network: nn.Module, action_dist_provider: Callable[[torch.Tensor], dist.Distribution]):
        super().__init__(network, action_dist_provider)

    @override
    def process_obs(self, obs: TensorOrNpArray) -> tuple[dist.Distribution, dict[str, torch.Tensor]]:
        action_logits, value_estimates = self.predict_actions_and_values(obs)
        return self.action_dist_provider(action_logits), {VALUE_ESTIMATES_KEY: value_estimates}

    def predict_values(self, obs: TensorOrNpArray) -> torch.Tensor:
        return self.predict_actions_and_values(obs)[1]

    def predict_actions_and_values(self, obs: TensorOrNpArray) -> tuple[torch.Tensor, torch.Tensor]:
        obs_tensor = torch.as_tensor(obs, dtype=torch.float32)
        actions_logits, value_estimates = self(obs_tensor)
        return actions_logits, value_estimates
