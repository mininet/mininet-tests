#!/usr/bin/python

from mininet.topo import Topo

class TwoHostNInterfaceTopo(Topo):
    "Two hosts connected by N interfaces"

    def __init__(self, n, **opts):
        "n is the number of interfaces connecting the hosts."
        super(TwoHostNInterfaceTopo, self).__init__(**opts)

        # Note: switches are not strictly necessary, but they do give
        # visibility into traffic from the root namespace.
        SWITCHES = ['s%i' % i for i in range(1, n + 1)]
        for sw in SWITCHES:
            self.add_switch(sw)

        HOSTS = ['h1', 'h2']
        for h in HOSTS:
            self.add_host(h)
            for sw in SWITCHES:
                self.add_link(h, sw)


topos = {'2hostNintf': lambda n: TwoHostNInterfaceTopo(n)}