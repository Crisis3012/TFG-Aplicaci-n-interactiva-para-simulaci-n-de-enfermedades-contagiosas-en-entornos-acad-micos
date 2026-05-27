# Estructura de clases y campos

## Common fields

uuid
name


## Faculty (Builder Class)

uuid    # Autogenerado
name    # Modificable (Escribir)

opening_time    # Modificable (Selección)
closing_time    # Modificable (Selección)
schedule_slot_minutes   # Modificable (Selección)

default_ventilated  # Modificable opcional (Casilla) -> Default: False

calendar_days   # Modificable (Selección multiple)

space_groups
space_types
spaces
careers


## SpaceGroup (Space Builder Class)

uuid    # Autogenerado
name    # Modificable (Escribir)

parent_uuid # Autogenerado

default_ventilated  # Modificable opcional (Casilla) -> Default: False

opening_time_override   # Modificable (Selección) -> Default: None
closing_time_override   # Modificable (Selección) -> Default: None

expanded    # Modificable visualización (Doble click) -> Default: True


## SpaceType (Internal Class)

uuid    
name    

contact_level
duration_relevance

is_transit_type
is_recreation_type

default_ventilated

mask_effect_relevance
ventilation_effect_relevance


## Space (Space Builder Class)

uuid    # Autogenerado
name    # Modificable (Escribir)

space_type_uuid # Modificable opcional (Selección) -> Default: None
parent_group_uuid   # Autogenerado

ventilated  # Modificable opcional (Casilla) -> Default: False

opening_time_override   # Modificable (Selección) -> Default: None
closing_time_override   # Modificable (Selección) -> Default: None

position_x  # Modificable visualización (Click and Drag)
position_y  # Modificable visualización (Click and Drag)


## Career (Agent Builder Class)

uuid    # Autogenerado
name    # Modificable (Escribir)

students_by_year    # Modificable (Escribir Número)

default_attendance_rate # Modificable opcional (Seleccionar numero entre 0 y 100)

mean_age    # Modificable opcional (Escribir Numero)
std_age     # Modificable opcional (Escribir Numero)
sex_ratio   # Modificable opcional (Escribir Numero)


## Course (Agent Builder Class)

uuid    # Autogenerado
name    # Modificable (Escribir)

career_uuid # Autogenerado

number_of_students  # Modificable opcional (Escribir Numero)

attendance_rate # Modificable opcional (Seleccionar numero entre 0 y 100)

mean_age    # Modificable opcional (Escribir Numero)
std_age     # Modificable opcional (Escribir Numero)
sex_ratio   # Modificable opcional (Escribir Numero)

base_schedule   # Modificable (Tabla de horarios)

course_groups   # Autogenerado? (Se pueden mirar los hijos para repartir los estudiantes del crso entre ellos)


## CourseGroup (Agent Builder Class)

uuid    # Autogenerado
name    # Modificable (Escribir)

course_uuid # Autogenerado

number_of_students  # Autogenerado (number_of_students del curso divido entre numero de grupos)

attendance_rate # Modificable opcional (Seleccionar numero entre 0 y 100)

mean_age    # Modificable opcional (Escribir Numero)
std_age     # Modificable opcional (Escribir Numero)
sex_ratio   # Modificable opcional (Escribir Numero)


schedule_overrides  # Modificable opcional (Tabla de horarios)


## Timetable (Agent Builder Class)

uuid    # Autogenerado

owner_type  # Autogenerado
owner_uuid  # Autogenerado

blocks  # Modificable (Generado a partir de tabla de horarios)


## ScheduleBlock (Timetable builder class)

uuid    # Autogenerado

day_of_week # Modificable (Columna de tabla de horarios)

start_time  # Modificable (Fila de tabla de horarios)
end_time    # Modificable (Fila de tabla de horarios)

space_uuid  # Modifcable (Seleccionar entre espacios creados en tabla de horarios)


## ScheduleOverride (Timetable builder class)

uuid    # Autogenerado

course_group_uuid   # Autogenerado

day_of_week # Modificable (Columna de tabla de horarios)

start_time  # Modificable (Fila de tabla de horarios)
end_time    # Modificable (Fila de tabla de horarios)

space_uuid  # Modifcable (Seleccionar entre espacios creados en tabla de horarios)


## PopulationConfig

uuid
name
description
enabled

source_level

generation_mode

population_seed

use_existing_population


## AgentProfile

uuid

course_uuid
course_group_uuid

age
sex

attendance_probability

speed

compliance_level


## AgentState

uuid

simulation_uuid
agent_uuid

epidemiological_state

current_space_uuid

infection_time
infected_by_agent_uuid
infected_in_space_uuid

viral_load

isolated
quarantined

symptomatic

recovery_time


## Disease

uuid
name
description
enabled

transmission_probability

incubation_period_min
incubation_period_max

infectious_period_min
infectious_period_max

recovery_period_min
recovery_period_max

viral_load_curve

susceptibility_params

asymptomatic_probability

immunity_duration

mask_reduction_factor
ventilation_reduction_factor
distance_effect
duration_effect


## SimulationConfig

uuid
name
description
enabled

faculty_uuid
disease_uuid

start_date
end_date

time_step_minutes

population_config_uuid

initial_infected_count
initial_infected_targets

random_seed

interventions

save_logs
save_agent_history
save_space_history


## SimulationBatch

uuid
name
description
enabled

faculty_uuid
disease_uuid

base_simulation_config

number_of_runs

population_seed
simulation_seeds

scenarios


## Intervention

uuid
name
description
enabled

intervention_type

start_time
end_time

target_type
target_uuid

effect_type
effect_value

compliance


## SimulationResult

uuid

simulation_uuid

final_susceptible
final_exposed
final_infectious
final_recovered

total_infections

peak_infectious
peak_time

total_contacts
total_transmissions


## SimulationTimeLog

uuid

simulation_uuid

time

susceptible_count
exposed_count
infectious_count
recovered_count

new_infections
new_recoveries

total_contacts
total_transmissions


## SpaceTimeLog

uuid

simulation_uuid

time
space_uuid

number_of_agents
number_of_susceptible
number_of_exposed
number_of_infectious
number_of_recovered

contacts_generated
transmissions_generated


## InfectionEvent

uuid

simulation_uuid

time

infected_agent_uuid
source_agent_uuid

space_uuid

contact_duration

transmission_probability

viral_load_source

intervention_context