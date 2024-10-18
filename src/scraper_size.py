from datetime import datetime, timezone
from bs4 import BeautifulSoup


import tls_client
import logging
import json


logger = logging.getLogger("SNEAKER_RELEASE_INFO")


headers = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
  "Accept": "*/*",
  "Accept-Language": "en-GB,en;q=0.5",
  "Accept-Encoding": "gzip, deflate, br, zstd",
  "Referer": "https://www.size.co.uk/",
  "Origin": "https://www.size.co.uk",
  "DNT": "1",
  "Connection": "keep-alive",
  "Sec-Fetch-Dest": "empty",
  "Sec-Fetch-Mode": "cors",
  "Sec-Fetch-Site": "cross-site",
  "Sec-GPC": "1",
}


def size_run(db):
    # Make a request to fetch the product data
    data = request_data()

    # A list of all the products in the file
    requested_products = data["upcoming"]

    # Fetch the products from the database
    db_docs = db.fetch_docs({"provider": "size"}, {"_id": 0})
    db_products = {prod["link"]: prod for prod in db_docs}

    products = []
    for prod in requested_products:
        prod_data = {
            "website": "Size",
            "ping_sent": False,
            "provider": "size",
            "type": "Sneaker-Release-Info",
            "timestamp": datetime.now(timezone.utc)
        }

        # Fetch the release date and check if it's within 5 minutes from now
        release_date = prod.get("launchDate")
        if release_date is None:
            continue
        release_datetime = datetime.fromisoformat(release_date)

        # Set the release date in the product data
        prod_data["release_date"] = release_datetime

        # Fetch the product link
        prod_data["link"] = prod.get("link")
        if prod_data["link"] is None:
            continue
            
        # Get the respective product from the database
        db_prod = db_products.get(prod_data["link"])
        prod_data["send_ping"] = should_send_ping(db_prod, prod_data)

        # If the product already exists or send ping is False, skip updating
        if (db_prod is not None) or (not prod_data["send_ping"]):
            continue

        # Set product name and price
        prod_data["product_name"] = prod.get("name")
        prod_data["price"] = round(float(prod["price"]["amount"]), 2)

        # Initialize custom_fields field with additional product data
        custom_fields = {
            "Style Code": prod.get("PLU"),
            "Price": round(float(prod["price"]["amount"]), 2),
        }
        prod_data["custom_fields"] = custom_fields

        # Fetch and set the image
        prod_data["image"] = prod.get("mainImage", {}).get("original")

        # Append the product data to the list for bulk update
        products.append(prod_data)

    # Update the products in the database
    if products:
        db.update_products(products)


def process_brand(brand: str):
    brand = brand.replace("-", " ")
    return brand.title()


def should_send_ping(old, new):
    # Get the current time in UTC
    current_time = datetime.now(timezone.utc)
    time_difference = new["release_date"] - current_time

    # Check if the current time is within 5 minutes after the release
    if -300 < time_difference.total_seconds() <= 0:
        if old is None:
            return True
        if not old.get("ping_sent", False):
            return True  

    # No ping needed at this time
    return False




def request_data(url = "https://mosaic-platform.jdmesh.co/public/stores/size/upcoming"):
    data = {}

    try:
        session = tls_client.Session(
            client_identifier="firefox_120",
            random_tls_extension_order=True
        )

        res = session.get(url, headers=headers)
        data = json.loads(res.content)

    except Exception as error:
        logger.error(error)

    finally:
        return data

