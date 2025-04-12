import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class MicroGrid:
    def __init__(self, load_df: pd.DataFrame, pv_price_df: pd.DataFrame):
        """
        Initialize the microgrid system with load and PV/price data.
        """
        self.load_df = load_df.copy()
        self.pv_price_df = pv_price_df.copy()
        
        # Create aligned time index
        self.time_index = pd.date_range(start="2024-08-26", periods=168, freq="H")
        self.load_df.index = pd.date_range(start="2024-08-19", periods=168, freq="H")
        self.pv_price_df.index = self.time_index
        
        # Microgrid parameters
        self.flexibility = 0.15
        self.battery_capacity = 2000  # in kWh
        self.battery_power = 1000     # max charge/discharge power in kW
        self.battery_soc = 0          # starting state of charge in kWh
        self.eta_ch = 0.95
        self.eta_dis = 0.95
        
        # Generate EV charging schedule
        self.ev_schedule = self._generate_ev_schedule()

        # To store energy usage logs
        self.energy_usage_log = []

    def _generate_ev_schedule(self):
        """
        Generate a time series with EV charging energy required per hour.
        """
        schedule = pd.Series(0, index=self.time_index)
        for day in pd.date_range("2024-08-26", "2024-09-01"):
            for hour in range(16, 20):  # 4 EVs × 50 kWh
                schedule[day + timedelta(hours=hour)] += 50
            for hour in range(15, 21):  # 2 EVs × 100 kWh
                schedule[day + timedelta(hours=hour)] += 50
        return schedule

    def get_energy_usage(self, t: datetime) -> dict:
        """
        Calculate energy use at time t, including load, EVs, PV, battery, and grid.
        """
        # Baseline and flexible load
        base_load = self.load_df.loc[t - timedelta(days=7)]["Load (kW)"]
        flexible_load = base_load * (1 + np.random.uniform(-self.flexibility, self.flexibility))
        
        # EV demand at this hour
        ev_demand = self.ev_schedule.loc[t]
        total_demand = flexible_load + ev_demand

        # PV supply
        pv_supply = self.pv_price_df.loc[t]["PV_3MW_generation (kWh)"]

        # Battery discharge
        battery_dis = min(total_demand, self.battery_power, self.battery_soc * self.eta_dis)
        self.battery_soc -= battery_dis / self.eta_dis

        # Grid import (if any)
        residual_demand = total_demand - pv_supply - battery_dis
        grid_import = max(residual_demand, 0)

        # PV curtailment and battery charging (optional)
        curtailed_pv = max(pv_supply - total_demand, 0)
        battery_ch = min(pv_supply - battery_dis, self.battery_power, 
                         (self.battery_capacity - self.battery_soc) / self.eta_ch)
        if curtailed_pv > 0:
            battery_ch = min(curtailed_pv, battery_ch)
            self.battery_soc += battery_ch * self.eta_ch

        # Log and return
        result = {
            "time": t,
            "flexible_load": flexible_load,
            "ev_demand": ev_demand,
            "pv_supply": pv_supply,
            "battery_discharge": battery_dis,
            "battery_charge": battery_ch,
            "battery_soc": self.battery_soc,
            "grid_import": grid_import,
            "curtailed_pv": curtailed_pv
        }
        self.energy_usage_log.append(result)
        return result
