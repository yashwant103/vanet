"""
VANET Bridge – TraCI Manager
=============================
Extracts real-time metrics from a running SUMO simulation via TraCI.
Falls back to synthetic estimates when SUMO is unavailable.
"""

import math
import random

# Try importing TraCI; mark as unavailable if not installed
try:
    import traci
    TRACI_AVAILABLE = True
except ImportError:
    TRACI_AVAILABLE = False


COMM_RANGE_M = 300.0   # IEEE 802.11p standard communication range


def fetch_edge_metrics(edge_id: str) -> dict:
    """
    Real-time per-edge metrics from SUMO via TraCI.

    Returns:
        dict with keys: edge, density, stability, mean_speed,
                        vehicle_count, road_length_m
    """
    if not TRACI_AVAILABLE:
        raise RuntimeError("TraCI not available. Install sumo-tools.")

    num_vehicles = traci.edge.getLastStepVehicleNumber(edge_id)
    road_length  = traci.lane.getLength(edge_id + "_0")
    mean_speed   = traci.edge.getLastStepMeanSpeed(edge_id)

    # Traffic Density: vehicles per metre
    density = num_vehicles / road_length if road_length > 0 else 0

    # Link Stability: COMM_RANGE / relative speed (higher = more stable)
    stability = COMM_RANGE_M / (mean_speed + 0.5)
    stability = min(stability, 1.0)   # normalise to [0, 1]

    return {
        "edge":          edge_id,
        "vehicle_count": num_vehicles,
        "road_length_m": road_length,
        "density":       round(density,   5),
        "stability":     round(stability, 4),
        "mean_speed":    round(mean_speed, 2),
    }


def fetch_all_vehicle_metrics() -> dict:
    """
    Aggregate metrics across ALL vehicles currently in the simulation.

    Returns:
        dict with keys: count, avg_speed, avg_delay, avg_jitter,
                        pdr_estimate, throughput_mbps, congestion_index
    """
    if not TRACI_AVAILABLE:
        raise RuntimeError("TraCI not available.")

    vehicle_ids = traci.vehicle.getIDList()
    count = len(vehicle_ids)
    if count == 0:
        return {"count": 0}

    speeds        = [traci.vehicle.getSpeed(v)        for v in vehicle_ids]
    wait_times    = [traci.vehicle.getWaitingTime(v)   for v in vehicle_ids]
    travel_times  = [traci.vehicle.getTraveltime(v)    for v in vehicle_ids]

    avg_speed  = sum(speeds)       / count
    avg_wait   = sum(wait_times)   / count
    avg_travel = sum(travel_times) / count

    # Derived network metrics
    stability  = max(0.35, 1.0 - avg_speed / 40.0)
    pdr        = min(0.99, 0.80 + stability * 0.19)
    delay_s    = max(0.005, 0.08 - stability * 0.04)
    throughput = (count * pdr * 512 * 8 * 10) / 1e6   # Mbps

    # Congestion: fraction of vehicles with wait_time > 10 s
    congestion_index = sum(1 for w in wait_times if w > 10) / count

    return {
        "count":             count,
        "avg_speed_ms":      round(avg_speed,  2),
        "avg_wait_s":        round(avg_wait,   2),
        "avg_travel_s":      round(avg_travel, 2),
        "stability":         round(stability,  4),
        "pdr_estimate":      round(pdr,        4),
        "delay_s":           round(delay_s,    5),
        "throughput_mbps":   round(throughput, 4),
        "congestion_index":  round(congestion_index, 4),
    }


def synthetic_metrics(density: int, step: int) -> dict:
    """
    Generates synthetic but realistic metrics when SUMO is unavailable.
    Used for dashboard demo mode.
    """
    avg_speed  = max(1.0, random.gauss(15 - density * 0.08, 2))
    stability  = max(0.35, 1.0 - avg_speed / 40.0)
    pdr        = min(0.99, 0.82 + stability * 0.17 + random.gauss(0, 0.01))
    delay_s    = max(0.005, 0.07 - stability * 0.035 + random.gauss(0, 0.003))
    throughput = (density * pdr * 512 * 8 * 10) / 1e6

    return {
        "count":             density,
        "avg_speed_ms":      round(avg_speed,  2),
        "stability":         round(stability,  4),
        "pdr_estimate":      round(pdr,        4),
        "delay_s":           round(delay_s,    5),
        "throughput_mbps":   round(throughput, 4),
        "congestion_index":  round(min(0.95, density / 120.0), 4),
    }
