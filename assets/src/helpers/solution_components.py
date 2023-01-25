import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def get_files_from_dir(path):
    dashboards_json_elements = {}

    for child in path.iterdir():
        logger.debug("Object %s found", child)

        with open(child) as f:
            dashboards_json_elements[child.stem] = f.read()
            logger.debug("Object %s read", child)

    return dashboards_json_elements


class SolutionComponents:
    def __init__(self):
        path = Path('./src/dashboards_definitions_json')

        logger.debug("Entering path %s, attempting to read all Dashboard files", path)

        self.dashboards = get_files_from_dir(path / 'dashboards')
        self.templates = get_files_from_dir(path / 'templates')
        self.index_patterns = get_files_from_dir(path / 'index_patterns')
        self.visualizations = get_files_from_dir(path / 'visualizations')

        logger.info("Components successfully read")
