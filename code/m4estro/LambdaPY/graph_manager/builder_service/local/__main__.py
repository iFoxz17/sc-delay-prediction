import json
import logging
import igraph as ig
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PLATFORM_COMM_LAYER_PATH = os.path.join(os.path.dirname(__file__), "..\\..\\..\\platform_comm_layer\\python")
if PLATFORM_COMM_LAYER_PATH not in sys.path:
    sys.path.append(PLATFORM_COMM_LAYER_PATH)

GRAPH_LAYER_PATH = os.path.join(os.path.dirname(__file__), "..\\..\\..\\graph_layer\\python")
if GRAPH_LAYER_PATH not in sys.path:
    sys.path.append(GRAPH_LAYER_PATH)

GRAPH_BUILDER_PATH = os.path.join(os.path.dirname(__file__), "..\\")
if GRAPH_BUILDER_PATH not in sys.path:
    sys.path.append(GRAPH_BUILDER_PATH)

GRAPH_MANAGER_LAMBDA_PATH = os.path.join(os.path.dirname(__file__), "..\\..\\")
if GRAPH_MANAGER_LAMBDA_PATH not in sys.path:
    sys.path.append(GRAPH_MANAGER_LAMBDA_PATH)

from model.base import Base
from csv_data_loader import CSVDataLoader
from graph_builder import GraphBuilder

logger = logging.getLogger(__name__)

SQLITE_DB_URL = f"sqlite:///{os.path.join(os.path.dirname(__file__))}\\temp.db"
CSV_PATH = os.path.join(os.path.dirname(__file__), "csv\\")
SCGRAPH_PATH = os.path.join(os.path.dirname(__file__), "sc_graph.json")

if __name__ == "__main__":
    engine = create_engine(SQLITE_DB_URL, echo=True, future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    logger.info("Starting CSV data loading...")
    loader: CSVDataLoader = CSVDataLoader(
        session, base_path=CSV_PATH
    )
    loader.load()
    session.close()
    logger.info("CSV data loading completed.")

    logger.info("Building graph...")
    builder: GraphBuilder = GraphBuilder(SQLITE_DB_URL)
    graph: ig.Graph = builder.build()
    logger.info("Graph building completed.")

    engine.dispose()

    logger.info(f"Grap summary: {graph.summary()}")

    logger.info(f"Serializing graph to {SCGRAPH_PATH}...")
    with open(SCGRAPH_PATH, "w") as f:
        json.dump(graph.to_dict_list(use_vids=False, vertex_name_attr='name') , f, indent=4)
    logger.info("Graph serialization completed.")

    