<!--
MASTER PLAN — version 1.0 (2026-11-16)
This is the authoritative project plan. Do not edit silently: any change must be
recorded in docs/execution_log.md (plan-change entry) and the version below bumped.
Execution progress is tracked separately in docs/execution_log.md.
-->

# Implementation Plan: Swiss Residential District Energy Simulation with CityLearn 3.3.0

**Document type:** Agent execution specification  
**Project:** Swiss Residential District Energy Simulation  
**Target framework:** CityLearn 3.3.0  
**Execution model:** Sequential, phase-gated implementation  
**Initial target region:** Zurich, Switzerland  
**Status:** Initial implementation plan — Phase A authorized for execution only

---

## 1. Project overview

### 1.1 Objective

Develop a research-quality simulation environment representing a Swiss residential district, using CityLearn 3.3.0 as the foundation.

The environment must support two complementary objectives:

1. **Energy-system research:** Represent Swiss residential buildings, heating demand, heat pumps, domestic hot water, weather, tariffs, and electricity consumption with realistic data and clearly documented assumptions.
2. **Reinforcement-learning experimentation:** Provide a functioning environment in which RL agents and existing control strategies can be trained, compared, and evaluated under Swiss conditions.

The project will initially focus on a six-building residential district in the Zurich region, with a representative mixture of single-family and multi-family buildings.

The implementation will progress through three phases, each adding complexity to the simulation.

### 1.2 Guiding principles

The following principles apply throughout the project:

- **Measured data first:** Prefer measured Swiss data wherever available and appropriate.
- **Transparent synthetic data:** Synthetic or derived values are permitted when necessary, but must always be explicitly identified and documented.
- **No fabricated measurements:** Never present estimated values as measured observations.
- **Preserve CityLearn:** Prefer configuration changes, data-schema adaptations, and custom extensions over modifications to the original CityLearn codebase.
- **Reproducibility:** Every simulation must be reproducible from documented data, configurations, code versions, and model parameters.
- **Auditability:** Every data source, transformation, model, algorithm, assumption, and experimental result must have a traceable record.
- **Incremental development:** Implement only the currently authorized phase.
- **Evidence-based decisions:** Document technical limitations and unresolved questions rather than silently making assumptions.

### 1.3 Initial modeling scope

The initial district should represent six realistic Swiss residential buildings.

The building selection should aim to capture meaningful variation in:

- Single-family versus multi-family housing.
- Building size and occupancy characteristics.
- Heating demand and seasonal consumption.
- Heat-pump electricity consumption.
- Building thermal characteristics, where available.

Building selection should prioritize a realistic representation of a Swiss residential district, with data completeness as a secondary criterion.

The initial system should include:

- Space-heating demand.
- Air-source heat pumps.
- Domestic hot water (DHW).
- Thermal storage where supported by the data and model.
- Outdoor weather conditions.
- Electricity consumption.
- Swiss electricity tariffs.
- Electricity-related carbon intensity.
- Existing CityLearn control strategies for baseline comparisons.

Cooling, PV, batteries, EVs, energy communities, and future climate scenarios will be introduced in later phases.

---

## 2. Phase roadmap

The project is divided into three phases.

| Phase | Focus | Estimated additional effort |
|---|---|---:|
| A | Swiss heating baseline | 5–8 working days |
| B | Integrated district energy system | 8–15 working days |
| C | Future climate and cooling adoption | 5–10 working days |

These estimates are indicative, not deadlines. Data-access issues, model limitations, and validation requirements take precedence over the estimates.

### Phase A — Minimum viable Swiss heating baseline

**Objective:** Build a functional, documented six-building Swiss residential simulation using hourly data.

Scope:

- Select six representative Swiss residential buildings.
- Integrate Swiss heating and electricity data.
- Represent air-source heat pumps and DHW.
- Incorporate Swiss weather data.
- Integrate an appropriate Swiss electricity tariff and carbon-intensity source.
- Configure CityLearn 3.3.0.
- Establish baseline control strategies.
- Validate the resulting simulation and document its limitations.

Expected deliverable:

A reproducible, hourly, heating-focused Swiss residential district simulation that can run baseline control experiments and serve as the foundation for subsequent phases.

### Phase B — Integrated district energy system

**Objective:** Extend the baseline into a higher-resolution district energy system with distributed renewable generation, storage, and local energy coordination.

Scope:

- Upgrade the data pipeline to support 15-minute resolution.
- Incorporate higher-resolution ETH/EKZ and HEAPO data where accessible.
- Introduce PV generation.
- Introduce battery storage.
- Incorporate electricity import and export pricing.
- Model dynamic electricity tariffs.
- Investigate local electricity sharing and LEG arrangements.
- Introduce EV charging where suitable data and assumptions are available.
- Develop or calibrate a more realistic building thermal model, such as an RC model.
- Evaluate district-level peak demand, self-consumption, self-sufficiency, and energy costs.

Expected deliverable:

A higher-resolution Swiss residential district simulation capable of studying distributed energy resources, storage, and local energy coordination.

### Phase C — Future climate and cooling adoption

**Objective:** Evaluate how climate change and increasing cooling adoption affect Swiss residential energy demand and the effectiveness of district-level energy management.

Scope:

- Establish historical climate as the reference scenario.
- Incorporate moderate and high warming scenarios.
- Introduce three cooling-adoption levels.
- Model buildings with both heating and cooling capabilities.
- Evaluate summer electricity demand and peak loads.
- Compare heating-only and mixed heating/cooling districts.
- Evaluate how control strategies perform under different climate and adoption scenarios.

Expected deliverable:

A future Swiss building-energy flexibility study comparing heating-only and heating-plus-cooling districts under historical and projected climate conditions.

---

## 3. Data acquisition and source strategy

The following sources form the initial data strategy. The execution agent must independently verify their current availability, access conditions, licensing, and suitability before using them.

| Source | Intended use | Important considerations |
|---|---|---|
| ETH HEAPO | Heat-pump electricity and household energy data | Reported 1,408 Zurich heat-pump households; 15-minute/daily data; 2018–2024. Confirm exact coverage, fields, and licence. |
| ETH/EKZ residential smart-meter dataset | Residential electricity consumption | Reported 2,447 installations; 15-minute data; 2023–2024. Verify metadata and access restrictions. |
| JASM / Empa CESAR | Swiss building archetype profiles | Heating, DHW, cooling, and electricity profiles. Verify resolution, building characteristics, and licensing. |
| MeteoSwiss | Historical weather and forecasts | Use hourly weather for Phase A where possible. Document station selection and spatial representativeness. |
| ElCom | Swiss electricity tariffs | Investigate appropriate 2026 tariffs and applicable tariff structures. |
| SFOE | PV resources and relevant energy information | Use in Phase B where appropriate. |
| Swiss carbon-intensity sources / HoroCarbon | Electricity-related emissions | Verify whether historical bulk data can be obtained and document temporal resolution and methodology. |
| CH2018 / CH2025 | Future climate scenarios | Investigate the most appropriate current scenario data for Phase C. |

### 3.1 Data-source requirements

For every dataset, record:

- Official dataset name.
- Publisher or responsible institution.
- Original repository or download URL.
- Date accessed.
- Dataset version or release.
- Licence and redistribution conditions.
- Access restrictions and approval requirements.
- Temporal coverage.
- Temporal resolution.
- Geographic coverage.
- Timezone and daylight-saving conventions.
- Relevant variables and units.
- Known limitations.
- Intended use in the simulation.

### 3.2 Data-access policy

The agent may:

- Access publicly available datasets.
- Download public files.
- Inspect data dictionaries and metadata.
- Process and transform locally available data.
- Generate derived datasets for the project.

The agent must stop and request approval before:

- Creating accounts or registering for services.
- Requesting restricted datasets.
- Using credentials or private access tokens.
- Accepting licences or data-sharing agreements.
- Proceeding where licensing or redistribution permissions are ambiguous.

The agent must never bypass access restrictions.

### 3.3 Data classification

Every variable used in the simulation must be classified as one of:

1. **Measured:** Directly observed or recorded by a source.
2. **Derived:** Calculated from measured or otherwise documented inputs.
3. **Modeled:** Generated by a physical or statistical model.
4. **Synthetic:** Created to fill a data gap or represent a scenario.

This classification must remain attached to the variable through subsequent transformations.

In particular, indoor temperatures and measured thermal heat-pump output must not be assumed to exist. If they are unavailable, their absence must be documented and any substitute must be clearly labeled as modeled or synthetic.

---

## 4. Technical architecture

The agent should first inspect the existing repository and CityLearn 3.3.0 installation before proposing architectural changes.

The intended architecture is:

1. **Source data layer:** Original downloaded files and source metadata.
2. **Processing layer:** Cleaning, filtering, temporal alignment, aggregation, unit conversion, and quality control.
3. **Canonical dataset layer:** Standardized building, weather, energy, tariff, and emissions datasets.
4. **Building model layer:** Building characteristics, heating demand, heat pumps, DHW, storage, and later PV, batteries, EVs, and cooling.
5. **CityLearn integration layer:** Dataset schema, building configuration, simulation environment, and control interfaces.
6. **Experiment layer:** Controllers, reward functions, scenarios, evaluation metrics, and experiment configurations.
7. **Audit and reporting layer:** Provenance, model documentation, experiment records, validation results, and generated reports.

### 4.1 CityLearn integration

- Use CityLearn 3.3.0 as the target framework.
- Inspect the existing schema, building attributes, storage models, energy-system representations, and available controllers before implementing custom functionality.
- Prefer adapting inputs and configurations to existing CityLearn functionality.
- Implement custom modules or extensions where necessary.
- Keep the original CityLearn code intact wherever practical.
- If a modification to the original framework becomes necessary, document the reason, scope, and consequences, and isolate the change so it can be reviewed and maintained.

### 4.2 Temporal resolution

Phase A must operate hourly.

However, the data-processing architecture must preserve the ability to support 15-minute data in Phase B.

Avoid irreversible aggregation of source data. Preserve original-resolution data and generate hourly datasets as derived outputs.

Document all temporal aggregation, interpolation, resampling, and alignment decisions.

### 4.3 Avoiding double counting

The agent must explicitly investigate the relationship between:

- Total household electricity consumption.
- Heat-pump electricity consumption.
- Space-heating thermal demand.
- DHW thermal demand.
- Other household electrical loads.

Do not add heat-pump electricity to total household consumption if it is already included.

Likewise, do not count both measured thermal output and modeled thermal demand as separate energy consumption.

Document the energy balance and the interpretation of each dataset before integrating it into CityLearn.

---

## 5. Auditability and project paper trail

**This section is mandatory and applies to every phase.**

The project must maintain a comprehensive, persistent record of how the simulation was constructed and how its results were produced.

The purpose is to allow a future researcher or reviewer to trace a result back through the experiment, model, configuration, transformations, and original data.

### 5.1 Required project documentation

Maintain a structured documentation directory in the repository. At minimum:

```text
docs/
    project_overview.md
    architecture.md
    implementation_plan.md

    data/
        data_source_registry.csv
        data_dictionary.md
        data_quality_reports/
        transformation_log.md

    models/
        model_registry.md
        model_assumptions.md
        parameter_registry.csv

    algorithms/
        algorithm_registry.md
        controller_documentation.md
        reward_function_documentation.md

    decisions/
        decision_log.md
        assumptions_log.md
        issues_and_risks.md

    experiments/
        experiment_registry.csv
        experiment_protocol.md
        results/
        validation_reports/

    phases/
        phase_a_completion_report.md
        phase_b_completion_report.md
        phase_c_completion_report.md
```

The agent may refine this structure, but it must preserve the underlying documentation requirements.

### 5.2 Data provenance registry

Every original dataset and every derived dataset must have a unique identifier.

The data-source registry must include:

- Dataset ID.
- Dataset name and publisher.
- Original URL or repository reference.
- Version or release.
- Access date.
- Licence and usage restrictions.
- Original filename.
- File format.
- Temporal and geographic coverage.
- Variables used.
- Data classification.
- Processing status.
- Checksums or cryptographic hashes where practical.
- Derived dataset IDs.
- Relevant documentation and quality reports.

Original downloaded files must be preserved separately from processed data.

Where redistribution is prohibited, do not copy source files into a distributable repository. Record their location, identifying metadata, and checksum where permitted.

### 5.3 Transformation lineage

Every processing step must be documented.

For each transformation, record:

- Transformation ID.
- Input dataset IDs.
- Output dataset ID.
- Script or module responsible.
- Code version or Git commit.
- Date executed.
- Parameters and configuration.
- Units before and after.
- Temporal operations performed.
- Missing-value treatment.
- Filtering and exclusions.
- Any assumptions introduced.
- Validation checks and results.

The processing pipeline should be scripted and reproducible rather than relying on undocumented manual edits.

### 5.4 Model registry

Maintain a registry of every physical, statistical, or empirical model used.

For each model, record:

- Model ID and name.
- Purpose.
- Source, reference, or implementation.
- Version.
- Governing equations or methodology.
- Input variables and units.
- Output variables and units.
- Parameters and their sources.
- Calibration procedure, if applicable.
- Validation procedure and results.
- Known limitations.
- Whether it is measured-data-driven, empirical, physical, or synthetic.

This applies to heat-pump performance, building thermal dynamics, heating demand, PV generation, batteries, EVs, and cooling models as they are introduced.

### 5.5 Algorithm and controller registry

Every control algorithm must be documented.

Record:

- Algorithm ID and name.
- Original source or publication.
- Implementation location.
- Version.
- Control objective.
- State and observation variables.
- Action variables.
- Constraints.
- Reward function, if applicable.
- Hyperparameters and configuration.
- Training procedure and random seeds.
- Evaluation protocol.
- Known limitations.

Existing CityLearn controllers must be documented just as custom controllers are.

### 5.6 Assumption and decision logs

Every important modeling decision must have a written justification.

Examples include:

- Why a particular building was selected.
- Why a dataset was considered representative.
- Why a synthetic variable was required.
- Why an hourly aggregation method was selected.
- Why a particular heat-pump COP model was used.
- Why a tariff or carbon-intensity series was selected.
- Why a particular reward function was adopted.

Each entry should include:

- Unique ID.
- Date.
- Decision or assumption.
- Context and rationale.
- Supporting evidence or references.
- Alternatives considered.
- Consequences and limitations.
- Status: proposed, accepted, rejected, or superseded.

Do not silently change an existing assumption. Record the change and its reason.

### 5.7 Experiment registry

Every simulation experiment must have a unique ID and a reproducible configuration.

Record:

- Experiment ID.
- Phase.
- Scenario and building configuration.
- Dataset versions and IDs.
- Model and algorithm IDs.
- Reward-function version.
- Simulation resolution and period.
- Random seeds.
- Software and dependency versions.
- Git commit.
- Execution date.
- Evaluation metrics.
- Output locations.
- Results and validation status.

A future reviewer should be able to reproduce an experiment without guessing which files, model parameters, or controller settings were used.

### 5.8 Software and environment reproducibility

Maintain:

- Dependency lockfiles.
- Python and CityLearn versions.
- Operating-system and relevant environment information.
- Configuration files.
- Git history.
- Reproducible execution instructions.
- Random seeds for stochastic experiments.

Avoid relying on undocumented local environment settings.

### 5.9 References and scientific traceability

Use primary sources wherever possible.

For models, algorithms, and scientific assumptions, retain:

- Publication title.
- Authors.
- Year.
- DOI or stable URL.
- Specific methodology or equation adopted.
- Any deviations from the original method.

Distinguish between a method implemented directly from a publication and a method adapted for this project.

### 5.10 Auditability acceptance criterion

A phase cannot be considered complete if its data sources, transformations, models, algorithms, assumptions, and experiments cannot be traced through the documentation.

A technically functioning simulation without an adequate paper trail is not an acceptable deliverable.

---

## 6. Phase A implementation specification

### 6.1 Objective

Create the first functioning Swiss district simulation using six representative residential buildings and hourly data.

### 6.2 Tasks

**Task A1 — Repository and framework inspection**

- Inspect the project repository and existing implementation.
- Verify the CityLearn 3.3.0 version.
- Review the framework's supported building, energy-system, storage, and controller interfaces.
- Identify existing functionality that can be reused.
- Document the proposed architecture and any required extensions.
- Establish the audit-documentation structure.

**Task A2 — Dataset verification and acquisition**

Investigate and acquire the approved publicly accessible datasets:

- HEAPO.
- ETH/EKZ smart-meter data.
- JASM / Empa CESAR.
- MeteoSwiss.
- ElCom tariffs.
- Swiss electricity carbon-intensity sources.

Investigate SFOE PV data for potential later use, but do not implement PV in Phase A unless explicitly necessary for a documented reason.

For every source, verify access, licence, data fields, temporal coverage, and suitability.

**Task A3 — Building selection**

Select six buildings or building representations that approximate a realistic Zurich-region residential district.

Prioritize a mixture of single-family and multi-family buildings.

For each building, document:

- Building type.
- Available building characteristics.
- Heating-system characteristics.
- Available electricity and thermal data.
- Data completeness.
- Representativeness.
- Any synthetic or modeled characteristics.

If individual datasets cannot be matched to the same physical building, do not imply that they can.

Instead, document the method used to construct each representative building and the degree of correspondence between its inputs.

**Task A4 — Data processing**

Create reproducible processing pipelines for:

- Data cleaning.
- Timestamp normalization.
- Timezone and daylight-saving handling.
- Hourly aggregation.
- Missing-data treatment.
- Unit conversion.
- Weather alignment.
- Building-level dataset construction.

Preserve original-resolution data.

Generate quality-control reports covering missingness, outliers, coverage, and physical plausibility.

**Task A5 — Heating and DHW model**

Implement a heating-focused building representation.

Include:

- Space-heating demand.
- Air-source heat-pump electricity consumption.
- Heat-pump efficiency or COP representation.
- DHW demand.
- Thermal storage where appropriate and supported.

Use measured data wherever possible.

Where thermal demand or heat-pump output is unavailable, use a documented archetype or physical model. Label all such outputs accordingly.

**Task A6 — Weather, tariffs, and carbon intensity**

- Integrate hourly MeteoSwiss weather.
- Select and document appropriate weather stations or spatial interpolation.
- Integrate a suitable Swiss 2026 electricity tariff.
- Integrate an appropriate electricity carbon-intensity series.
- Document tariff structure, units, temporal resolution, and emissions methodology.

If a suitable historical carbon-intensity dataset cannot be obtained, document the limitation and propose an approved alternative rather than inventing a time series.

**Task A7 — CityLearn integration**

- Build the six-building dataset and configuration.
- Integrate the heating, DHW, weather, and electricity inputs.
- Configure CityLearn 3.3.0.
- Implement necessary custom extensions without modifying the original framework wherever practical.
- Verify that the environment initializes and runs through the intended simulation period.

**Task A8 — Baseline controllers and reward function**

Use existing CityLearn controllers where appropriate.

Establish a transparent baseline comparison.

Review the reward function to ensure that its objective is appropriate for the Swiss heating scenario.

Document all state variables, actions, constraints, weights, and assumptions.

Do not introduce a complex custom RL algorithm unless it is required to demonstrate that the environment functions.

**Task A9 — Validation and evaluation**

Validate:

- Energy balance.
- Electricity consumption.
- Heat-pump operation.
- Heating and DHW demand.
- Seasonal patterns.
- Weather alignment.
- Tariff calculations.
- Carbon calculations.
- Simulation stability.

Where measured reference data exists, compare simulated and observed values.

Report metrics and limitations. Do not claim calibration or validation where only qualitative plausibility checks were performed.

### 6.3 Phase A acceptance criteria

Phase A is complete only when:

1. Six representative buildings are configured.
2. The CityLearn environment runs successfully at hourly resolution.
3. Heating, DHW, and heat-pump behavior are represented.
4. Weather data is integrated.
5. Electricity tariffs and carbon-intensity assumptions are documented and integrated where suitable data is available.
6. Energy accounting has been checked for double counting.
7. Baseline control strategies run successfully.
8. Data quality and model validation reports exist.
9. All data, models, transformations, assumptions, and experiments are registered.
10. The project can be reproduced using documented instructions.

If an input remains unavailable or unverified, the agent must report it as an unresolved limitation. It must not manufacture a successful acceptance result.

### 6.4 Phase A completion report

The agent must produce a report containing:

- Implemented functionality.
- Final building selection.
- Dataset inventory and provenance.
- Model and algorithm inventory.
- Data quality findings.
- Validation results.
- Known limitations.
- Outstanding issues.
- Repository changes.
- Reproduction instructions.
- Proposed modifications to Phases B and C.

The report must distinguish completed, partially completed, blocked, and deferred tasks.

---

## 7. Phase B implementation specification

**Phase B is not authorized until Phase A has been reviewed and approved.**

### 7.1 Objective

Extend the validated hourly baseline into a higher-resolution district energy system with distributed generation, storage, and local energy coordination.

### 7.2 Tasks

**Task B1 — Review Phase A**

- Inspect the Phase A completion report.
- Reassess the data architecture and model limitations.
- Identify changes required before increasing temporal resolution.
- Update the Phase B implementation proposal for approval.

**Task B2 — 15-minute data pipeline**

- Incorporate ETH/EKZ and HEAPO data at 15-minute resolution where available.
- Preserve original temporal resolution.
- Verify timestamp alignment and daylight-saving behavior.
- Ensure all datasets are synchronized correctly.
- Validate the relationship between household electricity, heat-pump electricity, and thermal demand.

**Task B3 — PV generation**

- Incorporate suitable Swiss PV data or documented generation models.
- Represent building-level PV generation.
- Document orientation, capacity, efficiency, and other assumptions.
- Validate generation profiles and units.

**Task B4 — Battery storage**

- Add battery storage to selected buildings or district configurations.
- Define capacity, charge/discharge limits, efficiencies, and state-of-charge constraints.
- Document all parameter sources.
- Validate energy conservation and operating constraints.

**Task B5 — Electricity tariffs and export remuneration**

- Extend tariff modeling to dynamic or time-varying tariffs where appropriate.
- Incorporate import and export pricing.
- Document applicable Swiss tariff and remuneration structures.
- Avoid applying tariffs or economic arrangements that do not apply to the modeled building or scenario.

**Task B6 — Local electricity sharing and LEG**

- Investigate the applicable Swiss legal and economic framework for local electricity communities.
- Model energy sharing and allocation rules only where supported by verified assumptions.
- Separate physical electricity flows from contractual or financial allocations.
- Document network charges, remuneration, and other economic assumptions.

**Task B7 — Building thermal model**

- Investigate the suitability of a calibrated resistance-capacitance (RC) model.
- Use available data to calibrate and validate thermal parameters.
- Document any parameters that cannot be directly measured.
- Compare the improved model against the Phase A representation.

**Task B8 — EV charging**

- Introduce EV charging only where appropriate data or documented scenario assumptions are available.
- Define charging demand, connection availability, and flexibility constraints.
- Keep EV assumptions separate from measured household loads.

**Task B9 — District objectives and evaluation**

Expand evaluation metrics to include:

- Peak grid import.
- Coincident district peak demand.
- PV self-consumption.
- Self-sufficiency.
- Battery utilization.
- Import and export costs.
- Energy sharing.
- Emissions.
- Operational flexibility.

Perform held-out validation where data availability permits.

### 7.3 Phase B acceptance criteria

1. The environment supports 15-minute resolution.
2. Higher-resolution data integration is reproducible.
3. PV generation is represented and validated.
4. Battery operation respects physical constraints.
5. Import and export accounting is correct.
6. Dynamic tariff calculations are documented.
7. LEG behavior is based on explicit and documented assumptions.
8. EV behavior is included only where justified.
9. The improved thermal model is evaluated against the earlier model.
10. District-level metrics are generated.
11. All new data, models, algorithms, and experiments are registered.
12. The Phase B implementation is reproducible.

### 7.4 Phase B completion report

Produce a report documenting:

- Changes to the Phase A architecture.
- New data sources.
- Temporal-resolution changes.
- PV and battery models.
- Tariff and LEG assumptions.
- EV implementation, if applicable.
- Thermal-model calibration.
- Validation and evaluation results.
- Remaining limitations.
- Updated Phase C proposal.

---

## 8. Phase C implementation specification

**Phase C is not authorized until Phase B has been reviewed and approved.**

### 8.1 Objective

Investigate how future climate conditions and increased cooling adoption affect Swiss residential energy demand, summer peak demand, and energy flexibility.

### 8.2 Tasks

**Task C1 — Review previous phases**

- Review Phase A and B completion reports.
- Verify that the existing heating and district-energy models are suitable for climate scenario analysis.
- Update the Phase C proposal before implementation.

**Task C2 — Climate scenarios**

- Establish a historical climate baseline.
- Investigate current CH2018 and/or CH2025 scenario resources.
- Select moderate and high warming scenarios.
- Document scenario periods, geographic applicability, and assumptions.
- Determine how scenario data can be represented at hourly resolution.

If source data is available only at daily or coarser resolution, document and validate the hourly disaggregation method.

**Task C3 — Cooling demand**

- Extend the building model to represent cooling.
- Investigate suitable Swiss building archetype cooling profiles.
- Define and document cooling-system assumptions.
- Account for building characteristics, weather, and cooling adoption.
- Distinguish modeled cooling demand from measured observations.

**Task C4 — Cooling adoption scenarios**

Define three cooling-adoption levels.

The exact penetration percentages should be proposed by the agent based on credible Swiss evidence and approved before implementation.

Represent different adoption levels across the six-building district.

**Task C5 — Heating and cooling integration**

- Represent mixed heating and cooling buildings.
- Preserve the existing heating functionality.
- Evaluate seasonal interactions between heating, cooling, and other electrical loads.
- Verify that cooling operation does not introduce inconsistent energy accounting.

**Task C6 — Scenario evaluation**

Compare:

- Historical climate baseline.
- Moderate warming.
- High warming.
- Three cooling-adoption levels.
- Heating-only district.
- Mixed heating and cooling district.

Evaluate:

- Seasonal electricity demand.
- Summer peak demand.
- Coincident district peaks.
- Heating and cooling energy consumption.
- Carbon emissions.
- Storage and renewable-energy interactions.
- Controller effectiveness under different scenarios.

**Task C7 — Transferability and robustness**

Investigate whether controllers developed for heating-focused scenarios continue to perform effectively when cooling is introduced.

Document differences in performance and any required controller adaptations.

### 8.3 Phase C acceptance criteria

1. Historical and future climate scenarios are represented.
2. Climate inputs and hourly processing are documented.
3. Cooling demand is modeled transparently.
4. Three cooling-adoption scenarios are implemented.
5. Heating-only and mixed-use districts can be compared.
6. Seasonal and peak-demand metrics are calculated.
7. Controller performance is compared across scenarios.
8. Climate and cooling assumptions are traceable.
9. Validation limitations are documented.
10. All experiments are reproducible.

### 8.4 Phase C completion report

Produce a final report documenting:

- Climate datasets and scenario selection.
- Cooling-adoption assumptions.
- Building cooling models.
- Changes to the CityLearn environment.
- Scenario configurations.
- Controller comparisons.
- Seasonal and peak-demand results.
- Model limitations.
- Scientific implications.
- Complete data, model, algorithm, and experiment provenance.

---

## 9. Agent execution protocol

This section governs how the implementation agent must work.

### 9.1 One-phase-at-a-time authorization

The agent receives the entire roadmap but may execute only the currently authorized phase.

Initial authorization:

**Phase A: Authorized.**

**Phase B: Not authorized.**

**Phase C: Not authorized.**

The agent must not begin implementation work for a later phase simply because it is described in this document.

It may identify dependencies and make recommendations for future phases, but must not implement them without approval.

### 9.2 Start-of-phase procedure

At the beginning of each authorized phase, the agent must:

1. Inspect the repository and current project state.
2. Read the project documentation and prior phase reports.
3. Verify the relevant datasets and dependencies.
4. Review outstanding issues and assumptions.
5. Identify conflicts between the implementation plan and actual findings.
6. Prepare a concise execution proposal if material changes are needed.
7. Confirm that the proposed work stays within the authorized phase.

Do not overwrite or discard existing work without understanding its purpose.

### 9.3 Implementation procedure

During execution:

- Work incrementally.
- Use version control.
- Make changes in logically separated commits where possible.
- Write tests for new functionality.
- Maintain data and model registries.
- Update documentation as decisions are made, not only at the end.
- Preserve original source data.
- Keep experimental outputs separate from source data.
- Record failures and unexpected findings.
- Do not conceal incomplete work behind synthetic substitutes.

### 9.4 Handling blockers

If the agent encounters a blocker, it must:

1. Describe the issue.
2. Identify the affected task and deliverable.
3. Explain its technical or scientific implications.
4. Identify possible solutions.
5. State which solutions require user approval.
6. Avoid making irreversible or high-impact assumptions.

Examples include inaccessible datasets, unclear licensing, incompatible data formats, missing variables, and unsupported CityLearn functionality.

### 9.5 End-of-phase procedure

At the end of each phase, the agent must:

1. Run the available tests.
2. Validate the implemented functionality.
3. Update all audit registries.
4. Produce the phase completion report.
5. Identify unresolved issues.
6. Propose updates to subsequent phases.
7. Provide a summary of repository changes.
8. Provide reproduction instructions.

The agent must then stop.

It must not automatically continue to the next phase.

### 9.6 Phase approval gate

The user reviews the completion report and proposed changes.

The next phase can begin only after explicit authorization.

The user may:

- Approve the next phase as proposed.
- Request changes to the implementation plan.
- Request further investigation.
- Defer or remove parts of the next phase.

The agent must use the approved, updated plan rather than assuming the original roadmap remains unchanged.

---

## 10. Global quality and testing requirements

The following requirements apply throughout the project.

### Data quality

- Check missingness and completeness.
- Detect implausible values and outliers.
- Verify units and conversion factors.
- Check timestamp alignment.
- Verify daylight-saving transitions.
- Check for duplicate observations.
- Document interpolation and aggregation.
- Maintain provenance through all derived datasets.

### Physical consistency

- Check energy balances.
- Verify heating and cooling loads.
- Check heat-pump performance assumptions.
- Verify storage charge/discharge constraints.
- Avoid double counting.
- Check import/export accounting.
- Verify emissions calculations.

### Software quality

- Maintain modular code.
- Avoid unnecessary modifications to CityLearn.
- Add automated tests for custom modules.
- Use consistent configuration files.
- Maintain dependency versions.
- Provide reproducible execution instructions.
- Ensure new functionality does not silently break previous phases.

### Scientific quality

- Distinguish calibration from validation.
- Use held-out data where possible.
- Report uncertainty and limitations.
- Document model assumptions.
- Compare results against suitable references.
- Avoid claims unsupported by the available data.

---

## 11. Final project deliverables

At completion, the repository should contain:

1. A reproducible CityLearn 3.3.0 Swiss district simulation.
2. Six documented representative residential buildings.
3. A structured data acquisition and processing pipeline.
4. Documented building, heat-pump, and energy-system models.
5. Baseline and subsequent control algorithms.
6. Reproducible experiment configurations.
7. Automated tests and validation reports.
8. Complete data-source and transformation provenance.
9. Model, algorithm, and parameter registries.
10. Decision and assumption logs.
11. Phase completion reports.
12. A final scientific and technical report.

## 12. Definition of success

The project is successful when it provides a functioning and scientifically defensible Swiss residential district simulation that can support reproducible energy-system and reinforcement-learning experiments.

Equally important, it must be possible for a future researcher to answer:

- Which original datasets were used?
- What were their licences and access conditions?
- Which observations correspond to each simulated building?
- Which values were measured, derived, modeled, or synthetic?
- How were the original datasets transformed?
- Which building and energy-system models were used?
- Which parameters and assumptions were selected, and why?
- Which algorithms and reward functions were evaluated?
- Which software versions and configurations produced a result?
- Can the experiment be reproduced?

If these questions cannot be answered from the project repository and its documentation, the implementation is not considered complete.

---

**Initial execution instruction:** Begin with Phase A only. Inspect the repository, verify CityLearn 3.3.0, establish the audit trail, and assess the approved data sources. Do not begin Phase B or Phase C. At the end of Phase A, stop and submit the completion report and revised roadmap for approval.
