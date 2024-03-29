from typing import Callable

import torch
from torch import nn

from src.networks.core.net import Net
from src.networks.fnn import FNN
from src.networks.multihead_self_attention import MultiheadSelfAttention
from src.networks.skip_connection import ResidualSkipConnection
from src.networks.weighing import WeighingTypes, WeighingTrainableChoices


class TransformerEncoder(Net):

    def __init__(
            self,
            num_layers: int,
            num_features: int,
            attention_num_heads: int,
            attention_dropout=0.0,
            feedforward_provider: Callable[[int], nn.Module] = lambda num_features: FNN(
                in_size=num_features, out_sizes=[2048, num_features]
            ),
            post_attention_normalization_provider: Callable[[int], nn.Module]
                    = lambda num_features: nn.LayerNorm(num_features),
            post_fnn_normalization_provider: Callable[[int], nn.Module]
                    = lambda num_features: nn.LayerNorm(num_features),
            skip_connection_weight: WeighingTypes = 1.0,
            skip_connection_weight_trainable: WeighingTrainableChoices = False,
            batch_first=False,
    ):
        super().__init__()

        self.layers = []

        for i in range(num_layers):
            self.layers.append((
                ResidualSkipConnection(
                    layer=MultiheadSelfAttention(
                        embed_dim=num_features,
                        num_heads=attention_num_heads,
                        dropout=attention_dropout,
                        batch_first=batch_first,
                    ),
                    num_features=num_features,
                    skip_connection_weight=skip_connection_weight,
                    skip_connection_weight_trainable=skip_connection_weight_trainable,
                    normalization_provider=post_attention_normalization_provider,
                ),
                ResidualSkipConnection(
                    layer=feedforward_provider(num_features),
                    num_features=num_features,
                    skip_connection_weight=skip_connection_weight,
                    skip_connection_weight_trainable=skip_connection_weight_trainable,
                    normalization_provider=post_fnn_normalization_provider,
                )
            ))

        self.modules = nn.ModuleList([
            module
            for layer in self.layers
            for module in layer
        ])


    def forward(self, x: torch.Tensor, key_padding_mask: torch.Tensor = None, attn_mask: torch.Tensor = None):
        for attention_sublayer, fnn_sublayer in self.layers:
            x = attention_sublayer(x, key_padding_mask=key_padding_mask, attn_mask=attn_mask)
            x = fnn_sublayer(x)
        return x
