"""B5: assumed export (feed-in) price for the PV scenarios (D-034).

No source with a producer remuneration series was usable: the EKZ file has consumption prices only, the ElCom cubes hold consumer
tariffs only (the field `aidfee` is the 2.3 Rp/kWh consumer surcharge, EL-0056), and the SFOE reference market price was not
downloaded (licence and format unconfirmed, EL-0057; the owner chose an assumed sweep). The export price is therefore a labelled
ASSUMPTION: a constant price in Rp/kWh excluding VAT, swept over EXPORT_SWEEP_RP, default DEFAULT_EXPORT_RP. The zero value is the
what-if "exports earn nothing", which is also what CityLearn 3.3.0 does internally (cost = max(net, 0) * price).
The reported range of recent SFOE quarterly reference prices (about 5.7 to 9.5 Rp/kWh for Q3 and Q4 2025, from a web search summary,
unverified) only motivated the default of 8; it is not a data source.
"""
import numpy as np

EXPORT_SWEEP_RP = (0.0, 4.0, 8.0, 12.0)
DEFAULT_EXPORT_RP = 8.0


def export_price_chf_per_kwh(n_steps, rp_per_kwh=DEFAULT_EXPORT_RP):
    """Constant export price series in CHF/kWh (separate from the import price series)."""
    return np.full(int(n_steps), float(rp_per_kwh) / 100.0)
