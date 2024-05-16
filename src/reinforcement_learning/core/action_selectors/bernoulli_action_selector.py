from typing import Optional, Self

import torch
import torch.distributions as torchdist

from src.reinforcement_learning.core.action_selectors.discrete_action_selector import DiscreteActionSelector


class BernoulliActionSelector(DiscreteActionSelector):

    def __init__(self, latent_dim: int, action_dim: int):
        super().__init__(
            latent_dim=latent_dim,
            action_dim=action_dim,
        )
        self.distribution: Optional[torchdist.Bernoulli] = None

    def update_distribution_params(self, action_logits: torch.Tensor) -> Self:
        self.distribution = torchdist.Bernoulli(logits=action_logits)
        return self

    def sample(self) -> torch.Tensor:
        return self.distribution.sample()

    def mode(self) -> torch.Tensor:
        return torch.round(self.distribution.probs)

    def log_prob(self, actions: torch.Tensor) -> torch.Tensor:
        return self.distribution.log_prob(actions).sum(dim=1)

    def entropy(self) -> torch.Tensor | None:
        return self.distribution.entropy().sum(dim=1)