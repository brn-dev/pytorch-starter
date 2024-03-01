import torch

from src.networks.layered_net import LayeredNet
from src.networks.net import Net
from src.networks.net_list import NetList


class ParallelNet(LayeredNet):

    @staticmethod
    def compute_parallel_layer_in_out_features(
            in_size: int = None,
            out_sizes: list[int] = None,

            num_layers: int = None,
            num_features: int = None
    ) -> list[tuple[int, int]]:
        assert in_size is None and out_sizes is None or in_size is not None and out_sizes is not None
        assert [in_size, num_layers].count(None) == 1

        if num_layers is not None:
            in_size = num_features
            out_sizes = [num_features] * num_layers

        in_out_features = [(in_size, out_size) for out_size in out_sizes]
        return in_out_features

    @staticmethod
    def from_layer_provider(
            layer_provider: Net.LayerProvider,
            in_size: int = None,
            out_sizes: list[int] = None,
            num_layers: int = None,
            num_features: int = None
    ) -> 'ParallelNet':

        in_out_features = ParallelNet.compute_parallel_layer_in_out_features(
            in_size, out_sizes, num_layers, num_features
        )

        layers = ParallelNet.create_layer_list(layer_provider, in_out_features)
        return ParallelNet(layers)

    def __init__(self, layers: NetList):
        assert Net.are_all_in_out_features_defined(layers)

        super().__init__(
            in_features=layers[0].in_features,
            out_features=sum(layer.out_features for layer in layers),
            layers=layers,
            layer_connections=LayeredNet.LayerConnections.by_name('parallel', len(layers))
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        outs: list[torch.Tensor] = []

        for layer in self._layers:
            outs.append(layer(x))

        return torch.cat(outs, dim=-1)