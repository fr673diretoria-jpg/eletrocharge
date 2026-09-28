"""Cálculos de geolocalização compartilhados entre routers."""
from math import atan2, cos, radians, sin, sqrt


def calcular_distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em linha reta entre duas coordenadas (fórmula de Haversine)."""
    raio_terra = 6371
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return raio_terra * c
