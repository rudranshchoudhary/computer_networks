from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

class CustomTopo(Topo):
    def __init__(self):
        Topo.__init__(self)

        # Add switches
        switches = [self.addSwitch(f's{i}') for i in range(1, 9)]

        # Add hosts
        hosts = [self.addHost(f'h{i}') for i in range(1, 3)]

        # Add links between hosts and switches
        self.addLink(hosts[0], switches[0])
        self.addLink(hosts[0], switches[1])
        self.addLink(hosts[1], switches[6])
        self.addLink(hosts[1], switches[7])

        # Add links between switches to form a mesh topology
        self.addLink(switches[0], switches[1])
        self.addLink(switches[0], switches[2])
        self.addLink(switches[1], switches[3])
        self.addLink(switches[2], switches[4])
        self.addLink(switches[3], switches[4])
        self.addLink(switches[4], switches[5])
        self.addLink(switches[5], switches[6])
        self.addLink(switches[6], switches[7])
        self.addLink(switches[7], switches[2])

def main():
    setLogLevel('info')

    # Define multiple controllers (Controller1 and Controller2)
    controller1 = RemoteController('c1', ip='127.0.0.1', port=6633)
    controller2 = RemoteController('c2', ip='127.0.0.1', port=6655)

    # Create the custom topology
    topo = CustomTopo()

    # Assign switches to the two controllers
    net = Mininet(topo=topo, link=TCLink, controller=None)

    # Add controllers to the network
    net.addController(controller1)
    net.addController(controller2)

    # Start the network
    net.start()

    # Launch the CLI for testing
    CLI(net)

    # Stop the network
    net.stop()

if __name__ == '__main__':
    main()
