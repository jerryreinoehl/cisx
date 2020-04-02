#!/usr/bin/env python3
################################################################################
# cisx.py
################################################################################


import getopt
import sys
import os


from cisxp import ciscoparser
from cisxp import natwriter


################################################################################


class CISX():
    import conf                            # import default values

    def __init__(self):
        self.opts = {
            'nat_file' : self.conf.NAT_CSV_FILE,
            'src_dir'  : self.conf.CONFIGURATION_DIRECTORY,
            'error_log' : self.conf.ERROR_LOG,
        }

    def run(self, args):
        self.get_opts(args)  # populate options dict
        if 'write_nat' in self.opts:
            self.write_nat()

    def print_usage(self):
        print(self.usage)

    def get_opts(self, args):
        shortopts = ''
        longopts = ['nat']
        while len(args) > 0:
            try:
                optlist, args = getopt.getopt(args[1:], shortopts, longopts)
            except getopt.GetoptError as err:
                print(err)
                self.print_usage()
                sys.exit(1)

            for opt, arg in optlist:
                self.set_opt(opt, arg)

            if len(args) > 0:
                if len(optlist) <= 0:
                    self.print_usage()
                    sys.exit(1)
                self.set_opt(optlist[-1][0], args[0])

    def set_opt(self, opt, arg):
        if opt == '--nat':
            self.opts['write_nat'] = True
            if arg != '':
                self.opts['nat_file'] = arg

    def write_nat(self):
        src_dir = self.opts['src_dir']
        files = os.listdir(src_dir)
        nat_file = open(self.opts['nat_file'], 'w')
        writer = natwriter.NATWriter(nat_file)
        writer.write_headers()
        errors = []

        for file in files:
            if file.startswith('.'):
                continue
            fullname = os.path.join(src_dir, file)
            try:
                parser = ciscoparser.CiscoParser()
                device = parser.parse(fullname)
                errors.extend(parser.errors)
                writer.write(device)
            except Exception as e:
                for error in errors:
                    print(error)
                parser.print_line()
                raise e

        nat_file.close()
        for error in errors:
            print(error)


################################################################################


if __name__ == '__main__':
    CISX().run(sys.argv)


################################################################################
