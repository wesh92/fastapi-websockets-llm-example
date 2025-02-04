from logging import INFO, getLogger
from typing import Annotated

from documentation.docs import API_VERSION, FEATURE_OR_CODENAME

from fastapi import APIRouter, HTTPException, Request, Response, Security

from internal.auth.auth_service import get_current_user
from internal.auth.auth_model import User
from .weather_service import fetch_weather_alerts
from .weather_model import IncomingWeatherAlertQuery, WeatherAlertResponse

logger = getLogger("gunicorn.error")
logger.setLevel(INFO)

ENDPOINT_ACTIVE = True

if ENDPOINT_ACTIVE is False:
    pass
else:
    router = APIRouter()

    # Post is obviously the wrong method here, but just as an example. GETs are easy.
    @router.post(
        "/weatherAlerts",
        response_model=WeatherAlertResponse,
        summary="Fetch weather alerts from the National Weather Service API.",
        response_description="Weather alerts fetched successfully.",
    )
    async def weather_alerts(
        request: Request,
        request_object: IncomingWeatherAlertQuery,
        response: Response,
        current_user: Annotated[User, Security(get_current_user, scopes=["weather"])],
    ):
        """
        Fetch weather alerts from the National Weather Service API.
        """
        response.headers["API-Version"] = f"{API_VERSION} - {FEATURE_OR_CODENAME}"
        try:
            weather_alerts = await fetch_weather_alerts(request_object)
            if not weather_alerts:
                raise HTTPException(
                    status_code=204,
                    detail="Request successful, but no weather alerts found.",
                )
            return weather_alerts
        except Exception as e:
            logger.error(f"Failed to fetch weather alerts: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to fetch weather alerts."
            )
