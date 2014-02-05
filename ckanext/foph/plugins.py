import ckan
import ckan.plugins as p
from pylons import config

class FophHarvest(p.SingletonPlugin):
    """
    Plugin containing the harvester for FOPH
    """
