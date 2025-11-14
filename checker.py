import os
from dotenv import load_dotenv
from googlemaps import Client, exceptions, geocoding


load_dotenv()

def is_land(lat, lng):
    """
    Checks if a coordinate is on land using Google Maps Geocoding API.
    It determines this by checking for land-specific types like 'route' in the response.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("API key not found. Please set GOOGLE_MAPS_API_KEY in your .env file.")

    try:
        gmaps = Client(key=api_key)
        
        # Reverse geocode the coordinates
        reverse_geocode_result = geocoding.reverse_geocode(gmaps, (lat, lng))
        
        # If the result is empty, it's likely sea or a very remote area.
        if not reverse_geocode_result:
            return False
            
        # Define types that strongly indicate a land-based location.
        land_indicators = {'route', 'street_address', 'premise', 'intersection'}

        # Check all returned results for any land-indicating types.
        for result in reverse_geocode_result:
            # The 'types' field is a list of strings.
            # We check if any of our indicators are present in this list.
            if any(indicator in result.get('types', []) for indicator in land_indicators):
                return True # Found a land indicator, so it's land.

        # If no land indicators were found in any of the results, it's likely water.
        return False
    except exceptions.ApiError as e:
        print(f"An API error occurred: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False
