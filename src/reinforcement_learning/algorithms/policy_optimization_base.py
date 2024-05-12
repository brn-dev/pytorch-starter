import abc
from dataclasses import dataclass
from typing import Callable, TypeVar

import gymnasium
import numpy as np
from torch import optim

from src.reinforcement_learning.core.buffers.basic_rollout_buffer import BasicRolloutBuffer
from src.reinforcement_learning.core.callback import Callback
from src.reinforcement_learning.core.infos import InfoDict, stack_infos
from src.reinforcement_learning.core.policies.base_policy import BasePolicy
from src.reinforcement_learning.gym.envs.singleton_vector_env import as_vec_env


@dataclass
class LoggingConfig:
    log_rollout_infos: bool = False
    log_reset_info: bool = False


LogConf = TypeVar('LogConf', bound=LoggingConfig)
Buffer = TypeVar('Buffer', bound=BasicRolloutBuffer)

Policy = TypeVar('Policy', bound=BasePolicy)
PolicyProvider = Callable[[], Policy]


class PolicyOptimizationBase(abc.ABC):


    def __init__(
            self,
            env: gymnasium.Env,
            policy: Policy | PolicyProvider,
            policy_optimizer: optim.Optimizer | Callable[[BasePolicy], optim.Optimizer],
            buffer: Buffer,
            gamma: float,
            gae_lambda: float,
            reset_env_between_rollouts: bool,
            callback: Callback,
            logging_config: LogConf
    ):
        self.env, self.num_envs = as_vec_env(env)

        self.policy = policy if isinstance(policy, BasePolicy) else policy()
        self.policy_optimizer = (
            policy_optimizer
            if isinstance(policy_optimizer, optim.Optimizer)
            else policy_optimizer(policy)
        )
        self.buffer = buffer

        self.gamma = gamma
        self.gae_lambda = gae_lambda

        self.reset_env_between_rollouts = reset_env_between_rollouts

        self.callback = callback
        self.logging_config = logging_config

    @abc.abstractmethod
    def optimize(
            self,
            last_obs: np.ndarray,
            last_dones: np.ndarray,
            info: InfoDict
    ) -> None:
        raise NotImplemented

    def rollout_step(self, obs: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
        action_selector, extra_predictions = self.policy.process_obs(obs)
        actions = action_selector.get_actions()

        next_obs, rewards, terminated, truncated, info = self.env.step(actions.detach().cpu().numpy())

        self.buffer.add(
            observations=obs,
            rewards=rewards,
            episode_starts=np.logical_or(terminated, truncated),
            actions=actions,
            action_log_probs=action_selector.log_prob(actions),
            **extra_predictions
        )

        return next_obs, rewards, terminated, truncated, info


    def perform_rollout(
            self,
            max_steps: int,
            obs: np.ndarray,
            info: InfoDict
    ) -> tuple[int, np.ndarray, np.ndarray, np.ndarray]:
        num_envs = self.env.get_wrapper_attr('num_envs')

        terminated = np.empty((num_envs,), dtype=bool)
        truncated = np.empty((num_envs,), dtype=bool)
        step = 0

        infos: list[InfoDict] = []
        for step in range(min(self.buffer.buffer_size, max_steps)):
            obs, rewards, terminated, truncated, step_info = self.rollout_step(obs)
            infos.append(step_info)

        if self.logging_config.log_rollout_infos:
            info['rollout'] = stack_infos(infos)

        return step + 1, obs, terminated, truncated


    def train(self, num_steps: int):
        obs: np.ndarray = np.empty(())

        step = 0
        while step < num_steps:
            info: InfoDict = {}

            if step == 0 or self.reset_env_between_rollouts:
                obs, reset_info = self.env.reset()

                if self.logging_config.log_reset_info:
                    info['reset'] = reset_info

            steps_performed, obs, last_terminated, last_truncated = self.perform_rollout(
                max_steps=num_steps - step,
                obs=obs,
                info=info
            )
            step += steps_performed

            self.callback.on_rollout_done(self, step, info)

            self.optimize(obs, np.logical_or(last_terminated, last_truncated), info)

            self.callback.on_optimization_done(self, step, info)

            self.buffer.reset()

