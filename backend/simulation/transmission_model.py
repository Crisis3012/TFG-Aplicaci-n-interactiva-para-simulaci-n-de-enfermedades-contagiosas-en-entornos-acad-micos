from __future__ import annotations

import random
import uuid

from backend.simulation.agent import SimulationAgent
from backend.simulation.config import InterventionConfig, InterventionEffectType
from backend.simulation.contact import Contact, InfectionEvent
from backend.simulation.disease import DiseaseConfig, DiseaseState
from backend.simulation.event import SimulationEvent, SpaceContext
from backend.simulation.space_profiles import get_transmission_profile


class TransmissionModel:
    """
    Procesa contactos efectivos y decide si producen contagios.

    La probabilidad de contagio depende de:
    - transmisibilidad base de la enfermedad,
    - infectividad actual del agente infeccioso,
    - tipo de espacio,
    - duración del contacto,
    - ventilación,
    - intervenciones activas.
    """

    def process_contacts(
        self,
        contacts: list[Contact],
        agents_by_id: dict[str, SimulationAgent],
        event: SimulationEvent,
        space_context: SpaceContext | None,
        disease: DiseaseConfig,
        rng: random.Random,
        interventions: list[InterventionConfig] | None = None,
    ) -> list[InfectionEvent]:
        if not contacts:
            return []

        infection_events: list[InfectionEvent] = []

        for contact in contacts:
            source_agent = agents_by_id.get(contact.source_agent_id)
            target_agent = agents_by_id.get(contact.target_agent_id)

            if source_agent is None or target_agent is None:
                continue

            if source_agent.state != DiseaseState.INFECTIOUS:
                continue

            if target_agent.state != DiseaseState.SUSCEPTIBLE:
                continue

            probability = self.calculate_transmission_probability(
                source_agent=source_agent,
                contact=contact,
                event=event,
                space_context=space_context,
                disease=disease,
                interventions=interventions or [],
            )

            if probability <= 0:
                continue

            if rng.random() >= probability:
                continue

            infection_chain_id = (
                source_agent.infection_chain_id
                or source_agent.agent_id
            )

            was_infected = target_agent.infect(
                current_slot=contact.start_slot,
                disease=disease,
                source_agent_id=source_agent.agent_id,
                infection_chain_id=infection_chain_id,
                initial_state=DiseaseState.EXPOSED,
            )

            if not was_infected:
                continue

            infection_events.append(
                InfectionEvent(
                    infection_id=str(uuid.uuid4()),
                    source_agent_id=source_agent.agent_id,
                    infected_agent_id=target_agent.agent_id,
                    event_id=event.event_id,
                    space_uuid=event.space_uuid,
                    slot=contact.start_slot,
                    transmission_probability=probability,
                    infection_chain_id=infection_chain_id,
                )
            )

        return infection_events

    def calculate_transmission_probability(
        self,
        source_agent: SimulationAgent,
        contact: Contact,
        event: SimulationEvent,
        space_context: SpaceContext | None,
        disease: DiseaseConfig,
        interventions: list[InterventionConfig],
    ) -> float:
        profile = get_transmission_profile(
            space_context.space_type_uuid if space_context is not None else None
        )

        infectiousness = source_agent.get_infectiousness_multiplier(
            current_slot=contact.start_slot,
            disease=disease,
        )

        if infectiousness <= 0:
            return 0.0

        space_modifier = profile.transmission_modifier

        if space_context is not None:
            # Permite que SpaceType.duration_relevance y el perfil trabajen juntos.
            duration_relevance = (
                profile.duration_relevance
                * max(0.0, space_context.duration_relevance)
            )
        else:
            duration_relevance = profile.duration_relevance

        ventilation_modifier = self._calculate_ventilation_modifier(
            space_context=space_context,
            profile_ventilation_reduction=profile.ventilation_risk_reduction,
        )

        intervention_modifier = self._calculate_intervention_modifier(
            interventions=interventions,
            event=event,
            space_context=space_context,
            current_slot=contact.start_slot,
        )

        per_slot_probability = (
            disease.base_transmission_probability
            * infectiousness
            * space_modifier
            * ventilation_modifier
            * intervention_modifier
        )

        per_slot_probability = self._clamp_probability(per_slot_probability)

        effective_duration = max(
            1.0,
            contact.duration_slots * duration_relevance,
        )

        # Probabilidad acumulada durante la duración del contacto:
        # P = 1 - (1 - p)^duration
        probability = 1 - ((1 - per_slot_probability) ** effective_duration)

        return self._clamp_probability(probability)

    def _calculate_ventilation_modifier(
        self,
        space_context: SpaceContext | None,
        profile_ventilation_reduction: float,
    ) -> float:
        if space_context is None:
            return 1.0

        if not space_context.ventilated:
            return 1.0

        relevance = max(0.0, space_context.ventilation_effect_relevance)
        reduction = profile_ventilation_reduction * relevance
        reduction = self._clamp(reduction, minimum=0.0, maximum=0.95)

        return 1.0 - reduction

    def _calculate_intervention_modifier(
        self,
        interventions: list[InterventionConfig],
        event: SimulationEvent,
        space_context: SpaceContext | None,
        current_slot: int,
    ) -> float:
        """
        Aplica solo intervenciones de tipo TRANSMISSION_MODIFIER.

        Por ahora las demás intervenciones se dejan para el motor:
        - CONTACT_MODIFIER afectará al ContactModel.
        - ATTENDANCE_MODIFIER afectará a asistencia.
        - SPACE_CLOSURE afectará a eventos disponibles.
        - ISOLATION_RULE afectará a agentes.
        """

        modifier = 1.0

        for intervention in interventions:
            if intervention.effect_type != InterventionEffectType.TRANSMISSION_MODIFIER:
                continue

            if not intervention.is_active(current_slot):
                continue

            if not self._intervention_targets_event(
                intervention=intervention,
                event=event,
                space_context=space_context,
            ):
                continue

            modifier *= intervention.value

        return max(0.0, modifier)

    def _intervention_targets_event(
        self,
        intervention: InterventionConfig,
        event: SimulationEvent,
        space_context: SpaceContext | None,
    ) -> bool:
        target_type = intervention.target_type

        if target_type == "whole_faculty":
            return True

        if target_type == "space":
            return event.space_uuid in intervention.target_uuids

        if target_type == "space_type":
            if space_context is None:
                return False
            return space_context.space_type_uuid in intervention.target_uuids

        if target_type == "academic_group":
            return event.academic_group_id in intervention.target_uuids

        if target_type == "course":
            return event.course_uuid in intervention.target_uuids

        if target_type == "career":
            return event.career_uuid in intervention.target_uuids

        return False

    @staticmethod
    def _clamp_probability(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))