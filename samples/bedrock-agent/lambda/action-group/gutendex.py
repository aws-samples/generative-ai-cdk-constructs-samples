import requests


def get_books_from_gutendex(n: int) -> dict:
    """Return the count and first n books from the /books API."""
    api_url = "https://gutendex.com"
    response = requests.get(api_url + "/books")
    books = response.json()
    return {"count": books["count"], "books": books["results"][:n]}
