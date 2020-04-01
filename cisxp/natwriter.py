################################################################################
# natwriter.py
################################################################################


import sys


from cisxp import device
from cisxp import csvwriter


################################################################################


class NATWriter(csvwriter.CSVWriter):
    def __init__(self, file=sys.stdout):
        super().__init__(file)

        # Column identifiers.
        self.cols = [
            'hostname',
            'object',
            'inside intf name',
            'inside intf addr',
            'mapped intf name',
            'mapped intf addr',
            'src type',
            'inside src name',
            'inside src addr',
            'mapped src name',
            'mapped src addr',
            'fallback addr',
            'dest type',
            'inside dest name',
            'inside dest addr',
            'mapped dest name',
            'mapped dest addr',
            'srv protocol',
            'inside srv name',
            'inside srv src port',
            'inside srv dest port',
            'mapped srv name',
            'mapped srv src port',
            'mapped srv dest port',
            'after auto',
            'no proxy arp',
            'route lookup',
        ]

        # Column names, maps column identifier to itself.
        self.col_names = {
            'hostname'              : 'Hostname',
            'object'                : 'Object Name',
            'inside intf name'      : 'Inside Intf Name',
            'inside intf addr'      : 'Inside Intf Addr',
            'mapped intf name'      : 'Mapped Intf Name',
            'mapped intf addr'      : 'Mapped Intf Addr',
            'src type'              : 'Src Type',
            'inside src name'       : 'Inside Src Name',
            'inside src addr'       : 'Inside Src Addr',
            'mapped src name'       : 'Mapped Src Name',
            'mapped src addr'       : 'Mapped Src Addr',
            'fallback addr'         : 'Fallback Addr',
            'dest type'             : 'Dest Type',
            'inside dest name'      : 'Inside Dest Name',
            'inside dest addr'      : 'Inside Dest Addr',
            'mapped dest name'      : 'Mapped Dest Name',
            'mapped dest addr'      : 'Mapped Dest Addr',
            'srv protocol'          : 'Srv Protocol',
            'inside srv name'       : 'Inside Srv Name',
            'inside srv src port'   : 'Inside Srv Src Port',
            'inside srv dest port'  : 'Inside Srv Dest Port',
            'mapped srv name'       : 'Mapped Srv Name',
            'mapped srv src port'   : 'Mapped Srv Src Port',
            'mapped srv dest port'  : 'Mapped Srv Dest Port',
            'after auto'            : 'After-Auto',
            'no proxy arp'          : 'No-Proxy-Arp',
            'route lookup'          : 'Route-Lookup',
        }

    def write(self, device):
        self.device = device
        self.rows = []
        self.populate_rows()
        self.write_rows()

    def populate_rows(self):
        self.fill_auto_nat_objects()

    def fill_auto_nat_objects(self):
        network_objects = [obj for obj in self.device.objects
                            if obj.nat != None]
        for object in network_objects:
            self.row = {}                        # reset row
            self.fill_auto_nat_object(object)     # add auto nat object
            self.rows.append(self.row)
        for nat in self.device.nats:
            self.row = {}
            self.row['hostname'] = self.device.hostname
            self.set_interface_cols(nat)
            self.rows.append(self.row)

    def fill_auto_nat_object(self, object):
        self.row['hostname'] = self.device.hostname
        self.row['object'] = object.name
        self.set_interface_cols(object.nat)

    def set_interface_cols(self, nat):
        self.row.update({
            'inside intf name' : self.get_interface_name(nat.inside_interface),
            'mapped intf name' : self.get_interface_name(nat.outside_interface),
            'inside intf addr' : self.get_interface_addr(nat.inside_interface),
            'mapped intf addr' : self.get_interface_addr(nat.outside_interface),
            'src type' : nat.src_type,
            'inside src name' : self.get_object_name(nat.inside_src),
            'mapped src name' : self.get_object_name(nat.outside_src),
            'inside src addr' : self.get_object_addr(nat.inside_src),
            'mapped src addr' : self.get_object_addr(nat.outside_src),
            'fallback addr' : self.get_fallback_addr(nat),
            'dest type' : nat.dest_type,
            'inside dest name' : self.get_object_name(nat.inside_dest),
            'mapped dest name' : self.get_object_name(nat.outside_dest),
            'inside dest addr' : self.get_object_addr(nat.inside_dest),
            'mapped dest addr' : self.get_object_addr(nat.outside_dest),
            'srv protocol' : self.get_service_protocol(nat),

            'inside srv name' : self.get_service_name(nat.inside_service),
            'inside srv src port' : self.get_src_port(nat.inside_service),
            'inside srv dest port' : self.get_dest_port(nat.inside_service),
            'mapped srv name' : self.get_service_name(nat.outside_service),
            'mapped srv src port' : self.get_src_port(nat.outside_service),
            'mapped srv dest port' : self.get_dest_port(nat.outside_service),

            'after auto' : self.get_boolean(nat.after_auto),
            'no proxy arp' : self.get_boolean(nat.no_proxy_arp),
            'route lookup' : self.get_boolean(nat.route_lookup),
        })

    # Returns an interface name string regardless of interface class type.
    def get_interface_name(self, interface):
        if isinstance(interface, device.Interface):
            return interface.custom_name
        else:
            return interface

    def get_object_name(self, object):
        if isinstance(object, device.Object):
            return object.name
        else:
            return object

    def get_service_name(self, service):
        if isinstance(service, device.Object):
            if service.type == device.ObjectType.SERVICE:
                return service.name

    def get_service_protocol(self, nat):
        if isinstance(nat, device.Object):
            if nat.type == device.ObjectType.SERVICE:
                return nat.protocol
        elif isinstance(nat.service_protocol, str):
            return nat.service_protocol
        elif nat.inside_service != None:
            return self.get_service_protocol(nat.inside_service)
        else:
            return nat.service_protocol

    def get_src_port(self, service):
        if isinstance(service, device.Object):
            return self.get_port(service.src_port)

    def get_dest_port(self, service):
        if isinstance(service, device.Object):
            return self.get_port(service.dest_port)

    def get_port(self, port):
        if isinstance(port, list):
            return f'{port[0]} - {port[1]}'
        else:
            return port

    def get_interface_addr(self, interface):
        if isinstance(interface, device.Interface):
            return self.get_addr(interface.primary_addr())
        else:
            return interface

    def get_object_addr(self, object):
        if isinstance(object, device.Object):
            if object.addr != None:
                return self.get_addr(object.addr)
            elif object.fqdn != None:
                return object.fqdn
        else:
            return object

    def get_fallback_addr(self, nat):
        if isinstance(nat, device.NAT):
            if nat.fallback:
                return self.get_interface_addr(nat.outside_interface)
        else:
            return nat

    def get_addr(self, addr):
        if isinstance(addr, device.Addr):
            return str(addr)
        elif isinstance(addr, list):
            return f'{self.get_addr(addr[0])} - {self.get_addr(addr[1])}'
        else:
            return addr

    def get_boolean(self, bool):
        return bool if bool == True else None


################################################################################
