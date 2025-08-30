from typing import Dict
import os
import pandas as pd
from sqlalchemy.orm import Session

from model.manufacturer import Manufacturer
from model.vertex import Vertex
from model.route import Route
from model.country import Country
from model.location import Location
from model.supplier import Supplier
from model.site import Site
from model.carrier import Carrier
from model.route_order import RouteOrder
from model.order import Order
from model.ori import ORI
from model.oti import OTI
from model.tmi import TMI
from model.wmi import WMI

DEFAULT_FILENAMES = {
    "countries": "country.csv",
    "locations": "location.csv",
    "carriers": "carrier.csv",
    "manufacturers": "manufacturer.csv",
    "suppliers": "supplier.csv",
    "sites": "site.csv",
    "orders": "order.csv",
    "vertices": "vertex.csv",
    "routes": "route.csv",
    "route_orders": "route_order.csv",
    "ori": "ori.csv",
    "oti": "oti.csv",
    "tmi": "tmi.csv",
    "wmi": "wmi.csv"
}

class CSVDataLoader():
    def __init__(self, session: Session, base_path: str, filenames: Dict[str, str] = DEFAULT_FILENAMES):
        
        self.session = session
        self.base_path = base_path
        self.filenames = filenames

    def clear_all_tables(self):
        self.session.query(ORI).delete()
        self.session.query(OTI).delete()
        self.session.query(TMI).delete()
        self.session.query(WMI).delete()
        self.session.query(Route).delete()
        self.session.query(Vertex).delete()
        self.session.query(Order).delete()
        self.session.query(RouteOrder).delete()
        self.session.query(Carrier).delete()
        self.session.query(Supplier).delete()
        self.session.query(Site).delete()
        self.session.query(Manufacturer).delete()
        self.session.query(Location).delete()
        self.session.query(Country).delete()
        
        self.session.commit()

    def load(self):
        base_path = self.base_path
        filenames = self.filenames

        self.clear_all_tables()

        # Helper to load a dataframe from CSV
        def load_df(name):
            return pd.read_csv(os.path.join(base_path, name))

        # Country
        countries = []
        for _, row in load_df(filenames["countries"]).iterrows():
            country = Country(
                id=int(row['id']),
                code=row['code'] if pd.notna(row['code']) else "NA",            # Namibia bug in pandas
                name=row['name'],
                total_holidays=int(row['total_holidays']),
                weekend_start=int(row['weekend_start']),
                weekend_end=int(row['weekend_end'])
            )
            countries.append(country)
        self.session.add_all(countries)
        self.session.commit()

        # Locations
        locations = []
        for _, row in load_df(filenames['locations']).iterrows():
            location = Location(
                id=int(row['id']),
                name=row['name'],
                city=row['city'],
                state=row['state'],
                country_code=row['country_code'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
            )
            locations.append(location)
        
        self.session.add_all(locations)
        self.session.commit()

        # Carriers
        carriers = []
        for _, row in load_df(filenames['carriers']).iterrows():
            carrier = Carrier(
                name=row['name'],
                n_losses=int(row['n_losses']),
                n_orders=int(row['n_orders']),
            )
            carriers.append(carrier)

        self.session.add_all(carriers)
        self.session.commit()

        # Manufacturer(s)
        manufacturers = []
        for _, row in load_df(filenames['manufacturers']).iterrows():
            manufacturer = Manufacturer(id=int(row['id']), name=row['name'], location_name=row['location_name'])
            manufacturers.append(manufacturer)

        self.session.add_all(manufacturers)
        self.session.commit()

        # Suppliers
        suppliers = []
        for _, row in load_df(filenames['suppliers']).iterrows():
            supplier = Supplier(id=int(row['id']), manufacturer_supplier_id=row['manufacturer_supplier_id'], name=row['name'])
            suppliers.append(supplier)
        
        self.session.add_all(suppliers)
        self.session.commit()
        
        # Sites
        sites = []
        for _, row in load_df(filenames['sites']).iterrows():
            site = Site(
                id=int(row['id']),
                supplier_id=int(row['supplier_id']),
                location_name=row['location_name'],
                n_rejections=int(row['n_rejections']),
                n_orders=int(row['n_orders'])
            )
            sites.append(site)
        
        self.session.add_all(sites)
        self.session.commit()

        # Orders
        orders = []
        for _, row in load_df(filenames['orders']).iterrows():
            order = Order(
                id=int(row['id']),
                manufacturer_id=int(row['manufacturer_id']),
                manufacturer_order_id=int(row['manufacturer_order_id']),
                site_id=int(row['site_id']),
                carrier_id=row['carrier_id'],
                status=row['status'],
                n_steps=int(row['n_steps']),
                tracking_link=row['tracking_link'],
                tracking_number=row['tracking_number'],
                manufacturer_creation_timestamp=pd.to_datetime(row['manufacturer_creation_timestamp']),
                manufacturer_estimated_delivery_timestamp=pd.to_datetime(row['manufacturer_estimated_delivery_timestamp']) if pd.notna(row['manufacturer_estimated_delivery_timestamp']) else None,
                manufacturer_confirmed_delivery_timestamp=pd.to_datetime(row['manufacturer_confirmed_delivery_timestamp']) if pd.notna(row['manufacturer_confirmed_delivery_timestamp']) else None,
                carrier_creation_timestamp=pd.to_datetime(row['carrier_creation_timestamp']) if pd.notna(row['carrier_creation_timestamp']) else None,
                carrier_estimated_delivery_timestamp=pd.to_datetime(row['carrier_estimated_delivery_timestamp']) if pd.notna(row['carrier_estimated_delivery_timestamp']) else None,
                carrier_confirmed_delivery_timestamp=pd.to_datetime(row['carrier_confirmed_delivery_timestamp']) if pd.notna(row['carrier_confirmed_delivery_timestamp']) else None,
                SLS=bool(row['SLS'])
            )
            orders.append(order)
        
        self.session.add_all(orders)
        self.session.commit()

        # Vertices
        vertices = []
        for _, row in load_df(filenames['vertices']).iterrows():
            vertex = Vertex(id=int(row['id']), name=row['name'], type=row['type'])
            vertices.append(vertex)

        self.session.add_all(vertices)
        self.session.commit()

        # Routes
        routes = []
        for _, row in load_df(filenames['routes']).iterrows():
            route = Route(source_id=int(row['source_id']), destination_id=int(row['destination_id']))
            routes.append(route)

        self.session.add_all(routes)
        self.session.commit()

        # RouteOrders
        route_orders = []
        for _, row in load_df(filenames['route_orders']).iterrows():
            route_order = RouteOrder(
                source_id=int(row['source_id']),
                destination_id=int(row['destination_id']),
                order_id=int(row['order_id']),
            )
            route_orders.append(route_order)
        
        self.session.add_all(route_orders)
        self.session.commit()
        
        # ORI
        oris = []
        for _, row in load_df(filenames['ori']).iterrows():
            ori = ORI(vertex_id=int(row['vertex_id']), created_at=pd.to_datetime(row['created_at']), hours=float(row['hours']))
            oris.append(ori)

        self.session.add_all(oris)
        self.session.commit()

        # OTI
        otis = []
        for _, row in load_df(filenames['oti']).iterrows():
            oti = OTI(source_id=int(row['source_id']), destination_id=int(row['destination_id']), created_at=pd.to_datetime(row['created_at']), hours=float(row['hours']))
            otis.append(oti)

        self.session.add_all(otis)
        self.session.commit()

        # TMI
        tmis = []
        for _, row in load_df(filenames['tmi']).iterrows():
            tmi = TMI(source_id=int(row['source_id']), 
                      destination_id=int(row['destination_id']),
                      created_at=pd.to_datetime(row['created_at']),
                      timestamp=pd.to_datetime(row['timestamp']),
                      transportation_mode=row['transportation_mode'],
                      value=float(row['value'])
                      )
            tmis.append(tmi)

        self.session.add_all(tmis)
        self.session.commit()

        # WMI
        wmis = []
        for _, row in load_df(filenames['wmi']).iterrows():
            wmi = WMI(source_id=int(row['source_id']), 
                      destination_id=int(row['destination_id']), 
                      created_at=pd.to_datetime(row['created_at']),
                      timestamp=pd.to_datetime(row['timestamp']),
                      n_interpolation_points=int(row['n_interpolation_points']),
                      step_distance_km=float(row['step_distance_km']),
                      value=float(row['value'])
                      )
            wmis.append(wmi)
        
        self.session.add_all(wmis)
        self.session.commit()