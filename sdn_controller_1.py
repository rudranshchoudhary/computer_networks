Conversation opened. 2 messages. All messages read.

Skip to content
Using BITS Pilani University Mail with screen readers
f20190545@pilani.bits-pilani.ac.in 

4 of 15
Final ACN project

RUDRANSH CHOUDHARY <h20240309@pilani.bits-pilani.ac.in>
Attachments
Sat, Nov 23, 2024, 7:44 AM
to Animesh, VAIBHAV

Final controller and topology code ,everything is working fine

 2 Attachments
  •  Scanned by Gmail

RUDRANSH CHOUDHARY <h20240309@pilani.bits-pilani.ac.in>
Attachments
Tue, Feb 4, 2025, 10:21 AM
to NAGGENDER

 2 Attachments
  •  Scanned by Gmail
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.topology import event
from ryu.topology.api import get_switch, get_link
import logging


class FailureRecoveryController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(FailureRecoveryController, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.network_graph = {
            1: {3: {'out_port': 2}, 4: {'out_port': 3}},
            2: {3: {'out_port': 2}, 5: {'out_port': 3}},
            3: {1: {'out_port': 1}, 2: {'out_port': 2}, 4: {'out_port': 4}, 5: {'out_port': 3}},
            4: {1: {'out_port': 1}, 3: {'out_port': 3}, 5: {'out_port': 2}},
            5: {2: {'out_port': 2}, 3: {'out_port': 3}, 4: {'out_port': 1}},
        }
        self.host_to_switch = {
            'h1': {'switch': 1, 'port': 1},  # h1 connected to switch 1, port 1
            'h2': {'switch': 2, 'port': 1},  # h2 connected to switch 2, port 1
        }
        self.host_mac = {
            'h1': '00:00:00:00:00:01',  # MAC address of h1
            'h2': '00:00:00:00:00:02',  # MAC address of h2
        }
        self.host_ips = {
            'h1': '10.0.0.1',  # IP address of h1
            'h2': '10.0.0.2',  # IP address of h2
        }
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.DEBUG)
        self.logger.debug("Controller initialized.")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle initial switch features request."""
        datapath = ev.msg.datapath
        dpid = datapath.id
        self.datapaths[dpid] = datapath
        self.logger.info(f"Switch {dpid} connected and registered.")

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Allow LLDP packets to the controller
        self.logger.debug(f"Adding LLDP flow to switch {dpid}.")
        match = parser.OFPMatch(eth_type=0x88cc)  # LLDP ethertype
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        # Default flow to send unknown packets to controller
        self.logger.debug(f"Adding default flow to switch {dpid}.")
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        """Add a flow entry to the switch."""
        self.logger.debug(f"Preparing to add flow to switch {datapath.id} with priority {priority}.")
        self.logger.debug(f"Match: {match}, Actions: {actions}")
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)
        self.logger.info(f"Flow successfully added to switch {datapath.id}.")

    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        """Update network topology on switch connection."""
        self.logger.info(f"New switch detected: {ev.switch.dp.id}")
        switch_list = get_switch(self, None)
        self.logger.info(f"Current detected switches: {[sw.dp.id for sw in switch_list]}")
        self.logger.debug("Triggering path recalculation after new switch detection.")
        self.recalculate_paths()

    @set_ev_cls(event.EventSwitchLeave)
    def switch_leave_handler(self, ev):
        """Handle switch failure events."""
        dpid = ev.switch.dp.id
        self.logger.warning(f"Switch failure detected: {dpid}")

        # Remove the failed switch from the network graph
        if dpid in self.network_graph:
            self.logger.debug(f"Removing switch {dpid} from network graph.")
            del self.network_graph[dpid]
        
        # Remove any connections to the failed switch from other switches
        for node in self.network_graph:
            if dpid in self.network_graph[node]:
                self.logger.debug(f"Removing connection from switch {node} to failed switch {dpid}.")
                del self.network_graph[node][dpid]
        
        # Remove the failed switch from the datapaths
        if dpid in self.datapaths:
            self.logger.debug(f"Removing switch {dpid} from datapaths.")
            del self.datapaths[dpid]
        
        # Recalculate paths to handle the failure
        self.logger.info("Recalculating paths due to switch failure.")
        self.recalculate_paths()

    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        """Handle link recovery events."""
        src_dpid = ev.link.src.dpid
        dst_dpid = ev.link.dst.dpid
        src_port = ev.link.src.port_no
        dst_port = ev.link.dst.port_no

        self.logger.info(f"Link recovery detected: {src_dpid} -> {dst_dpid}")

        # Add the link back to the network graph
        if src_dpid not in self.network_graph:
            self.network_graph[src_dpid] = {}
        if dst_dpid not in self.network_graph:
            self.network_graph[dst_dpid] = {}

        self.network_graph[src_dpid][dst_dpid] = {'out_port': src_port}
        self.network_graph[dst_dpid][src_dpid] = {'out_port': dst_port}

        # Recalculate paths to include the recovered link
        self.logger.info("Recalculating paths due to link recovery.")
        self.recalculate_paths()

    @set_ev_cls(event.EventLinkDelete)
    def link_delete_handler(self, ev):
        """Handle link failure events."""
        src_dpid = ev.link.src.dpid
        dst_dpid = ev.link.dst.dpid

        self.logger.warning(f"Link failure detected: {src_dpid} -> {dst_dpid}")

        # Remove the failed link from the network graph
        if src_dpid in self.network_graph and dst_dpid in self.network_graph[src_dpid]:
            self.logger.debug(f"Removing link {src_dpid} -> {dst_dpid} from network graph.")
            del self.network_graph[src_dpid][dst_dpid]
        if dst_dpid in self.network_graph and src_dpid in self.network_graph[dst_dpid]:
            self.logger.debug(f"Removing link {dst_dpid} -> {src_dpid} from network graph.")
            del self.network_graph[dst_dpid][src_dpid]

        # Recalculate paths to handle the failure
        self.logger.info("Recalculating paths due to link failure.")
        self.recalculate_paths()

    def recalculate_paths(self):
        """Calculate shortest paths for all switch pairs and install flows."""
        self.logger.info("Starting path recalculation for the entire network.")
        for src in self.network_graph:
            for dst in self.network_graph:
                if src != dst:
                    self.logger.debug(f"Calculating shortest path from {src} to {dst}.")
                    path = self.dijkstra(src, dst)
                    if path:
                        self.logger.info(f"Path from {src} to {dst} found: {path}")
                        # Ensure paths are only between hosts
                        if (f"10.0.0.{src}" in self.host_ips.values()) and (f"10.0.0.{dst}" in self.host_ips.values()):
                            self.install_path_flows(path, f"10.0.0.{src}", f"10.0.0.{dst}")
                    else:
                        self.logger.warning(f"No path found from {src} to {dst}.")

    def dijkstra(self, src, dst):
        """Dijkstra's algorithm to find the shortest path."""
        self.logger.debug(f"Running Dijkstra's algorithm from {src} to {dst}.")
        unvisited = set(self.network_graph.keys())
        distances = {node: float('inf') for node in unvisited}
        distances[src] = 0
        previous_nodes = {node: None for node in unvisited}

        while unvisited:
            current_node = min(unvisited, key=lambda node: distances[node])
            unvisited.remove(current_node)
            self.logger.debug(f"Visiting node {current_node} with current distance {distances[current_node]}.")

            if distances[current_node] == float('inf'):
                self.logger.debug("Unreachable node found, stopping algorithm.")
                break

            for neighbor, data in self.network_graph[current_node].items():
                if neighbor in unvisited:
                    new_distance = distances[current_node] + 1  # Uniform cost for all links
                    self.logger.debug(f"Checking neighbor {neighbor}, new distance: {new_distance}.")
                    if new_distance < distances[neighbor]:
                        distances[neighbor] = new_distance
                        previous_nodes[neighbor] = current_node
                        self.logger.debug(f"Updated shortest path to {neighbor} via {current_node}.")

            if current_node == dst:
                self.logger.debug(f"Destination {dst} reached.")
                break

        # Reconstruct path
        path = []
        current = dst
        while previous_nodes[current] is not None:
            path.insert(0, current)
            current = previous_nodes[current]
        if path:
            path.insert(0, src)

        self.logger.debug(f"Shortest path from {src} to {dst}: {path}")
        return path if path else None

    def install_path_flows(self, path, src_ip, dst_ip):
        """Install flow rules along a given path, including host connections."""
        self.logger.info(f"Installing flows for path: {path} from {src_ip} to {dst_ip}")

        # Check if the source or destination is a host
        src_switch, src_out_port = None, None
        dst_switch, dst_in_port = None, None

        for host, connection in self.host_to_switch.items():
            if src_ip == self.host_ips.get(host):
                src_switch = connection['switch']
                src_out_port = connection['port']
            if dst_ip == self.host_ips.get(host):
                dst_switch = connection['switch']
                dst_in_port = connection['port']

        # Install flow for the source host to the first switch in the path
        if src_switch and len(path) > 0:
            first_switch = path[0]
            if first_switch in self.datapaths:
                datapath = self.datapaths[first_switch]
                parser = datapath.ofproto_parser
                match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip)
                actions = [parser.OFPActionOutput(src_out_port)]
                self.add_flow(datapath, 1, match, actions)

        # Install flows for intermediate switches in the path
        for i in range(len(path) - 1):
            current_switch = path[i]
            next_switch = path[i + 1]
            out_port = self.network_graph[current_switch][next_switch]['out_port']
            if current_switch in self.datapaths:
                datapath = self.datapaths[current_switch]
                parser = datapath.ofproto_parser
                match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip)
                actions = [parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 1, match, actions)

        # Install flow for the last switch to the destination host
        if dst_switch and len(path) > 0:
            last_switch = path[-1]
            if last_switch in self.datapaths:
                datapath = self.datapaths[last_switch]
                parser = datapath.ofproto_parser
                match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip)
                actions = [parser.OFPActionOutput(dst_in_port)]
                self.add_flow(datapath, 1, match, actions)
controller.py
Displaying controller.py.
