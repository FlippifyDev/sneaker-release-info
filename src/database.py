from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pymongo import UpdateOne

import logging
import pymongo
import os

logger = logging.getLogger("PING-MANAGER")

load_dotenv()


class Database():
    def __init__(self) -> None:
        # Config
        db_deployment =  os.getenv("DB_DEPLOYMENT")
        db_name =        os.getenv("DB_NAME")
        username =       os.getenv("DB_USERNAME")
        password =       os.getenv("DB_PASSWORD")

        # Config - Collections Names
        results_col =              os.getenv("COL_RESULTS")

        # Connection
        conn_string = f"mongodb+srv://{username}:{password}@{db_deployment}.mongodb.net/"
        self.client = pymongo.MongoClient(conn_string)
        self.db = self.client[db_name]

        # Collections
        self.results_col = self.db[results_col]

        # Create or modify the collection with changeStreamPreAndPostImages enabled
        try:
            self.db.create_collection(results_col, changeStreamPreAndPostImages={"enabled": True})
        except pymongo.errors.CollectionInvalid:
            # Collection already exists, so modify it to enable pre- and post-images
            self.db.command({
                'collMod': results_col,
                'changeStreamPreAndPostImages': {'enabled': True}
            })



    def delete_old_releases(self):
        """Delete documents where release_date is more than 4 days old."""
        try:
            # Get the current time in UTC
            current_time = datetime.now(timezone.utc)
            
            # Calculate the cutoff time for 4 days old
            cutoff_time = current_time - timedelta(days=4)
            
            # Query to find documents with release_date older than 4 days
            query = {"release_date": {"$lt": cutoff_time}}
            
            # Perform the deletion operation
            result = self.results_col.delete_many(query)
            
            # Log or return the result of the deletion
            logger.info(f"Deleted {result.deleted_count} documents where release_date is older than 4 days.")

        except Exception as e:
            logger.error(f"An error occurred while deleting documents: {e}")            



    def fetch_docs(self, query, projection):
        return list(self.results_col.find(query, projection))
    


    def remove_all_docs(self):
        try:
            result = self.results_col.delete_many({})
            logger.info(f"Deleted {result.deleted_count} documents from the collection.")
        except Exception as e:
            logger.error(f"An error occurred while deleting documents: {e}")



    def update_products(self, products):
        operations = []  # A list to hold the batch of updates

        for product in products:
            # The unique identifier for each product, assuming it's the link or product_name
            query = {"link": product["link"]}

            # Define the fields to update. Here we're using the `$set` operator
            update_data = {
                "$set": product
            }

            # Add the update operation to the batch
            operations.append(UpdateOne(query, update_data, upsert=True))

        if operations:
            try:
                # Perform the bulk update
                result = self.results_col.bulk_write(operations)
                logger.info(f"Updated {result.matched_count} products, inserted {result.upserted_count} new products.")
            except Exception as e:
                logger.error(f"Error updating products: {e}")
    
    

    def add_products(self, products_to_add): 
        try:
            for product in products_to_add:
                # Check if a product with the same 'deal-link' already exists
                if self.results_col.find_one({"link": product['link']}):
                    continue

                # Insert product if it's not a duplicate
                self.results_col.insert_one(product)

            return True
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Error while adding products to the database: {e}")
            return False