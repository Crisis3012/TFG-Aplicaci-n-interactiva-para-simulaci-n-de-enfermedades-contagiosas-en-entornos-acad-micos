from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any


class DiseaseState(Enum):
    SUSCEPTIBLE = "susceptible"
    EXPOSED = "exposed"
    INFECTIOUS = "infectious"
    RECOVERED = "recovered"


@dataclass
class DiseaseConfig:
    """
    Configuración básica de una enfermedad simulada.

    Todos los tiempos se expresan en slots de simulación.
    Si el slot base es de 30 minutos, 1 hora = 2 slots.
    """

    name: str = "Enfermedad personalizada"

    # Probabilidad base de transmisión por contacto efectivo.
    base_transmission_probability: float = 0.03

    # Tiempo desde infección hasta volverse infeccioso.
    incubation_slots: int = 48

    # Duración total de la fase infecciosa.
    infectious_duration_slots: int = 96

    # Primera parte de la fase infecciosa con mayor infectividad.
    high_infectiousness_duration_slots: int = 32

    # Multiplicadores de infectividad.
    high_infectiousness_multiplier: float = 1.5
    low_infectiousness_multiplier: float = 0.7

    # Probabilidad de que un infectado no asista a un evento.
    absenteeism_probability: float = 0.2

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("El nombre de la enfermedad no puede estar vacío.")

        if not 0 <= self.base_transmission_probability <= 1:
            raise ValueError("base_transmission_probability debe estar entre 0 y 1.")

        if self.incubation_slots < 0:
            raise ValueError("incubation_slots no puede ser negativo.")

        if self.infectious_duration_slots <= 0:
            raise ValueError("infectious_duration_slots debe ser mayor que 0.")

        if self.high_infectiousness_duration_slots < 0:
            raise ValueError("high_infectiousness_duration_slots no puede ser negativo.")

        if self.high_infectiousness_duration_slots > self.infectious_duration_slots:
            raise ValueError(
                "high_infectiousness_duration_slots no puede ser mayor que infectious_duration_slots."
            )

        if self.high_infectiousness_multiplier < 0:
            raise ValueError("high_infectiousness_multiplier no puede ser negativo.")

        if self.low_infectiousness_multiplier < 0:
            raise ValueError("low_infectiousness_multiplier no puede ser negativo.")

        if not 0 <= self.absenteeism_probability <= 1:
            raise ValueError("absenteeism_probability debe estar entre 0 y 1.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiseaseConfig":
        return cls(**data)


def get_default_disease_presets() -> dict[str, DiseaseConfig]:
    """
    Enfermedades predeterminadas.

    Estos valores son presets iniciales de trabajo, no parámetros calibrados.
    Más adelante podrán ajustarse o sustituirse por presets mejor definidos.
    """

    return {
        "COVID-like": DiseaseConfig(
            name="COVID-like",
            base_transmission_probability=0.035,
            incubation_slots=96,
            infectious_duration_slots=160,
            high_infectiousness_duration_slots=64,
            high_infectiousness_multiplier=1.6,
            low_infectiousness_multiplier=0.7,
            absenteeism_probability=0.25,
        ),
        "Gripe-like": DiseaseConfig(
            name="Gripe-like",
            base_transmission_probability=0.04,
            incubation_slots=48,
            infectious_duration_slots=96,
            high_infectiousness_duration_slots=40,
            high_infectiousness_multiplier=1.5,
            low_infectiousness_multiplier=0.6,
            absenteeism_probability=0.3,
        ),
        "Baja transmisión": DiseaseConfig(
            name="Baja transmisión",
            base_transmission_probability=0.015,
            incubation_slots=72,
            infectious_duration_slots=96,
            high_infectiousness_duration_slots=32,
            high_infectiousness_multiplier=1.3,
            low_infectiousness_multiplier=0.6,
            absenteeism_probability=0.15,
        ),
        "Alta transmisión": DiseaseConfig(
            name="Alta transmisión",
            base_transmission_probability=0.07,
            incubation_slots=48,
            infectious_duration_slots=120,
            high_infectiousness_duration_slots=48,
            high_infectiousness_multiplier=1.8,
            low_infectiousness_multiplier=0.8,
            absenteeism_probability=0.2,
        ),
    }