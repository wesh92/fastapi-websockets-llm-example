import httpx
import timeit

from .weather_model import WeatherAlertResponse, IncomingWeatherAlertQuery, QueryMetrics

async def fetch_weather_alerts(
    request_object: IncomingWeatherAlertQuery,
) -> WeatherAlertResponse:
    """
    Fetch weather alerts from the National Weather Service API.
    """
    # Define the base URL for the NWS API
    base_url = "https://api.weather.gov/alerts/active"
    
    # Define the query parameters
    params = {"area": request_object.state}
    
    # Make an HTTP request to the NWS API
    time_start = timeit.default_timer()
    async with httpx.AsyncClient() as client:
        response = await client.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
    
    # Extract the alert properties and metrics
    alerts = data["features"]
    time_end = timeit.default_timer()
    metrics = QueryMetrics(
        query_time_ms=round((time_end - time_start) * 100),
        total_records=len(alerts),
    )
    
    return WeatherAlertResponse(features=alerts, query_metrics=metrics)