from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContactProfile:
    """
    Perfil usado por ContactModel para decidir cuántos contactos efectivos
    se generan dentro de un evento.

    base_contacts_per_slot:
        Contactos esperados por agente infeccioso y slot de simulación.

    density_relevance:
        Cuánto afecta la ocupación del espacio al número de contactos.

    max_contact_fraction:
        Fracción máxima de asistentes que un infeccioso puede contactar
        dentro de un evento.

    min_contact_duration_slots / max_contact_duration_slots:
        Rango de duración de los contactos generados.
    """

    base_contacts_per_slot: float
    density_relevance: float
    max_contact_fraction: float
    min_contact_duration_slots: int
    max_contact_duration_slots: int


@dataclass(frozen=True)
class TransmissionProfile:
    """
    Perfil usado por TransmissionModel para modificar la probabilidad de
    contagio cuando ya existe un contacto efectivo.

    transmission_modifier:
        Multiplicador del riesgo base de transmisión.

    duration_relevance:
        Cuánto importa la duración del contacto.

    ventilation_risk_reduction:
        Reducción máxima del riesgo si el espacio está ventilado.

    mask_risk_reduction:
        Reducción máxima del riesgo si se aplica una intervención de mascarilla.
        Se deja preparado para intervenciones futuras.
    """

    transmission_modifier: float
    duration_relevance: float
    ventilation_risk_reduction: float
    mask_risk_reduction: float


DEFAULT_CONTACT_PROFILE = ContactProfile(
    base_contacts_per_slot=0.6,
    density_relevance=1.0,
    max_contact_fraction=0.30,
    min_contact_duration_slots=1,
    max_contact_duration_slots=1,
)


DEFAULT_TRANSMISSION_PROFILE = TransmissionProfile(
    transmission_modifier=1.0,
    duration_relevance=1.0,
    ventilation_risk_reduction=0.25,
    mask_risk_reduction=0.35,
)


CONTACT_PROFILES: dict[str, ContactProfile] = {
    # Clase: contactos moderados, no todos contactan con todos.
    "classroom": ContactProfile(
        base_contacts_per_slot=0.4,
        density_relevance=0.8,
        max_contact_fraction=0.25,
        min_contact_duration_slots=1,
        max_contact_duration_slots=1,
    ),

    # Laboratorio: más interacción cercana y trabajo en grupos pequeños.
    "lab": ContactProfile(
        base_contacts_per_slot=0.8,
        density_relevance=1.0,
        max_contact_fraction=0.40,
        min_contact_duration_slots=1,
        max_contact_duration_slots=2,
    ),

    # Pasillo: contactos breves, pero la densidad afecta bastante.
    "corridor": ContactProfile(
        base_contacts_per_slot=0.5,
        density_relevance=1.2,
        max_contact_fraction=0.20,
        min_contact_duration_slots=1,
        max_contact_duration_slots=1,
    ),

    # Sala común: interacción social más probable y mezcla entre grupos.
    "common_space": ContactProfile(
        base_contacts_per_slot=0.9,
        density_relevance=1.1,
        max_contact_fraction=0.50,
        min_contact_duration_slots=1,
        max_contact_duration_slots=2,
    ),
}


TRANSMISSION_PROFILES: dict[str, TransmissionProfile] = {
    # Clase: riesgo base.
    "classroom": TransmissionProfile(
        transmission_modifier=1.0,
        duration_relevance=1.0,
        ventilation_risk_reduction=0.30,
        mask_risk_reduction=0.40,
    ),

    # Laboratorio: riesgo algo mayor por interacción cercana.
    "lab": TransmissionProfile(
        transmission_modifier=1.15,
        duration_relevance=1.1,
        ventilation_risk_reduction=0.30,
        mask_risk_reduction=0.40,
    ),

    # Pasillo: contacto breve, menor riesgo por contacto efectivo.
    "corridor": TransmissionProfile(
        transmission_modifier=0.7,
        duration_relevance=0.5,
        ventilation_risk_reduction=0.15,
        mask_risk_reduction=0.25,
    ),

    # Sala común: contacto social más relevante.
    "common_space": TransmissionProfile(
        transmission_modifier=1.25,
        duration_relevance=1.2,
        ventilation_risk_reduction=0.25,
        mask_risk_reduction=0.35,
    ),
}


def get_contact_profile(space_type_uuid: str | None) -> ContactProfile:
    if not space_type_uuid:
        return DEFAULT_CONTACT_PROFILE

    return CONTACT_PROFILES.get(space_type_uuid, DEFAULT_CONTACT_PROFILE)


def get_transmission_profile(space_type_uuid: str | None) -> TransmissionProfile:
    if not space_type_uuid:
        return DEFAULT_TRANSMISSION_PROFILE

    return TRANSMISSION_PROFILES.get(space_type_uuid, DEFAULT_TRANSMISSION_PROFILE)