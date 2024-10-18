from src.logger_setup import setup_logger
from src.scrapers import fetch_scrapers
from src.database import Database


logger = setup_logger("SNEAKER_RELEASE_INFO", "bot")



def main():
    try:
        db = Database()
        
    except Exception as error:
        logger.error(error)
        raise error
    
    scrapers = fetch_scrapers()
    for scraper in scrapers:
        scraper(db)

    db.delete_old_releases()



if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise error
