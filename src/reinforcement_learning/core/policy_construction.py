from dataclasses import dataclass
import inspect
from typing import TypedDict, Callable, Protocol, TypeVar, Optional, Any

import gymnasium
from torch import optim
from torch.optim import Optimizer

from src.reinforcement_learning.core.action_selectors.action_selector import ActionSelector
from src.reinforcement_learning.core.policies.base_policy import BasePolicy

InitializationHyperParameters = dict[str, Any]
ChangeHyperParametersFunction = Callable[[InitializationHyperParameters], None]


class PolicyInitializationInfo(TypedDict):

    init_action_selector_source_code: str
    init_policy_source_code: str
    init_optimizer_source_code: str
    wrap_env_source_code: str

    hyper_parameters: InitializationHyperParameters


class InitActionSelectorFunction(Protocol):
    def __call__(
            self,
            latent_dim: int,
            action_dim: int,
            hyper_parameters: InitializationHyperParameters
    ) -> ActionSelector:
        raise NotImplemented


InitPolicyFunction = Callable[[InitActionSelectorFunction, InitializationHyperParameters], BasePolicy]
InitOptimizerFunction = Callable[[BasePolicy, InitializationHyperParameters], optim.Optimizer]
WrapEnvFunction = Callable[[gymnasium.Env, InitializationHyperParameters], gymnasium.Env]

StateDict = dict[str, Any]
ApplyPolicyStateDictFunction = Callable[[BasePolicy, StateDict], None]
ApplyOptimizerStateDictFunction = Callable[[optim.Optimizer, StateDict], None]


def create_policy_initialization_info(
    init_action_selector: InitActionSelectorFunction,
    init_policy: InitPolicyFunction,
    init_optimizer: InitOptimizerFunction,
    wrap_env: WrapEnvFunction,
    hyper_parameters: Optional[InitializationHyperParameters] = None,
) -> PolicyInitializationInfo:
    return {
        'init_action_selector_source_code': inspect.getsource(init_action_selector),
        'init_policy_source_code': inspect.getsource(init_policy),
        'init_optimizer_source_code': inspect.getsource(init_optimizer),
        'wrap_env_source_code': inspect.getsource(wrap_env),
        'hyper_parameters': hyper_parameters or {},  # type: ignore
    }


SomeFunction = TypeVar('SomeFunction', bound=Callable)


def override_initialization_function(info: PolicyInitializationInfo, key: str, fun: Optional[SomeFunction]) -> None:
    if fun is not None:
        info[key] = inspect.getsource(fun)  # type: ignore


def get_initialization_function(info: PolicyInitializationInfo, key: str) -> SomeFunction:
    fun_source_code: str = info[key]  # type: ignore

    locals_globals = {}
    exec(fun_source_code, locals_globals)

    assert len(locals_globals) == 1
    return list(locals_globals.values())[0]


OverrideConditionFunction = Callable[[PolicyInitializationInfo], bool]


@dataclass
class PolicyConstructionOverride:
    init_action_selector: Optional[InitActionSelectorFunction] = None
    init_policy: Optional[InitPolicyFunction] = None
    init_optimizer: Optional[InitOptimizerFunction] = None
    wrap_env: Optional[WrapEnvFunction] = None

    change_hyper_parameters: Optional[ChangeHyperParametersFunction] = None

    apply_policy_state_dict: Optional[ApplyPolicyStateDictFunction] = None
    apply_optimizer_state_dict: Optional[ApplyOptimizerStateDictFunction] = None

    override_condition: Optional[OverrideConditionFunction] = None

    def override_initialization_info(self, info: PolicyInitializationInfo):
        if self.override_condition is None or self.override_condition(info):
            override_initialization_function(info, 'init_action_selector_source_code', self.init_action_selector)
            override_initialization_function(info, 'init_policy_source_code', self.init_policy)
            override_initialization_function(info, 'init_optimizer_source_code', self.init_optimizer)
            override_initialization_function(info, 'wrap_env_source_code', self.wrap_env)

            if self.change_hyper_parameters is not None:
                self.change_hyper_parameters(info['hyper_parameters'])

        return info


class PolicyConstruction:

    @staticmethod
    def init_from_info(
            info: PolicyInitializationInfo,
            env: gymnasium.Env,
    ) -> tuple[BasePolicy, Optimizer, gymnasium.Env]:

        init_action_selector = get_initialization_function(info, 'init_action_selector_source_code')
        init_policy = get_initialization_function(info, 'init_policy_source_code')
        init_optimizer = get_initialization_function(info, 'init_optimizer_source_code')
        wrap_env = get_initialization_function(info, 'wrap_env_source_code')
        hyper_parameters = info['hyper_parameters']

        policy = init_policy(init_action_selector, hyper_parameters)
        optimizer = init_optimizer(policy, hyper_parameters)

        env = wrap_env(env, hyper_parameters)

        return policy, optimizer, env

    @staticmethod
    def apply_state_dicts(
            policy: BasePolicy,
            policy_state_dict: Optional[StateDict],
            optimizer: optim.Optimizer,
            optimizer_state_dict: Optional[StateDict],
            apply_policy_state_dict: Optional[ApplyPolicyStateDictFunction] = None,
            apply_optimizer_state_dict: Optional[ApplyOptimizerStateDictFunction] = None,
    ) -> None:
        if policy_state_dict is not None:
            if apply_policy_state_dict is not None:
                apply_policy_state_dict(policy, policy_state_dict)
            else:
                policy.load_state_dict(policy_state_dict)

        if optimizer_state_dict is not None:
            if apply_optimizer_state_dict is not None:
                apply_optimizer_state_dict(optimizer, optimizer_state_dict)
            else:
                optimizer.load_state_dict(optimizer_state_dict)

    @staticmethod
    def init_and_apply_state_dicts(
            info: PolicyInitializationInfo,
            env: gymnasium.Env,
            policy_state_dict: Optional[StateDict],
            optimizer_state_dict: Optional[StateDict],
            apply_policy_state_dict: Optional[ApplyPolicyStateDictFunction] = None,
            apply_optimizer_state_dict: Optional[ApplyOptimizerStateDictFunction] = None,
    ) -> tuple[BasePolicy, Optimizer, gymnasium.Env]:
        policy, optimizer, env = PolicyConstruction.init_from_info(info, env)

        PolicyConstruction.apply_state_dicts(
            policy=policy,
            policy_state_dict=policy_state_dict,
            optimizer=optimizer,
            optimizer_state_dict=optimizer_state_dict,
            apply_policy_state_dict=apply_policy_state_dict,
            apply_optimizer_state_dict=apply_optimizer_state_dict,
        )

        return policy, optimizer, env

