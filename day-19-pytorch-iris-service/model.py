"""Model definition for the Iris classifier.

A small multilayer perceptron: 4 inputs (the Iris measurements) ->
one hidden layer -> 3 outputs (setosa / versicolor / virginica).
Kept separate from training and serving so both can import it.
"""

import torch
import torch.nn as nn

CLASSES = ["setosa", "versicolor", "virginica"]
N_FEATURES = 4


class IrisMLP(nn.Module):
    """4 -> hidden -> hidden -> 3 classifier with ReLU activations."""

    def __init__(self, hidden: int = 16):
        super().__init__()
        self.hidden = hidden
        self.net = nn.Sequential(
            nn.Linear(N_FEATURES, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, len(CLASSES)),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def predict_species(model: IrisMLP, features, mean, std):
    """Return (species, {species: probability}) for one 4-float sample."""
    model.eval()
    x = (torch.tensor([features], dtype=torch.float32) - torch.tensor(mean)) / torch.tensor(std)
    with torch.no_grad():
        probs = torch.softmax(model(x), dim=1)[0]
    best = int(torch.argmax(probs))
    return CLASSES[best], {c: round(float(p), 4) for c, p in zip(CLASSES, probs)}
