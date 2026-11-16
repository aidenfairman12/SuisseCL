# Controller documentation

State/action interface (stock CityLearn, central agent): 25 observations (hour, day_type, outdoor temperature, electricity pricing and predicted 1-3, per-building net consumption, heating/DHW storage SOC); 12 action slots = heating_storage and dhw_storage per building (continuous in [-1, 1]; positive = charge the tank, negative = discharge, as fractions of tank capacity; limited by tank capacity, loss coefficient and heat-pump nominal power). SFH-low has no DHW tank (action slot present but inactive; to be verified).
Constraints: tank capacity (synthetic, D-017a), heat-pump nominal power = 1.1 × peak measured electricity, heating and DHW demand always met (no unmet-demand mechanism).
See `algorithm_registry.md` for each controller. Assumptions: weather forecasts are not observed; price forecasts are exact because the tariff is deterministic.
