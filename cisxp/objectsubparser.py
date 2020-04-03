################################################################################
# objectsubparser.py
################################################################################

import re


from cisxp import device
from cisxp import iptools


################################################################################


class ObjectSubparser():
    def __init__(self, parser, object):
        self.parser = parser
        self.object = object
        if self.object == None:
            self.object = device.Object()

    def parse(self):
        stop = lambda: self.parser.indent > 0
        token_map = [
            (('name',),                   self.parse_name_object),
            (('object', 'network'),       self.parse_network_object),
            (('object', 'service'),       self.parse_service_object),
            (('object-group', 'network'), self.parse_network_object_group),
        ]
        self.parser.parse_map_once(token_map, stop, True)
        return self.object

    # Regular expression to match name object line.
    name_object_re = re.compile(
        r'\s*name\s+{addr}\s+({name})(?:\s+description\s+(.+))?\s*'
        .format(addr=iptools.addr_re.pattern, name=iptools.name_re.pattern)
    )
    def parse_name_object(self):
        self.object.type = device.ObjectType.NAME
        match = self.parser.re_match(self.name_object_re)
        if match == None:
            return
        self.name_object_from_match(*match.groups())

    # Sets name object properties from re match group
    def name_object_from_match(self, addr, _cidr, name, description):
        self.object.addr = device.Addr(addr)
        self.object.name = name
        if description != None:
            self.object.description = description

    # Parser object with network object subparser.
    def parse_network_object(self):
        parser = NetworkObjectSubparser(self.parser, self.object)
        parser.parse()

    def parse_service_object(self):
        parser = ServiceObjectSubparser(self.parser, self.object)
        parser.parse()

    def parse_network_object_group(self):
        parser = NetworkObjectGroupSubparser(self.parser, self.object)
        parser.parse()


################################################################################


class NetworkObjectSubparser():
    def __init__(self, parser, object=None):
        self.parser = parser
        self.object = object
        if self.object == None:
            self.object = device.Object()

    def parse(self):
        self.object.type = device.ObjectType.NETWORK
        self.object.name = self.parser.token_at(2)
        stop = lambda: self.parser.indent == 0
        token_map = [
            (('host',),        self.set_host),
            (('subnet',),      self.set_subnet),
            (('range',),       self.set_range),
            (('fqdn',),        self.set_fqdn),
            (('nat',),         self.set_nat),
            (('description',), self.set_description),
        ]
        self.parser.next()
        self.parser.parse_map(token_map, stop, True)
        return self.object

    # Sets network object addr.
    def set_host(self):
        self.object.addr = device.Addr(self.parser.token_at(1))

    # Regular expression to match network object subnet property.
    network_subnet_re = re.compile(
        r'\s*subnet\s+{addr}(?:\s+{addr})?\s*'
        .format(addr=iptools.addr_re.pattern)
    )
    # Sets network object addr.
    def set_subnet(self):
        match = self.parser.re_match(self.network_subnet_re)
        if match == None:
            return
        self.set_subnet_from_match(*match.groups())

    # Sets network object addr from subnet line re match.
    def set_subnet_from_match(self, addr1, cidr1, addr2, _cidr2):
        self.object.addr = device.Addr(addr1)
        if cidr1 != None:
            self.object.addr.cidr = int(cidr1)
        else:
            self.object.addr.cidr = iptools.mask_to_cidr(addr2)

    # Regular expression to match network object range property.
    network_range_re = re.compile(
        r'\s*range\s+{addr}\s+{addr}'.format(addr=iptools.addr_re.pattern)
    )
    # Sets network object range property.
    def set_range(self):
        match = self.parser.re_match(self.network_range_re)
        if match == None:
            return
        self.set_range_from_match(*match.groups())

    # Sets network object range property from network range re match.
    def set_range_from_match(self, addr1, _cidr1, addr2, _cidr2):
        self.object.addr = [device.Addr(addr1), device.Addr(addr2)]

    # Sets network object fqdn property.
    def set_fqdn(self):
        self.object.fqdn = self.parser.token_at(1)

    # Regular expression to match auto nat property.
    auto_nat_re = re.compile(
        r'\s*nat\s+\(({name}),\s*({name})\)\s+'
        r'(static|dynamic)\s+(?:(?:{addr})|({name}))'
        r'(?:\s+(interface))?'
        r'(?:\s+service\s+(tcp|udp)\s+({name})\s+({name}))?'
        r'(?:\s+(dns))?\s*'
        .format(name=iptools.name_re.pattern, addr=iptools.addr_re.pattern)
    )
    # Sets network object nat property.
    def set_nat(self):
        match = self.parser.re_match(self.auto_nat_re)
        if match == None:
            return
        self.set_nat_from_match(*match.groups())

    # Sets network object nat property from auto nat re match.
    def set_nat_from_match(self, inside_interface, outside_interface, src_type,
                           addr, _cidr, object_name, fallback, service_protocol,
                           inside_service, outside_service, _dns):
        nat = device.NAT()
        self.object.nat = nat
        nat.inside_interface = self.get_nat_interface(inside_interface)
        nat.outside_interface = self.get_nat_interface(outside_interface)

        nat.inside_src = self.object
        nat.outside_src = self.get_nat_addr(nat, addr, object_name)

        nat.src_type = src_type

        nat.fallback = fallback == 'interface'
        nat.service_protocol = service_protocol
        nat.inside_service = \
            self.get_nat_service(service_protocol, inside_service)
        nat.outside_service = \
            self.get_nat_service(service_protocol, outside_service)

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

    # Sets network object description property.
    def set_description(self):
        self.object.description = self.parser.join_tokens(1)


################################################################################


class ServiceObjectSubparser():
    def __init__(self, parser, object=None):
        self.parser = parser
        self.object = object
        if self.object == None:
            self.object = device.Object()

    def parse(self):
        self.object.type = device.ObjectType.SERVICE
        self.object.name = self.parser.token_at(2)
        stop = lambda: self.parser.indent == 0
        token_map = [
            (('service', ),    self.set_service),
            (('description',), self.set_description),
        ]
        self.parser.next()
        self.parser.parse_map(token_map, stop, True)
        return self.object

    # Regular expression to match service properties.
    service_re = re.compile(
        r'\s*service\s+(tcp|udp)'
        r'(?:\s+source\s+([A-Za-z]+)\s+({name})(?:\s+({name}))?)?'
        r'(?:\s+destination\s+([A-Za-z]+)\s+({name})(?:\s+({name}))?)?\s*'
        .format(name=iptools.name_re.pattern)
    )
    # Sets service properties
    def set_service(self):
        match = self.parser.re_match(self.service_re)
        if match == None:
            return
        self.set_service_from_match(*match.groups())

    # Sets service object properties from service re match.
    def set_service_from_match(self, protocol, src_op, src_port, src_end,
                               dest_op, dest_port, dest_end):
        self.object.protocol = protocol
        if src_op == 'range':
            self.object.src_op = src_op
            self.object.src_port = [src_port, src_end]
        elif src_op != None:
            self.object.src_op = src_op
            self.object.src_port = src_port

        if dest_op == 'range':
            self.object.dest_op = dest_op
            self.object.dest_port = [dest_port, dest_end]
        elif dest_op != None:
            self.object.dest_op = dest_op
            self.object.dest_port = dest_port

    # Sets service object description property.
    def set_description(self):
        self.object.description = self.parser.join_tokens(1)


################################################################################


class NetworkObjectGroupSubparser():
    def __init__(self, parser, object=None):
        self.parser = parser
        self.object = object
        if self.object == None:
            self.object = device.Object

    def parse(self):
        self.object.type = device.ObjectType.NETWORK_GROUP
        self.object.name = self.parser.token_at(2)

        stop = lambda: self.parser.indent == 0
        token_map = [
            (('network-object', 'host'),   self.add_host),
            (('network-object', 'object'), self.add_object),
            (('network-object',),          self.add_subnet),
            (('group-object',),            self.add_group_object),
            (('description',),             self.set_description),
            # range
            # any
        ]
        self.parser.next()
        self.parser.parse_map(token_map, stop, True)
        return self.object

    # Regular expression to match network-object host property.
    host_re = re.compile(
        r'\s*network-object\s+host\s+(?:(?:{addr})|(?:{addr6})|({name}))'
        .format(addr=iptools.addr_re.pattern, addr6=iptools.addr6_re.pattern,
                name=iptools.name_re.pattern)
    )
    # Adds a host item to network object group.
    def add_host(self):
        match = self.parser.re_match(self.host_re)
        if match == None:
            return
        self.add_host_from_match(*match.groups())

    def add_host_from_match(self, addr, _cidr, addr6, _cidr6, name):
        cidr = 32
        type = 4
        if addr != None:
            address = addr
        elif addr6 != None:
            address = addr6
            cidr = 128
            type = 6
        else:
            address = self.parser.device.get_object(name)
            if address == None:
                address = name
        self.object.add_item(device.Addr(address, cidr, 6))

    # Adds an object item to network object group.
    def add_object(self):
        object_name = self.parser.token_at(2)
        object = self.parser.device.get_object(object_name)
        if object == None:
            object = object_name
        self.object.add_item(object)

    # Regular expression to match network-object subnet property.
    subnet_re = re.compile(
        r'\s*network-object\s+(?:(?:(?:(?:{addr})|({name}))\s+(?:{addr}))|'
        r'(?:{addr6}))\s*'
        .format(addr=iptools.addr_re.pattern, addr6=iptools.addr6_re.pattern,
                name=iptools.name_re.pattern)
    )
    # Adds a subnet item to network object group.
    def add_subnet(self):
        match = self.parser.re_match(self.subnet_re)
        if match == None:
            return
        self.add_subnet_from_match(*match.groups())

    # Adds a subnet item to network object group from subnet re match.
    def add_subnet_from_match(self, addr1, cidr1, name, addr2, _cidr2, addr6_1,
                              cidr6):
        if addr2 != None:                      # set cidr
            cidr = iptools.mask_to_cidr(addr2)
            type = 4
        else:
            cidr = cidr6
            type = 6

        if addr1 != None:                      # set addr
            addr = addr1
        elif addr6_1 != None:
            addr = addr6_1
        else:
            addr = self.parser.device.get_object(name)
            if addr == None:
                addr = name
        self.object.add_item(device.Addr(addr, cidr, type))

    # Adds a group object item to network object group.
    def add_group_object(self):
        object_name = self.parser.token_at(1)
        object = self.parser.device.get_object(object_name)
        if object == None:
            object = object_name
        self.object.add_item(object)

    # Sets network object group description.
    def set_description(self):
        self.object.description = self.parser.join_tokens(1)


################################################################################
