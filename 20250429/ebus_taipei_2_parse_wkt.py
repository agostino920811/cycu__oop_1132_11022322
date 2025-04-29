# -*- coding: utf-8 -*-
"""
This module retrieves bus stop data for a specific route and direction from the Taipei eBus website,
saves the rendered HTML and CSV file, and stores the parsed data in a SQLite database.
"""
import json
import re
import pandas as pd
from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine, Column, String, Float, Integer, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base


class taipei_route_info:
    """
    Manages fetching, parsing, and storing bus stop data for a specified route and direction.
    """
    def __init__(self, route_id: str, direction: str = 'go', working_directory: str = 'data'):
        """
        Initializes the taipei_route_info by setting parameters and fetching the webpage content.

        Args:
            route_id (str): The unique identifier of the bus route.
            direction (str): The direction of the route; must be either 'go' or 'come'.
        """
        self.route_id = route_id
        self.direction = direction
        self.content = None
        self.url = f'https://ebus.gov.taipei/Route/StopsOfRoute?routeid={route_id}'
        self.working_directory = working_directory

        if self.direction not in ['go', 'come']:
            raise ValueError("Direction must be 'go' or 'come'")
        
        # Save the rendered HTML to a file for inspection
        self.html_file = f"{self.working_directory}/ebus_taipei_{self.route_id}.html"

        #read self.content from the self.html_file
        with open(self.html_file, 'r', encoding='utf-8') as file:
            self.content = file.read()

    def parse_wkt_fields(self) -> dict:
        """
        Parses WKT fields from the HTML content by capturing keys like 'wkt', 'wkt0', 'wkt1' and their LINESTRING values.
        
        Returns:
            dict: A dictionary where each key is a 'wkt' field and the value is its corresponding LINESTRING data.
        """

        wkt_dict = {}
        pattern = r'JSON\.stringify\s*\(\s*(\{[\s\S]*?\})\s*\)'
        match = re.search(pattern, self.content)
        if match:
            json_text = match.group(1)
            
            json_dict = json.loads(json_text)
            for key in json_dict.keys():
                if key.startswith('wkt'):
                    wkt_dict[key] = json_dict[key]
            
            return wkt_dict
        else:
            return {}
        
class taipei_route_list:
    """
    Manages fetching, parsing, and storing route data for Taipei eBus.
    """
    def __init__(self, working_directory: str = 'data'):
        """
        Initializes the taipei_route_list, fetches webpage content,
        configures the ORM, and sets up the SQLite database.

        Args:
            working_directory (str): Directory to store the HTML and database files.
        """
        self.working_directory = working_directory
        self.url = 'https://ebus.gov.taipei/ebus?ct=all'
        self.content = None

        # Setup ORM base and table
        Base = declarative_base()

        class bus_route_orm(Base):
            __tablename__ = 'data_route_list'

            route_id = Column(String, primary_key=True)
            route_name = Column(String)
            route_data_updated = Column(Integer, default=0)

        self.orm = bus_route_orm

        # Create and connect to the SQLite engine
        self.engine = create_engine(f'sqlite:///{self.working_directory}/hermes_ebus_taipei.sqlite3')
        self.engine.connect()
        Base.metadata.create_all(self.engine)

        # Create session
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.html_file_path = f'{self.working_directory}/hermes_ebus_taipei_route_list.html'


    def read_from_database(self) -> pd.DataFrame:
        """
        Reads bus route data from the SQLite database.

        Returns:
            pd.DataFrame: DataFrame containing bus route data.
        """
        query = self.session.query(self.orm)
        self.db_dataframe = pd.read_sql(query.statement, self.session.bind)
        return self.db_dataframe




if __name__ == "__main__":
    # Initialize and process route data
    route_list = taipei_route_list()
    #define a empty geodataframe for gathering all the following df 
    geo_df = pd.DataFrame()    

    for _, row in route_list.read_from_database().iterrows():
        try:
            route_info = taipei_route_info(route_id=row["route_id"], direction="go")
            dict_wkt = route_info.parse_wkt_fields()

            # Save the parsed data to a CSV file
            df = pd.DataFrame(dict_wkt.items(), columns=['wkt_id', 'wkt_string'])
            df['route_id'] = route_info.route_id
            df['route_name'] = row["route_name"]

            #convert df to geodataframe
            import geopandas as gpd
            df['geometry'] = gpd.GeoSeries.from_wkt(df['wkt_string'])
            df = gpd.GeoDataFrame(df, geometry='geometry')
 
            # Set the coordinate reference system (CRS) to WGS84
            df.crs = 'EPSG:4326'
            # Set the geometry column
            df.set_geometry('geometry', inplace=True)


            # Append the new data to the existing GeoDataFrame
            geo_df = pd.concat([geo_df, df], ignore_index=True)
            print(f"Route ID: {route_info.route_id}", len(dict_wkt))            
            print(f"Processing route {df}...")
        except Exception as e:
            print(f"Error processing route {row['route_name']}: {e}")

    # Save the combined GeoDataFrame to a GeoPackage
    geo_df.to_file(f"{route_list.working_directory}/ebus_taipei_routes.gpkg", layer='data_routes_wkt', driver='GPKG')