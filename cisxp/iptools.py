################################################################################
# iptools.py
################################################################################


import re


# Regular expression to match an ip address with an optional cidr.
addr_re = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:/(\d{1,2}))?')

addr6_re = re.compile(r'([0-9A-Fa-f:]+)(?:/(\d{1,2}))?')

# Regular expression to match object name.
name_re = re.compile(r'[-A-Za-z0-9_.+()]+')

# Returns the cidr prefix equivalent of the given subnet mask.
def mask_to_cidr(mask):
    bytes = mask.split('.')               # separate each byte
    bytes = [int(byte) for byte in bytes] # and convert each to int
    addr = (bytes[0] << 24) + (bytes[1] << 16) + (bytes[2] << 8) + bytes[3]
    cidr = 0
    # calculate the number of leading 1 bits
    while (addr & 0x80000000) == 0x80000000:
        cidr += 1
        addr = (addr << 1) & 0xffffffff
    return cidr
