################################################################################
# ciscoparser.py
################################################################################


import re


from cisxp import ciscoparserbase
from cisxp import device
from cisxp import iptools
from cisxp.objectsubparser import *


################################################################################


class CiscoParser(ciscoparserbase.CiscoParserBase):
    def __init__(self):
        super().__init__()
        self.device = device.Device()

    def parse(self, filename=None):
        if filename != None:
            self.open(filename)

        # maps tokens to parser methods
        token_map = [
            (('interface',),    self.parse_interface),
            (('name',),         self.parse_object),
            (('object',),       self.parse_object),
            (('object-group',), self.parse_object),
            (('nat',),          self.parse_nat),
            (('hostname',),     self.set_hostname),
        ]

        self.parse_map(token_map)
        return self.device

    def parse_interface(self):
        if self.indent != 0:
            return
        interface = self.get_or_add_interface()
        parser = InterfaceSubparser(self, interface)
        parser.parse()

    def parse_object(self):
        if self.indent != 0:
            return
        object = self.get_or_add_object()
        parser = ObjectSubparser(self, object)
        parser.parse()

    def parse_nat(self):
        if self.indent != 0:
            return
        parser = NATSubparser(self)
        nat = parser.parse()
        self.device.add_nat(nat)

    def set_hostname(self):
        self.device.hostname = self.token_at(1)

    # Returns an existing interface within device or creates a new one if one
    # does not already exist.
    def get_or_add_interface(self):
        interface = self.device.get_interface(self.token_at(1))
        interface_exists = interface != None
        if not interface_exists:
            interface = device.Interface()
            self.device.add_interface(interface)
        return interface

    # Returns an existing object within device or creates a new one if one
    # does not already exist.
    def get_or_add_object(self):
        object = self.device.get_object(self.get_object_name())
        object_exists = object != None
        if not object_exists:
            object = device.Object()
            self.device.add_object(object)
        return object

    # Returns an object name from current line.
    def get_object_name(self):
        if self.match('name'): return self.token_at(2)
        elif self.match('object'): return self.token_at(2)
        elif self.match('object-group'): return self.token_at(2)
        return None


################################################################################


class InterfaceSubparser():
    def __init__(self, parser, interface=None):
        self.parser = parser
        self.interface = interface
        if self.interface == None:
            self.interface = device.Interface()

    def parse(self):
        self.set_interface_name()
        self.parser.next()

        # stop parsing when text offset is 0
        stop = lambda: self.parser.indent == 0
        token_map = [
            (('description',),          self.set_description),
            (('ip', 'address', 'dhcp'), lambda: None),    # bypass dhcp
            (('ip', 'address'),         self.set_addr),
            (('nameif', ),              self.set_custom_name),
            (('hsrp', 'version'),       lambda: None),    # bypass hsrp version
            (('hsrp',),                 self.set_hsrp),
            (('vrf', 'member'),         self.set_vrf),
            (('vlan',),                 self.set_vlan),
        ]

        self.parser.parse_map(token_map, stop, True)
        return self.interface

    # Sets interface name.
    def set_interface_name(self):
        if self.parser.match('interface'):
            self.interface.name = self.parser.token_at(1)

    # Sets interface description.
    def set_description(self):
        self.interface.description = self.parser.join_tokens(1)

    # Regular expression to match interface ip address property.
    ip_address_re = re.compile(
        r'\s*ip\saddress\s+(?:{addr}(?:\s+{addr})?'
        r'(?:\s+standby\s+{addr})?'
        r'(?:\s+(secondary))?)\s*'
        .format(addr=iptools.addr_re.pattern)
    )
    # Adds an address to the interface.
    def set_addr(self):
        match = self.parser.re_match(self.ip_address_re)
        if match == None:
            return
        self.set_addr_from_match(*match.groups())

    # Adds an address to the interface from re match groups.
    def set_addr_from_match(self, addr1, cidr1, addr2, _cidr2, standby,
                            _standby_cidr, secondary):
        addr = device.Addr(addr1)
        if cidr1 != None:
            addr.cidr = int(cidr1)
        else:
            addr.cidr = iptools.mask_to_cidr(addr2)
        addr.standby = standby
        addr.secondary = secondary == 'secondary'
        self.interface.add_addr(addr)

    # Sets interface custom name.
    def set_custom_name(self):
        self.interface.custom_name = self.parser.join_tokens(1)

    # Sets interface hsrp group and hsrp addr.
    def set_hsrp(self):
        self.interface.hsrp_group = int(self.parser.token_at(1))
        self.parser.next()
        if self.parser.match('ip'):
            self.interface.hsrp_addr = self.parser.token_at(1)
        else:
            self.parser.putback()

    # Sets interface vrf.
    def set_vrf(self):
        self.interface.vrf = self.parser.join_tokens(2)

    # Sets interface vlan.
    def set_vlan(self):
        vlan_id = int(self.parser.token_at(1))
        vlan = device.VLAN(vlan_id)
        self.interface.vlan = vlan


################################################################################


class NATSubparser():
    def __init__(self, parser, nat=None):
        self.parser = parser
        self.nat = nat
        if self.nat == None:
            self.nat = device.NAT()

    # Regular expression to match manual nat configuration.
    man_nat_re = re.compile(
        r'\s*nat\s+\(({name}),\s*({name})\)\s+'
        r'(?:\s*(after-auto)\s*)?'
        r'source\s+(static|dynamic)\s+({name})\s+({name})'
        r'(?:\s+(interface))?'
        r'(?:\s+destination\s+(static)\s+({name})\s+({name}))?'
        r'(?:\s+service\s+({name})\s+({name}))?'
        r'(?:\s+(unidirectional))?'
        r'(?:\s+(no-proxy-arp))?'
        r'(?:\s+(route-lookup))?'
        .format(name=iptools.name_re.pattern)
    )
    def parse(self):
        match = self.parser.re_match(self.man_nat_re)
        if match == None:
            return
        self.set_nat_from_match(*match.groups())
        return self.nat

    def set_nat_from_match(self, inside_interface, outside_interface,
                           after_auto, src_type, inside_src, outside_src,
                           fallback, dest_type, inside_dest, outside_dest,
                           inside_service, outside_service, unidirectional,
                           no_proxy_arp, route_lookup):
        self.nat.inside_interface = self.get_nat_interface(inside_interface)
        self.nat.outside_interface = self.get_nat_interface(outside_interface)

        self.nat.src_type = src_type
        self.nat.inside_src = self.get_nat_addr(self.nat, None, inside_src)
        self.nat.outside_src = self.get_nat_addr(self.nat, None, outside_src)

        if dest_type != None:
            self.nat.dest_type = dest_type
            self.nat.inside_dest= self.get_nat_addr(self.nat, None, inside_dest)
            self.nat.outside_dest = \
                self.get_nat_addr(self.nat, None, outside_dest)

        self.nat.inside_service = self.get_nat_service(None, inside_service)
        self.nat.outside_service = self.get_nat_service(None, outside_service)

        self.nat.fallback = fallback == 'interface'
        self.nat.after_auto = after_auto == 'after-auto'
        self.nat.unidirectional = unidirectional == 'unidirectional'
        self.nat.no_proxy_arp = no_proxy_arp == 'no-proxy-arp'
        self.nat.route_lookup = route_lookup == 'route-lookup'

    # Returns an interface from the given interface name.
    def get_nat_interface(self, interface_name):
        if interface_name == 'any':
            return device.Interface.interface_any()
        interface = \
            self.parser.device.get_interface_by_custom_name(interface_name)
        if interface == None:
            interface = device.Interface(interface_name)
            self.parser.error(f'Interface "{interface_name}" not found.')
        return interface

    # Returns a new object from either addr or object name.
    def get_nat_addr(self, nat, addr, object_name):
        if addr != None:
            nat_addr = device.Object(addr=device.Addr(addr))
        elif object_name == 'interface':
            nat_addr = device.Object(nat.outside_interface.custom_name)
            nat_addr.addr = nat.outside_interface.primary_addr()
            if nat_addr.addr == None:
                self.parser.error(
                    f'Interface "{nat.outside_interface.custom_name}" '
                     'used in nat without primary address.'
                )
        elif object_name == 'any':
            nat_addr = device.Object('any')
            nat_addr.addr = device.Addr('0.0.0.0', 0)
        else:
            nat_addr = self.parser.device.get_object(object_name)
            if nat_addr == None:
                nat_addr = device.Object(object_name)
                self.parser.error(f'Network object "{object_name}" '
                                   'not found.')

        if nat_addr.type == None:
            nat_addr.type = device.ObjectType.NETWORK
        return nat_addr

    # Returns None if service_name == None or a new service Object with the
    # given service protocol and name.
    def get_nat_service(self, service_protocol, service_name):
        if service_name == None:
            return None
        service = self.parser.device.get_object(service_name)
        if service == None:
            service = device.Object()
            service.type = device.ObjectType.SERVICE
            service.protocol = service_protocol
            service.src_port = service_name
            if service_protocol == None:
                self.parser.error(f'Service object "{service_name}" not found.')
        return service


################################################################################
