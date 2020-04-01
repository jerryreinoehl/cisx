################################################################################
# device.py
################################################################################


class Device():
    def __init__(self):
        self.hostname = None
        self.interfaces = []
        self.vlans = []
        self.vrfs = []
        self.objects = []
        self.nats = []

    # Adds an interface object to this device.
    def add_interface(self, interface):
        self.interfaces.append(interface)

    # Returns an existing interface object with the given name or None if it is
    # not found.
    def get_interface(self, name):
        if name == None: return None
        for interface in self.interfaces:
            if interface.name == name:
                return interface
        return None

    # Returns an existing interface object with the given custom name or None
    # if it is not found.
    def get_interface_by_custom_name(self, custom_name):
        if custom_name == None: return None
        for interface in self.interfaces:
            if interface.custom_name == custom_name:
                return interface
        return None

    # Adds an Object object to this device.
    def add_object(self, object):
        self.objects.append(object)

    # Returns an existing Object object with the given name or None if it is
    # not found.
    def get_object(self, name):
        if name == None: return None
        for object in self.objects:
            if object.name == name:
                return object
        return None

    # Adds a VLAN object to this device.
    def add_vlan(self, vlan):
        pass

    # Adds a VRF object to this device.
    def add_vrf(self, vrf):
        pass

    # Adds a NAT object to this device.
    def add_nat(self, nat):
        self.nats.append(nat)

################################################################################


class Interface():
    def __init__(self, name=None):
        self.name = None         # static name such as GigabitEthernet0/1
        self.custom_name = None  # custom name defined with nameif
        self.description = None
        self.addrs = []
        self.vrf = None
        self.vlan = None
        self.hsrp_group = None
        self.hsrp_addr = None

    def add_addr(self, addr):
        if addr not in self.addrs:
            self.addrs.append(addr)

    # Returns the first primary addr in addrs.
    def primary_addr(self):
        for addr in self.addrs:
            if not addr.secondary:
                return addr

    def interface_any():
        interface = Interface()
        interface.custom_name = 'any'
        interface.add_addr(Addr('0.0.0.0', 0))
        return interface

################################################################################


class Addr():
    def __init__(self, addr, cidr=32, type=4, standby=None, secondary=False):
        self.addr = addr            # str or Object
        self.cidr = cidr
        self.type = 4               # ipv4 or ipv6
        self.standby = standby      # standby address Addr()
        self.secondary = secondary

    def __eq__(self, other):
        if other == None:
            return False
        return (self.addr == other.addr
                and self.cidr == other.cidr
                and self.standby == other.standby
                and self.secondary == other.secondary)

    def __str__(self):
        if self.type == 4 and self.cidr == 32:
            return self.addr
        elif self.type == 6 and self.cidr == 64:
            return self.addr
        else:
            return f'{self.addr}/{self.cidr}'


################################################################################


class VLAN():
    def __init__(self, id=None, name=None):
        self.id = id
        self.name = name

    def __str__(self):
        return f'vlan {self.id} {self.name}'


################################################################################


class VRF():
    def __init__(self, name=None):
        self.name = name
        self.routes = []

    def add_route(self, route):
        self.routes.append(route)


################################################################################


class Route():
    def __init__(self):
        self.source = None
        self.addr = None
        self.next_hop = None
        self.time_stamp = None
        self.interface_name = None
        self.metric = None


################################################################################


class NAT():
    def __init__(self):
        # inside_interface and outside_interface are Interface objects or
        # the string 'any' to indicate the mapping on any interface.
        self.inside_interface = None   # Interface()
        self.outside_interface = None  # Interface()

        # after_auto is set to True if the keyword 'after-auto' present in
        # manual nat configuration line.
        self.after_auto = False
        self.src_type = None           # 'static' or 'dynamic'

        # inside_src is the address(es) that will map to the outside_src.
        # inside_src can be an Object or Addr object or the string 'any'.
        # 'any' indicates any inside address will be translated.
        self.inside_src = None         # Object()

        # outside_src is the address(es) the inside source address is mapped to
        # during translation. outside_src can be an Object or Addr object or
        # the strings 'interface' or 'any'. 'interface' indicates the
        # outside_src is the addr of the outside_interface. 'any' would indicate
        # a one-to-one mapping when used with src_type static and a destination
        # clause.
        self.outside_src = None        # Object()

        # fallback is True if the keyword 'interface' was given and was not
        # used to indicate the mapping of outside_src to outside_interface.
        self.fallback = False
        self.dest_type = None          # 'static' or 'dynamic'

        # Similar to inside_src, used to map destination address(es).
        self.inside_dest = None

        # Similar to outside_dest, used to map destination address(es).
        self.outside_dest = None
        self.service_protocol = None   # 'tcp' or 'udp' if service present

        # inside_service and outside_service represent the port translation
        # rules. They can be either an Object object of type SERVICE or a string
        # representing the service (such as 'ssh', 'https') or port
        # number (such as '22', '443').
        self.inside_service = None     # service Object()
        self.outside_service = None    # service Object()

        # no_proxy_arp is True if keyword 'no-proxy-arp' present in manual nat
        # configuration line.
        self.no_proxy_arp = False

        # route_lookup is True if keyword 'route-lookup' present in manual nat
        # configuration line.
        self.route_lookup = False


################################################################################


class ObjectType():
    NAME = 'name'
    NETWORK = 'network'
    SERVICE = 'service'
    NETWORK_GROUP = 'network group'
    SERVICE_GROUP = 'service group'


################################################################################


class Object():
    def __init__(self, name=None, type=None, description=None, addr=None):
        self.name = name
        self.type = type
        self.description = description
        self.addr = addr             # an Addr() or [Addr(), Addr()] for range
        # network object properties
        self.fqdn = None
        self.nat = None
        # service object properties
        self.protocol = None
        self.src_op = None
        self.src_port = None      # port number or list representing range
        self.dest_op = None
        self.dest_port = None
        # object group properties
        self.items = []

    def add_item(self, item):
        self.items.append(item)


################################################################################


class ObjectGroup(Object):
    def __init__(self):
        super().__init__()
        self._ObjectGroup__init__()

    def _ObjectGroup__init__(self):
        # items consists of all the items belonging to the object group.
        # If this is a network object group the items may be one of:
        #   Addr() representing either a host or subnet,
        #   [range_start, range_end],
        #   ( Object(), int():cidr ),
        #   str - 'any', ipv6
        #   Object(), or
        #   ObjectGroup().
        self.items = []

    def from_object(object):
        new_object = ObjectGroup()
        new_object.__dict__ = object.__dict__.copy()
        ObjectGroup._ObjectGroup__init__(new_object)
        return new_object



################################################################################
