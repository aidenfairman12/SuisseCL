# Prompt: research how to adapt a CityLearn RL project to Swiss data

Copy everything below the line into a fresh agent. It assumes no prior context.

---

## Your role
You are a research assistant. Produce a well-sourced written report (a single Markdown document) on how to adapt an existing building-energy reinforcement-learning project to **Swiss** data and conditions. Do **research and planning only**. Do not write or modify project code, do not download large datasets, and do not sign up for services. If something needs access, credentials or a download, list it as a recommendation instead.

## Project background (what exists today)
- **CityLearn** (https://github.com/citylearn-project/CityLearn, version 3.3.0) is an open-source Gymnasium simulator for coordinating the energy use of a district of buildings. It simulates hourly electricity demand, PV generation, batteries, thermal storage and heat pumps / cooling devices, and reports KPIs (cost, carbon, peak demand, ramping, load factor, thermal discomfort, unmet demand during outages).
- The project trains and compares controllers on the **CityLearn Challenge 2023** dataset (`citylearn_challenge_2023_phase_3_1`): 6 US-style residential buildings, hourly, about 3 months (2,208 steps). That data is **cooling-driven** (hvac_mode = cooling), uses a flat electricity price, and uses a carbon-intensity series typical of a fossil-heavy grid. Controllers compared: do-nothing, rule-based, SAC (central and per-building), and MARLISA (multi-agent SAC). A composite reward balances comfort, electricity cost, carbon, peak demand and ramping.
- **Goal:** transfer this pipeline to realistic **Swiss** data and see whether the methods carry over. Brainstormed ideas include heat-pump-dominated heating, Swiss tariffs, a low-carbon grid, and a future scenario with air-conditioning uptake as Swiss summers get hotter.

## What a CityLearn dataset needs (so you know what to look for)
One folder containing:
- `schema.json`: building list, device definitions (e.g. `heating_device` / `cooling_device` heat pumps with nominal power and efficiency, `dhw_device`, `dhw_storage`, `electrical_storage` battery with capacity and power, `pv` with nominal power), which observations and actions are active.
- One CSV per building (hourly). Columns used in the 2023 data include: `month, hour, day_type, daylight_savings_status, indoor_dry_bulb_temperature, indoor_relative_humidity, non_shiftable_load, dhw_demand, cooling_demand, heating_demand, solar_generation, occupant_count, indoor_dry_bulb_temperature_cooling_set_point, indoor_dry_bulb_temperature_heating_set_point, hvac_mode`.
- `weather.csv`: outdoor dry-bulb temperature, relative humidity, diffuse and direct solar irradiance, each with 1/2/3-hour-ahead predicted columns.
- `pricing.csv`: `electricity_pricing` plus 1/2/3-hour-ahead predictions.
- `carbon_intensity.csv`: one `carbon_intensity` column.
- For some building types, a pre-trained LSTM thermal-dynamics model (`.pth`) per building to simulate indoor temperature.

## Research questions
Answer each one, cite sources, and say plainly where evidence is weak or missing.

1. **Building and load data.** What openly available Swiss datasets could supply hourly (or finer) household / small-building electricity load, heat-pump electricity use, space-heating and domestic-hot-water demand, and indoor temperature? Consider smart-meter studies, research datasets (e.g. from ETH, EPFL, Empa, PSI, SFOE-funded projects), and synthetic or archetype generators. For each: size, time span, resolution, licence and access route, privacy limits, and how well it maps to the CityLearn CSV columns above.
2. **PV generation.** Swiss sources for PV production or irradiance-based modelling (e.g. MeteoSwiss, SFOE, public PV datasets). Typical residential PV sizes in Switzerland.
3. **Weather.** Where to get hourly Swiss weather (temperature, humidity, direct and diffuse irradiance) plus forecasts. Which stations or grid products, licences, and how to build the 1/2/3-hour "predicted" columns honestly.
4. **Electricity tariffs.** How Swiss household tariffs actually work: high/low-tariff periods, dynamic or time-of-use options, grid-usage and peak-power charges, and feed-in remuneration for PV. Where regulated tariff data is published (e.g. ElCom). Pick two or three representative tariff structures that could be turned into an `electricity_pricing` series, and explain what a battery or heat-pump controller could exploit in each.
5. **Carbon intensity.** Hourly or average carbon intensity of Swiss supply, including imports and the difference between production-based and consumption-based figures. How much does it vary over a day? Is it informative enough to be worth a reward weight, or should the reward emphasise something else (for example peak power or self-consumption)?
6. **Heat pumps and thermal modelling.** How Swiss heat pumps (air-source and ground-source) differ from the cooling devices in the US dataset. What determines COP versus outdoor temperature, and what simple, defensible models exist (for example COP curves). Which building thermal models could replace the pre-trained LSTM (RC-network models, archetype building stock models for Switzerland). Does CityLearn 3.3.0 support a heating-only heat-pump building cleanly, and what would need to change in a schema? (Check the CityLearn docs and source on GitHub.)
7. **Future-climate and air-conditioning scenario.** Credible Swiss climate-scenario data for hotter summers (e.g. the CH2018 climate scenarios and any hourly downscaled series). Current and projected residential A/C uptake in Switzerland, and how to represent it (cooling device on top of a heating-dominated building). What grid effects have been studied?
8. **Swiss-specific features worth modelling.** For example renewable energy communities (local sharing of PV between neighbours, now possible under Swiss law), EV charging, district heating, ground-source storage, and seasonal mismatch between PV and heating demand. Rank them by value and by how hard they are to add to CityLearn.
9. **Validation and pitfalls.** The risk of training on simulated or synthetic loads and deploying on real ones. How others validate building-control RL against real Swiss data, and which metrics matter to Swiss utilities and building owners.
10. **Recommended plan.** A phased plan: (a) minimum viable Swiss dataset in CityLearn format, (b) richer version, (c) future-climate scenario. For each phase: data sources chosen, effort estimate (days), main risks, and what to ask the project owner to decide.

## How to work
- Prefer primary sources: official data portals, peer-reviewed papers, regulator and utility documents, and project repositories. Give a link for every factual claim.
- Mark each claim as **verified** (you read the source), **reported** (a secondary source says so) or **unverified**.
- Do not invent dataset names, URLs, column names or tariff figures. If you cannot find something, say so.
- Keep licence and privacy constraints visible. Flag anything that would need a data-sharing agreement.

## Deliverable format
One Markdown report with: (1) a one-page executive summary and recommendation, (2) a table of candidate data sources (source, content, resolution, span, licence/access, fit to CityLearn columns), (3) a section per research question, (4) the phased plan, (5) a list of open decisions for the project owner, (6) references.
