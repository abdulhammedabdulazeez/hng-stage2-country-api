import httpx
from typing import List, Dict, Optional, Tuple
import random
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Country, AppMetadata
from sqlalchemy import select, func
from datetime import datetime, UTC
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


class CountryService:

    # ============================================================================
    # EXTERNAL API FUNCTIONS
    # ============================================================================

    async def fetch_countries_data(self) -> List[Dict]:
        """
        Fetch country data from restcountries API.

        Returns:
            List of country dictionaries

        Raises:
            Exception: If API call fails or times out
        """
        url = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException:
                raise Exception("Timeout while fetching countries data")
            except httpx.HTTPError as e:
                raise Exception(f"Could not fetch data from restcountries API - {str(e)}")

    async def fetch_exchange_rate(self) -> Dict[str, float]:
        """
        Fetch exchange rates from exchange rate API.

        Returns:
            Dictionary mapping currency codes to rates (e.g., {"NGN": 1600.23, "USD": 1.0})

        Raises:
            Exception: If API call fails or times out
        """
        url = f"https://open.er-api.com/v6/latest/USD"

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return data.get("rates", {})
            except httpx.TimeoutException:
                raise Exception("Timeout while fetching exchange rate")
            except httpx.HTTPError as e:
                raise Exception(f"Could not fetch data from open.er-api API - {str(e)}")

    # ============================================================================
    # BUSINESS LOGIC FUNCTIONS
    # ============================================================================

    def extract_currency_code(self, currencies: List[Dict]) -> Optional[str]:
        """
        Extract first currency code from currencies array.

        Args:
            currencies: List of currency dictionaries from API

        Returns:
            Currency code (e.g., "NGN") or None if empty
        """
        if not currencies:
            return None

        first_currency = currencies[0]
        return first_currency.get("code")

    def calculate_estimated_gdp(self, population: int, exchange_rate: float) -> float:
        """
        Calculate estimated GDP using formula:
        estimated_gdp = population × random(1000–2000) ÷ exchange_rate

        Args:
            population: Country population
            exchange_rate: Exchange rate against USD

        Returns:
            Estimated GDP or None if exchange_rate is None/0
        """

        if exchange_rate is None or exchange_rate == 0:
            return None

        random_multiplier = random.uniform(1000, 2000)
        return (population * random_multiplier) / exchange_rate

    async def upsert_country(self, session: AsyncSession, country_data: Dict, exchange_rates: Dict[str, float]) -> Country:
        """
        Insert new country or update existing one (case-insensitive name match).

        Args:
            session: Database session
            country_data: Country data from external API
            exchange_rates: Dictionary of exchange rates

        Returns:
            Created or updated Country object
        """
        # Extract currency code
        currency_code = self.extract_currency_code(country_data.get("currencies", []))

        # Get exchange rate if currency exists
        exchange_rate = None
        if currency_code:
            exchange_rate = exchange_rates.get(currency_code)

        # Calculate GDP
        population = country_data.get("population", 0)
        estimated_gdp = self.calculate_estimated_gdp(population, exchange_rate)

        # Check if country exists (case-insensitive name match)
        name = country_data.get("name")
        stmt = select(Country).where(func.lower(Country.name) == func.lower(name))
        result = await session.execute(stmt)
        existing_country = result.scalar_one_or_none()

        if existing_country:
            # UPDATE existing country with fresh random multiplier
            existing_country.capital = country_data.get("capital")
            existing_country.region = country_data.get("region")
            existing_country.population = population
            existing_country.currency_code = currency_code
            existing_country.exchange_rate = exchange_rate
            existing_country.estimated_gdp = estimated_gdp if estimated_gdp is not None else 0
            existing_country.flag_url = country_data.get("flag")
            existing_country.last_refreshed_at = datetime.now(UTC)
            return existing_country
        else:
            # INSERT new country
            new_country = Country(
                name=name,
                capital=country_data.get("capital"),
                region=country_data.get("region"),
                population=population,
                currency_code=currency_code,
                exchange_rate=exchange_rate,
                estimated_gdp=estimated_gdp if estimated_gdp is not None else 0,
                flag_url=country_data.get("flag"),
                last_refreshed_at=datetime.now(UTC)
            )
            session.add(new_country)
            return new_country

    async def refresh_all_countries(self, session: AsyncSession) -> Tuple[int, datetime]:
        """
        Fetch and refresh all country data from external APIs.

        Args:
            session: Database session

        Returns:
            Tuple of (total_countries, last_refreshed_at)

        Raises:
            Exception: If external APIs fail
        """

        # Fetch data from external APIs
        countries_data = await self.fetch_countries_data()
        exchange_rates = await self.fetch_exchange_rate()

        # Process each country
        for country_data in countries_data:
            await self.upsert_country(session, country_data, exchange_rates)

        # Update global metadata
        refresh_time = datetime.now(UTC)
        await self.update_app_metadata(session, refresh_time)

        # Commit all changes
        await session.commit()

        # Get top 5 for image generation
        top_countries = await self.get_top_countries_by_gdp(session, limit=5)

        # Generate summary image
        try:
            self.generate_summary_image(
                total_countries=len(countries_data),
                top_countries=top_countries,
                last_refreshed=refresh_time
            )
        except Exception as img_error:
            print(f"Warning: Failed to generate image: {img_error}")
            # Continue anyway - image generation is not critical

        return len(countries_data), refresh_time

    async def update_app_metadata(self, session: AsyncSession, refresh_time: datetime) -> None:
        """
        Update or create app metadata with last refresh timestamp.

        Args:
            session: Database session
            refresh_time: Timestamp of refresh
        """
        stmt = select(AppMetadata).where(AppMetadata.id == 1)
        result = await session.execute(stmt)
        metadata = result.scalar_one_or_none()

        if metadata:
            metadata.last_refreshed_at = refresh_time
        else:
            metadata = AppMetadata(id=1, last_refreshed_at=refresh_time)
            session.add(metadata)

    # ============================================================================
    # QUERY FUNCTIONS
    # ============================================================================

    async def get_countries_with_filters(self, session: AsyncSession, region: Optional[str] = None, currency: Optional[str] = None, sort: Optional[str] = None) -> List[Country]:
        """
        Get countries with optional filters and sorting.

        Args:
            session: Database session
            region: Filter by region (case-insensitive)
            currency: Filter by currency_code (case-insensitive)
            sort: Sort order (gdp_asc, gdp_desc, population_asc, population_desc)

        Returns:
            List of Country objects
        """
        # Build query
        stmt = select(Country)

        # Apply filters
        if region:
            stmt = stmt.where(func.lower(Country.region) == func.lower(region))

        if currency:
            stmt = stmt.where(func.lower(Country.currency_code) == func.lower(currency))

        # Apply sorting
        if sort == "gdp_desc":
            stmt = stmt.order_by(Country.estimated_gdp.desc())
        elif sort == "gdp_asc":
            stmt = stmt.order_by(Country.estimated_gdp.asc())
        elif sort == "population_desc":
            stmt = stmt.order_by(Country.population.desc())
        elif sort == "population_asc":
            stmt = stmt.order_by(Country.population.asc())

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_country_by_name(self, session: AsyncSession, name: str) -> Optional[Country]:
        """
        Get a single country by name (case-insensitive).

        Args:
            session: Database session
            name: Country name

        Returns:
            Country object or None if not found
        """
        stmt = select(Country).where(func.lower(Country.name) == func.lower(name))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_country_by_name(self, session: AsyncSession, name: str) -> bool:
        """
        Delete a country by name (case-insensitive).

        Args:
            session: Database session
            name: Country name

        Returns:
            True if deleted, False if not found
        """
        country = await self.get_country_by_name(session, name)
        if country:
            await session.delete(country)
            await session.commit()
            return True
        return False

    async def get_top_countries_by_gdp(self,session: AsyncSession, limit: int = 5) -> List[Country]:
        """
        Get top N countries by estimated GDP.

        Args:
            session: Database session
            limit: Number of countries to return

        Returns:
            List of top countries
        """
        stmt = select(Country).order_by(Country.estimated_gdp.desc()).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_countries(self, session: AsyncSession) -> int:
        """
        Get total count of countries in database.

        Args:
            session: Database session

        Returns:
            Total count
        """
        stmt = select(func.count(Country.id))
        result = await session.execute(stmt)
        return result.scalar_one()

    async def get_app_metadata(self, session: AsyncSession) -> Optional[AppMetadata]:
        """
        Get app metadata containing last refresh timestamp.

        Args:
            session: Database session

        Returns:
            AppMetadata object or None
        """
        stmt = select(AppMetadata).where(AppMetadata.id == 1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    # ============================================================================
    # IMAGE GENERATION FUNCTIONS
    # ============================================================================

    def generate_summary_image(
        self,
        total_countries: int,
        top_countries: List[Country],
        last_refreshed: datetime,
        output_path: str = "cache/summary.png"
    ) -> None:
        """
        Generate summary image with total countries, top 5 by GDP, and timestamp.
        
        Args:
            total_countries: Total number of countries
            top_countries: List of top countries by GDP
            last_refreshed: Last refresh timestamp
            output_path: Path to save image
        """
        # Create cache directory if it doesn't exist
        Path("cache").mkdir(exist_ok=True)

        # Create image (800x600 white background)
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)

        # Use default font
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
            text_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except:
            # Fallback to default font
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()

        # Draw title
        draw.text((50, 50), "Country Data Summary", fill='black', font=title_font)

        # Draw total countries
        draw.text((50, 120), f"Total Countries: {total_countries}", fill='black', font=text_font)

        # Draw top 5 countries
        draw.text((50, 170), "Top 5 Countries by GDP:", fill='black', font=text_font)
        y_position = 210
        for i, country in enumerate(top_countries[:5], 1):
            gdp_formatted = f"{country.estimated_gdp:,.2f}" if country.estimated_gdp else "N/A"
            text = f"{i}. {country.name}: ${gdp_formatted}"
            draw.text((70, y_position), text, fill='black', font=text_font)
            y_position += 40

        # Draw timestamp
        timestamp_text = f"Last Refreshed: {last_refreshed.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        draw.text((50, 500), timestamp_text, fill='gray', font=text_font)

        # Save image
        img.save(output_path)
