"""
Pydantic schemas for API request/response validation.
Separates API layer from database models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CountryResponse(BaseModel):
    """
    Response schema for country data.
    Used in GET /countries and GET /countries/:name
    """

    id: int
    name: str
    capital: Optional[str] = None
    region: Optional[str] = None
    population: int
    currency_code: Optional[str] = None
    exchange_rate: Optional[float] = None
    estimated_gdp: Optional[float] = None
    flag_url: Optional[str] = None
    last_refreshed_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Enables Country.from_orm(db_model)
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Nigeria",
                "capital": "Abuja",
                "region": "Africa",
                "population": 206139589,
                "currency_code": "NGN",
                "exchange_rate": 1600.23,
                "estimated_gdp": 25767448125.2,
                "flag_url": "https://flagcdn.com/ng.svg",
                "last_refreshed_at": "2025-10-22T18:00:00Z",
            }
        }


class CountryListResponse(BaseModel):
    """
    Response schema for list of countries.
    Used in GET /countries with filters
    """

    data: List[CountryResponse]
    count: int

    class Config:
        json_schema_extra = {
            "example": {
                "data": [
                    {
                        "id": 1,
                        "name": "Nigeria",
                        "capital": "Abuja",
                        "region": "Africa",
                        "population": 206139589,
                        "currency_code": "NGN",
                        "exchange_rate": 1600.23,
                        "estimated_gdp": 25767448125.2,
                        "flag_url": "https://flagcdn.com/ng.svg",
                        "last_refreshed_at": "2025-10-22T18:00:00Z",
                    }
                ],
                "count": 1,
            }
        }


class RefreshResponse(BaseModel):
    """
    Response after refreshing country data.
    Used in POST /countries/refresh
    """

    message: str
    total_countries: int
    last_refreshed_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Countries data refreshed successfully",
                "total_countries": 250,
                "last_refreshed_at": "2025-10-22T18:00:00Z",
            }
        }


class StatusResponse(BaseModel):
    """
    System status response.
    Used in GET /status
    """

    total_countries: int
    last_refreshed_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "total_countries": 250,
                "last_refreshed_at": "2025-10-22T18:00:00Z",
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response for all error cases.
    Used in 404, 500, 503 responses
    """

    error: str
    details: Optional[str] = None

    class Config:
        json_schema_extra = {"example": {"error": "Country not found", "details": None}}


class ValidationErrorResponse(BaseModel):
    """
    Validation error response.
    Used in 400 Bad Request
    """

    error: str = "Validation failed"
    details: dict

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Validation failed",
                "details": {"currency_code": "is required"},
            }
        }
