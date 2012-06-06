#!/usr/bin/python
'''
Create a non-blocking switch equivalent to a fat-tree.

Nikhil Handigol
'''

from mininet.topo import Topo
from dctopo import FatTreeTopo

class NonBlockingTopo( Topo ):
    "All hosts of a FatTree inter-connected by a single switch"

    LAYER_CORE = 0
    LAYER_AGG = 1
    LAYER_EDGE = 2
    LAYER_HOST = 3

    def __init__(self, k=4):
        super( NonBlockingTopo, self ).__init__()

        pods = range(0, k)
        core_sws = range(1, k / 2 + 1)
        agg_sws = range(k / 2, k)
        edge_sws = range(0, k / 2)
        hosts = range(2, k / 2 + 2)
        self.id_gen = FatTreeTopo.FatTreeNodeID

	core_id = self.id_gen(k, 1, 1).name_str()
	core_opts = self.def_nopts(self.LAYER_CORE, core_id)
        self.add_switch(core_id, **core_opts)

        for p in pods:
            for e in edge_sws:
                for h in hosts:
                    host_id = self.id_gen(p, e, h).name_str()
                    host_opts = self.def_nopts(self.LAYER_HOST, host_id)
                    self.add_host(host_id, **host_opts)
                    self.add_link(host_id, core_id)
        
    def def_nopts(self, layer, name = None):
        '''Return default dict for a FatTree topo.

        @param layer layer of node
        @param name name of node
        @return d dict with layer key/val pair, plus anything else (later)
        '''
        d = {'layer': layer}
        if name:
            id = self.id_gen(name = name)
            # For hosts only, set the IP
            if layer == self.LAYER_HOST:
              d.update({'ip': id.ip_str()})
              d.update({'mac': id.mac_str()})
            d.update({'dpid': "%016x" % id.dpid})
        return d

