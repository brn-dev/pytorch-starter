from typing import Tuple, Optional, Union, List, SupportsFloat, Iterable

import numpy as np
from gymnasium.core import RenderFrame, Env
from gymnasium.vector import VectorEnv


def as_vec_env(env: Env) -> tuple[VectorEnv, int]:
    try:
        num_envs = env.get_wrapper_attr('num_envs')
        return env, num_envs  # type: ignore
    except AttributeError:
        return SingletonVectorEnv(env), 1


class SingletonVectorEnv(VectorEnv):

    def __init__(self, env: Env):
        super().__init__(
            num_envs=1,
            observation_space=env.observation_space,
            action_space=env.action_space
        )
        self.env = env
        self.render_mode = env.render_mode

        self._actions: np.ndarray = np.empty((0,))

    def reset_wait(self, seed: Optional[Union[int, List[int]]] = None, options: Optional[dict] = None):
        obs, infos = self.env.reset(seed=seed, options=options)

        return self._add_env_singleton_dim(obs), infos

    def step_async(self, actions):
        self._actions = actions

    def step_wait(self, **kwargs) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
        obs, rewards, terminated, truncated, info = self.env.step(self._actions[0])

        return (
            self._add_env_singleton_dim(obs),
            self._add_env_singleton_dim(rewards),
            self._add_env_singleton_dim(terminated),
            self._add_env_singleton_dim(truncated),
            info
        )

    def render(self) -> RenderFrame | list[RenderFrame] | None:
        return self.env.render()

    @staticmethod
    def _add_env_singleton_dim(val: SupportsFloat | np.ndarray):

        arr = np.asarray(val)

        return np.expand_dims(arr, axis=0)

