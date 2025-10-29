from fastapi import APIRouter
from app.services import CountryService
from app.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, status, HTTPException
from app.schemas import RefreshResponse, ErrorResponse, CountryResponse, StatusResponse, CountryListResponse
from typing import Optional
from fastapi.responses import FileResponse
from pathlib import Path


router = APIRouter()
service = CountryService()


# ============================================================================
# POST /countries/refresh - Refresh all countries from external APIs
# ============================================================================

@router("/countries/refresh", response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
    methods=["GET","POST"],
    responses={
        503: {
            "model": ErrorResponse,
            "description": "External API unavailable"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    } )
async def refresh_countries(session: AsyncSession = Depends(get_session)):

    try:
        total, timestamp = await service.refresh_all_countries(session)
        return RefreshResponse(
            message="Countries data refreshed successfully",
            total_countries=total,
            last_refreshed_at=timestamp
        )
    except Exception as e:
        error_msg = str(e)

         # ADD THIS LINE TO SEE THE REAL ERROR
        print(f"❌ ERROR in refresh_countries: {error_msg}")
        import traceback
        traceback.print_exc()

        # Determine which API failed based on error message
        api_name = "external API"
        if "restcountries" in error_msg.lower():
            api_name = "restcountries API"
        elif "exchange rate" in error_msg.lower() or "er-api" in error_msg.lower():
            api_name = "exchange rate API"

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "External data source unavailable",
                "details": f"Could not fetch data from {api_name}",
            },
        )


# ============================================================================
# GET /countries - Get all countries with optional filters and sorting
# ============================================================================

@router.get("/countries", response_model=CountryListResponse, responses={
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    })
async def get_countries( region: Optional[str] = None,
    currency: Optional[str] = None,
    sort: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):

    try:
        countries = await service.get_countries_with_filters(session, region, currency, sort)
        return CountryListResponse(
            data=[CountryResponse.model_validate(c) for c in countries],
            count=len(countries),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


# ============================================================================
# GET /countries/image - Serve summary image
# ============================================================================


@router.get(
    "/countries/image",
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "Summary image with top countries",
        },
        404: {"model": ErrorResponse, "description": "Image not found"},
    },
)
async def get_summary_image():

    image_path = Path("cache/summary.png")

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Summary image not found"},
        )

    return FileResponse(path=image_path, media_type="image/png", filename="summary.png")


# ============================================================================
# GET /countries/:name - Get a single country by name
# ============================================================================

@router.get("/countries/{name}", response_model=CountryResponse,  status_code=status.HTTP_200_OK,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Country not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def get_country_by_name(name: str, session: AsyncSession = Depends(get_session)):
    try:
        country = await service.get_country_by_name(session, name)
        if not country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Country not found"},
            )
        return CountryResponse.model_validate(country)

    except HTTPException:
        # Re-raise HTTP exceptions (404)
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


# ============================================================================
# DELETE /countries/:name - Delete a country by name
# ============================================================================

@router.delete(
    "/countries/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Country not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def delete_country(
    name: str,
    session: AsyncSession = Depends(get_session),
):

    try:
        deleted = await service.delete_country_by_name(session, name)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Country not found"},
            )
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )


# ============================================================================
# GET /status - Get system status
# ============================================================================

@router.get(
    "/status",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    responses={
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def get_status(session: AsyncSession = Depends(get_session)):

    try:
        # Get total countries
        total = await service.get_total_countries(session)

        # Get last refresh timestamp from metadata
        metadata = await service.get_app_metadata(session)
        last_refreshed = metadata.last_refreshed_at if metadata else None

        return StatusResponse(total_countries=total, last_refreshed_at=last_refreshed)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error"},
        )
