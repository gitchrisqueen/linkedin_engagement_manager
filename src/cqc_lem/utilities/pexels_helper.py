# Import API class from pexels_api package
import os
import random
from pexels_api import API
from pexels_api.tools import Photo

# Create API object
api = API(os.environ['PEXELS_API_KEY'])


def get_photo(query: str) -> Photo:
    photos = get_photos(query)
    # Select 1 random photo from entries
    selected_photo = random.choice(photos)
    return selected_photo

def get_photos(query: str, num_of_photos: int = 25) -> list[Photo]:
    # Search for photos
    api.search(query, page=1, results_per_page=num_of_photos)
    # Get photo entries
    photos = api.get_entries()

    return photos

