from __future__ import annotations

import math
import random

from backend.simulation.agent import SimulationAgent
from backend.simulation.contact import Contact
from backend.simulation.disease import DiseaseState
from backend.simulation.event import SimulationEvent, SpaceContext
from backend.simulation.space_profiles import get_contact_profile


class ContactModel:
    """
    Genera contactos efectivos dentro de un evento.

    La co-presencia en un espacio no implica contacto automático.
    Este modelo genera un subconjunto de contactos a partir de:
    - tipo de espacio,
    - duración del evento,
    - ocupación/densidad,
    - agentes infecciosos presentes.
    """

    def generate_contacts(
        self,
        event: SimulationEvent,
        agents_in_event: list[SimulationAgent],
        space_context: SpaceContext | None,
        rng: random.Random,
    ) -> list[Contact]:
        if not agents_in_event:
            return []

        infectious_agents = [
            agent
            for agent in agents_in_event
            if agent.state == DiseaseState.INFECTIOUS
        ]

        if not infectious_agents:
            return []

        profile = get_contact_profile(
            space_context.space_type_uuid if space_context is not None else None
        )

        contacts: list[Contact] = []

        for source_agent in infectious_agents:
            possible_targets = [
                agent
                for agent in agents_in_event
                if agent.agent_id != source_agent.agent_id
            ]

            if not possible_targets:
                continue

            expected_contacts = self._calculate_expected_contacts(
                event=event,
                number_of_attendees=len(agents_in_event),
                space_context=space_context,
                base_contacts_per_slot=profile.base_contacts_per_slot,
                density_relevance=profile.density_relevance,
            )

            sampled_contacts = self._sample_poisson(
                expected_value=expected_contacts,
                rng=rng,
            )

            max_contacts = self._calculate_max_contacts(
                number_of_possible_targets=len(possible_targets),
                max_contact_fraction=profile.max_contact_fraction,
            )

            number_of_contacts = min(
                sampled_contacts,
                max_contacts,
                len(possible_targets),
            )

            if number_of_contacts <= 0:
                continue

            selected_targets = rng.sample(possible_targets, k=number_of_contacts)

            for target_agent in selected_targets:
                contact_duration = self._sample_contact_duration(
                    event_duration_slots=event.duration_slots,
                    min_duration_slots=profile.min_contact_duration_slots,
                    max_duration_slots=profile.max_contact_duration_slots,
                    rng=rng,
                )

                contact_start_slot = self._sample_contact_start_slot(
                    event=event,
                    contact_duration_slots=contact_duration,
                    rng=rng,
                )

                contacts.append(
                    Contact(
                        source_agent_id=source_agent.agent_id,
                        target_agent_id=target_agent.agent_id,
                        event_id=event.event_id,
                        space_uuid=event.space_uuid,
                        start_slot=contact_start_slot,
                        duration_slots=contact_duration,
                    )
                )

        return contacts

    def _calculate_expected_contacts(
        self,
        event: SimulationEvent,
        number_of_attendees: int,
        space_context: SpaceContext | None,
        base_contacts_per_slot: float,
        density_relevance: float,
    ) -> float:
        duration_factor = max(1, event.duration_slots)

        contact_level = 1.0
        if space_context is not None:
            contact_level = max(0.0, space_context.contact_level)

        density_factor = self._calculate_density_factor(
            number_of_attendees=number_of_attendees,
            space_context=space_context,
            density_relevance=density_relevance,
        )

        expected_contacts = (
            base_contacts_per_slot
            * duration_factor
            * contact_level
            * density_factor
        )

        return max(0.0, expected_contacts)

    def _calculate_density_factor(
        self,
        number_of_attendees: int,
        space_context: SpaceContext | None,
        density_relevance: float,
    ) -> float:
        if space_context is None:
            return 1.0

        # Los pasillos se tratan como espacios de capacidad efectiva infinita.
        # Por tanto, no penalizamos ni amplificamos contactos por sobreocupación.
        if space_context.is_transit_type or space_context.space_type_uuid == "corridor":
            return 1.0

        if space_context.capacity is None or space_context.capacity <= 0:
            return 1.0

        occupancy_ratio = number_of_attendees / space_context.capacity

        raw_factor = 0.75 + occupancy_ratio * density_relevance

        return self._clamp(raw_factor, minimum=0.5, maximum=2.0)

    def _calculate_max_contacts(
        self,
        number_of_possible_targets: int,
        max_contact_fraction: float,
    ) -> int:
        if number_of_possible_targets <= 0:
            return 0

        if max_contact_fraction <= 0:
            return 0

        max_contacts = math.ceil(number_of_possible_targets * max_contact_fraction)

        # Permitimos al menos 1 contacto si hay targets y la fracción es positiva.
        return max(1, max_contacts)

    def _sample_contact_duration(
        self,
        event_duration_slots: int,
        min_duration_slots: int,
        max_duration_slots: int,
        rng: random.Random,
    ) -> int:
        event_duration_slots = max(1, event_duration_slots)

        min_duration_slots = max(1, min_duration_slots)
        max_duration_slots = max(min_duration_slots, max_duration_slots)
        max_duration_slots = min(max_duration_slots, event_duration_slots)

        return rng.randint(min_duration_slots, max_duration_slots)

    def _sample_contact_start_slot(
        self,
        event: SimulationEvent,
        contact_duration_slots: int,
        rng: random.Random,
    ) -> int:
        latest_start = event.end_slot - contact_duration_slots

        if latest_start <= event.start_slot:
            return event.start_slot

        return rng.randint(event.start_slot, latest_start)

    def _sample_poisson(
        self,
        expected_value: float,
        rng: random.Random,
    ) -> int:
        """
        Muestreo Poisson sin depender de numpy.

        Para valores pequeños usa el algoritmo clásico de Knuth.
        Para valores grandes usa una aproximación normal simple.
        """

        if expected_value <= 0:
            return 0

        if expected_value < 30:
            limit = math.exp(-expected_value)
            k = 0
            product = 1.0

            while product > limit:
                k += 1
                product *= rng.random()

            return k - 1

        sampled = rng.gauss(expected_value, math.sqrt(expected_value))
        return max(0, int(round(sampled)))

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))