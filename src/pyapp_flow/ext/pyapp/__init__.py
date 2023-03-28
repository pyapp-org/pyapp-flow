"""
PyApp integration
"""

from pyapp.multiprocessing import Pool
import pyapp_flow.parallel_nodes


class MapNode(pyapp_flow.parallel_nodes.MapNode):
    """
    PyApp supporting MapNode pool
    """

    pool_type = Pool
