# -*- coding: utf-8 -*-
"""
This module retrieves bus stop data for a specific route and direction from the Taipei eBus website,
saves the rendered HTML and CSV file, and stores the parsed data in a SQLite database.
"""

import re
import pandas as pd
from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine, Column, String, Float, Integer, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os # Import os module to create directory

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
        # Ensure the working directory exists
        if not os.path.exists(self.working_directory):
            os.makedirs(self.working_directory)

        self.url = 'https://ebus.gov.taipei/ebus?ct=all'
        self.content = None
        self.dataframe = None # Initialize dataframe attribute

        # Fetch webpage content
        self._fetch_content()

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

    def _fetch_content(self):
        """
        Fetches the webpage content using Playwright and saves it as a local HTML file.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url)
            page.wait_for_timeout(3000)  # Wait for the page to load
            self.content = page.content()
            browser.close()

        # Save the rendered HTML to a file for inspection
        html_file_path = f'{self.working_directory}/hermes_ebus_taipei_route_list.html'
        with open(html_file_path, "w", encoding="utf-8") as file:
            file.write(self.content)

    def parse_route_list(self) -> pd.DataFrame:
        """
        Parses bus route data from the fetched HTML content.

        Returns:
            pd.DataFrame: DataFrame containing bus route IDs and names.

        Raises:
            ValueError: If no route data is found.
        """
        pattern = r'<li><a href="javascript:go\(\'(.*?)\'\)">(.*?)</a></li>'
        matches = re.findall(pattern, self.content, re.DOTALL)

        if not matches:
            raise ValueError("No data found for route table")

        bus_routes = [(route_id, route_name.strip()) for route_id, route_name in matches]
        self.dataframe = pd.DataFrame(bus_routes, columns=["route_id", "route_name"])
        return self.dataframe

    def save_to_database(self):
        """
        Saves the parsed bus route data to the SQLite database via SQLAlchemy ORM.
        """
        if self.dataframe is None:
            raise ValueError("No dataframe to save. Call parse_route_list() first.")
        for _, row in self.dataframe.iterrows():
            self.session.merge(self.orm(route_id=row['route_id'], route_name=row['route_name']))

        self.session.commit()

    def export_to_csv(self, file_path: str):
        """
        Exports the parsed bus route data to a CSV file.

        Args:
            file_path (str): The full path including filename where the CSV will be saved.
        """
        if self.dataframe is None:
            raise ValueError("No dataframe to export. Call parse_route_list() first.")

        # Ensure the directory for the CSV file exists
        output_dir = os.path.dirname(file_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")

        self.dataframe.to_csv(file_path, index=False, encoding='utf-8-sig') # Use 'utf-8-sig' for BOM, compatible with Excel
        print(f"Bus route list successfully exported to: {file_path}")


    def read_from_database(self) -> pd.DataFrame:
        """
        Reads bus route data from the SQLite database.

        Returns:
            pd.DataFrame: DataFrame containing bus route data.
        """
        query = self.session.query(self.orm)
        self.db_dataframe = pd.read_sql(query.statement, self.session.bind)
        return self.db_dataframe

    def set_route_data_updated(self, route_id: str, route_data_updated: int = 1):
        """
        Sets the route_data_updated flag in the database.

        Args:
            route_id (str): The ID of the bus route.
            route_data_updated (bool): The value to set for the route_data_updated flag.
        """
        self.session.query(self.orm).filter_by(route_id=route_id).update({"route_data_updated": route_data_updated})
        self.session.commit()

    def set_route_data_unexcepted(self, route_id: str):
        self.session.query(self.orm).filter_by(route_id=route_id).update({"route_data_updated": 2 })
        self.session.commit()

    def __del__(self):
        """
        Closes the session and engine when the object is deleted.
        """
        self.session.close()
        self.engine.dispose()


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

        self._fetch_content()

    def _fetch_content(self):
        """
        Fetches the webpage content using Playwright and writes the rendered HTML to a local file.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url)

            if self.direction == 'come':
                page.click('a.stationlist-come-go-gray.stationlist-come')

            page.wait_for_timeout(3000)  # Wait for page render
            self.content = page.content()
            browser.close()

        # Save the rendered HTML to a file for inspection
        self.html_file = f"{self.working_directory}/ebus_taipei_{self.route_id}_{self.direction}.html"
        with open(self.html_file, "w", encoding="utf-8") as file: # Added file writing for debugging
             file.write(self.content)

    def parse_route_info(self) -> pd.DataFrame:
        """
        Parses the fetched HTML content to extract bus stop data.

        Returns:
            pd.DataFrame: DataFrame containing bus stop information.

        Raises:
            ValueError: If no data is found for the route.
        """
        pattern = re.compile(
            r'<li>.*?<span class="auto-list-stationlist-position.*?">(.*?)</span>\s*'
            r'<span class="auto-list-stationlist-number">\s*(\d+)</span>\s*'
            r'<span class="auto-list-stationlist-place">(.*?)</span>.*?'
            r'<input[^>]+name="item\.UniStopId"[^>]+value="(\d+)"[^>]*>.*?'
            r'<input[^>]+name="item\.Latitude"[^>]+value="([\d\.]+)"[^>]*>.*?'
            r'<input[^>]+name="item\.Longitude"[^>]+value="([\d\.]+)"[^>]*>',
            re.DOTALL
        )

        matches = pattern.findall(self.content)
        if not matches:
            raise ValueError(f"No data found for route ID {self.route_id}")

        bus_routes = [m for m in matches]
        self.dataframe = pd.DataFrame(
            bus_routes,
            columns=["arrival_info", "stop_number", "stop_name", "stop_id", "latitude", "longitude"]
        )

        # Convert appropriate columns to numeric types
        self.dataframe["stop_number"] = pd.to_numeric(self.dataframe["stop_number"])
        self.dataframe["stop_id"] = pd.to_numeric(self.dataframe["stop_id"])
        self.dataframe["latitude"] = pd.to_numeric(self.dataframe["latitude"])
        self.dataframe["longitude"] = pd.to_numeric(self.dataframe["longitude"])

        self.dataframe["direction"] = self.direction
        self.dataframe["route_id"] = self.route_id

        return self.dataframe

    def save_to_database(self):
        """
        Saves the parsed bus stop data to the SQLite database.
        """
        db_file = f"{self.working_directory}/hermes_ebus_taipei.sqlite3"
        engine = create_engine(f"sqlite:///{db_file}")
        Base = declarative_base()

        class bus_stop_orm(Base):
            __tablename__ = "data_route_info_busstop"
            stop_id = Column(Integer)
            arrival_info = Column(String)
            stop_number = Column(Integer, primary_key=True) # stop_number should be unique within a route and direction
            stop_name = Column(String)
            latitude = Column(Float)
            longitude = Column(Float)
            direction = Column(String, primary_key=True)
            route_id = Column(String, primary_key=True)

            __table_args__ = (
                # You can add a composite primary key if stop_number alone isn't unique across directions/routes
                # primary_key=True,
                # UniqueConstraint('route_id', 'direction', 'stop_number', name='_route_direction_stop_uc'),
            )


        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        for _, row in self.dataframe.iterrows():
            # Use merge to handle updates if the primary key exists, or insert if new
            # For data_route_info_busstop, the primary key is (stop_number, direction, route_id)
            session.merge(bus_stop_orm(
                stop_id=row["stop_id"],
                arrival_info=row["arrival_info"],
                stop_number=row["stop_number"],
                stop_name=row["stop_name"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                direction=row["direction"],
                route_id=row["route_id"]
            ))

        session.commit()
        session.close()


if __name__ == "__main__":
    # Ensure the 'data' directory exists
    working_data_dir = 'data'
    if not os.path.exists(working_data_dir):
        os.makedirs(working_data_dir)

    # Initialize and process route data
    print("Fetching and parsing all bus route list...")
    route_list = taipei_route_list(working_data_dir)
    df_route_list = route_list.parse_route_list()
    route_list.save_to_database()
    print("Bus route list fetched, parsed, and saved to database.")

    # Define the exact CSV output path
    csv_output_path = r'C:\Users\ian50\OneDrive\文件\GitHub\cycu__oop_1132_11022322\期末\taipei_bus_routes.csv'
    route_list.export_to_csv(csv_output_path)


    # You can uncomment the following lines to print the retrieved route list
    # print("\n--- Retrieved Bus Route List ---")
    # print(df_route_list)
    # print("--------------------------------")

    # Example: Process specific bus routes (you can change bus_list to process more or all)
    # To process all routes: bus_list = df_route_list['route_id'].tolist()
    # For demonstration, let's pick a few known routes from the image or common ones.
    # The image shows "0東" which has route_id like '0100000A00'
    # "承德幹線" (Chengde Main Line) might be '0161000900'
    # "基隆幹線" (Keelung Main Line) might be '0161001500'
    bus_list = ['0100000A00', '0161000900', '0161001500'] # Example bus IDs based on typical Taipei eBus format

    print(f"\nProcessing bus stop information for selected routes: {bus_list}")

    for route_id in bus_list:
        print(f"\nProcessing route: {route_id}")
        try:
            # Process 'go' direction
            route_info_go = taipei_route_info(route_id, direction="go", working_directory=working_data_dir)
            df_stops_go = route_info_go.parse_route_info()
            route_info_go.save_to_database()
            print(f"  Direction 'go' for route {route_id} processed. Sample data:")
            # Print first few rows to confirm data
            if not df_stops_go.empty:
                print(df_stops_go[['stop_number', 'stop_name', 'latitude', 'longitude']].head())
            else:
                print("  No stop data found for 'go' direction.")


            # Process 'come' direction
            route_info_come = taipei_route_info(route_id, direction="come", working_directory=working_data_dir)
            df_stops_come = route_info_come.parse_route_info()
            route_info_come.save_to_database()
            print(f"  Direction 'come' for route {route_id} processed. Sample data:")
            if not df_stops_come.empty:
                print(df_stops_come[['stop_number', 'stop_name', 'latitude', 'longitude']].head())
            else:
                print("  No stop data found for 'come' direction.")


            route_list.set_route_data_updated(route_id)
            print(f"Route data for {route_id} updated status in main list.")

        except ValueError as ve:
            print(f"Error processing route {route_id}: {ve}. (No data found for this route's stops, possibly valid.)")
            route_list.set_route_data_unexcepted(route_id) # Mark as unexcepted if no stop data
        except Exception as e:
            print(f"An unexpected error occurred while processing route {route_id}: {e}")
            route_list.set_route_data_unexcepted(route_id)
            continue

    print("\nAll specified routes processed.")

    # You can read all bus stops from the database to verify
    # print("\n--- All Bus Stops in Database ---")
    # from sqlalchemy import create_engine
    # from sqlalchemy.orm import sessionmaker
    # from sqlalchemy.ext.declarative import declarative_base
    #
    # Base = declarative_base()
    # class bus_stop_orm(Base):
    #     __tablename__ = "data_route_info_busstop"
    #     stop_id = Column(Integer)
    #     arrival_info = Column(String)
    #     stop_number = Column(Integer, primary_key=True)
    #     stop_name = Column(String)
    #     latitude = Column(Float)
    #     longitude = Column(Float)
    #     direction = Column(String, primary_key=True)
    #     route_id = Column(String, primary_key=True)
    #
    # engine_read = create_engine(f'sqlite:///data/hermes_ebus_taipei.sqlite3')
    # Session_read = sessionmaker(bind=engine_read)
    # session_read = Session_read()
    # query_stops = session_read.query(bus_stop_orm)
    # df_all_stops = pd.read_sql(query_stops.statement, session_read.bind)
    # print(df_all_stops.head())
    # session_read.close()
    # engine_read.dispose()