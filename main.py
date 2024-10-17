from src.logger_setup import setup_logger
from src.database import Database

from datetime import datetime, timezone
from bs4 import BeautifulSoup

import tls_client
import json


logger = setup_logger("SNEAKER_RELEASE_INFO", "bot")


headers = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
  "Accept": "*/*",
  "Accept-Language": "en-GB,en;q=0.5",
  "Accept-Encoding": "gzip, deflate, br, zstd",
  "Referer": "https://www.sneaktorious.com/",
  "DNT": "1",
  "Connection": "keep-alive",
  "Sec-Fetch-Dest": "empty",
  "Sec-Fetch-Mode": "no-cors",
  "Sec-Fetch-Site": "same-origin",
  "Sec-GPC": "1",
  "Priority": "u=4",
  "TE": "trailers"
}



def main():
    try:
        db = Database()
        #db.remove_all_docs()
    except Exception as error:
        logger.error(error)
        raise error

    # Make a request to fetch the product data
    data = request_data()
    
    # Create key pair values between the ids and the respective item
    brands =  create_filter_dict(data, "brand", "identifier", "name")
    regions = create_filter_dict(data, "region", "identifier", "name")

    # A list of all the products in the file
    requested_products = data["items"]

    # Fetch the products from the database
    db_docs = db.fetch_docs({}, {"_id": 0})
    db_products = {prod["link"]: prod for prod in db_docs}

    products = []
    for prod in requested_products[:1]:
        prod_data = {
            "ping_sent": False,
            "regions": [],
            "type": "Sneaker-Release-Info",
            "timestamp": datetime.now(timezone.utc)
        }

        # Fetch the release date
        release_date = prod["releaseDate"]
        if release_date is None:
            continue
        prod_data["release_date"] = datetime.fromisoformat(release_date)

        prod_data["link"] = f"https://www.sneaktorious.com{prod['link']}"
        # Get the respective product from the database
        db_prod = db_products.get(prod_data["link"])
        prod_data["send_ping"] = should_send_ping(db_prod, prod_data)

        # If the product already exist and send ping is False then there is no need to update the product
        if db_prod is not None and prod_data["send_ping"] is False:
            continue
        
        # Fetch the name of the website where the product is going to be released
        prod_data["website"] = brands.get(prod["brands"][0])
        if prod_data["website"] is None:
            continue

        prod_data["product_name"] = prod["title"]
        prod_data["no_raffles"] = prod["rafflesCount"]

        # Fetch the regions where the product is going to be released
        for region in prod["region"]:
            prod_data["regions"].append(regions[region])

        prod_data["image"] = extract_image(prod["thumbnail"])
        products.append(prod_data)

    db.update_products(products)



def should_send_ping(old, new):
    # Get the current time in UTC
    current_time = datetime.now(timezone.utc)
    time_difference = new["release_date"] - current_time

    # Check if the current time is within 1 day before the release
    if 0 < time_difference.total_seconds() <= 86400:
        if old is None:
            return True
        # If the 1-day ping hasn't been sent yet
        if not old.get("ping_sent", False):
            return True  

    # No ping needed at this time
    return False


# Function to extract the largest image URL from data-srcset
def get_largest_image_url(source):
    data_srcset = source['data-srcset']
    # Split by comma to get individual images
    images = data_srcset.split(',')
    # Initialize variables to track the largest image
    largest_image = None
    largest_width = 0

    for image in images:
        # Split by whitespace to separate the URL and width
        url, width = image.rsplit(' ', 1)
        width = int(width[:-1])  # Remove the 'w' and convert to int

        # Check if this image width is larger than the current largest
        if width > largest_width:
            largest_width = width
            largest_image = url
    
    return largest_image


def extract_image(image_html):
    soup = BeautifulSoup(image_html, "lxml")

    source_webp = soup.find('source', type='image/webp')
    largest_webp_image = get_largest_image_url(source_webp)

    return largest_webp_image


def create_filter_dict(data, filter_name, key, value):
    filter_dict = {}
    try:
        filter_list = data["filter"][filter_name]
        
        for di in filter_list:
            filter_dict[di[key]] = di[value]

    except Exception as error:
        logger.error(error)

    finally:
        return filter_dict
    


def request_data(url = "https://www.sneaktorious.com/sneakers.json"):
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



if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise error
