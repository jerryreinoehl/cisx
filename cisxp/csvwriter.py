################################################################################
# csvwriter.py
################################################################################


import sys


################################################################################


class CSVWriter():
    def __init__(self, file=sys.stdout):
        self.file = file     # output file
        self.cols = []       # column identifiers
        self.col_names = {}  # maps column identifiers to column display names
        self.row = {}        # maps column identifiers to column value
        self.rows = []       # list of rows

    # Must be implemented by subclass. Fills rows list with rows that map
    # column identifiers to values.
    def populate_rows(self):
        pass

    # Writes all headers and rows to file.
    def write(self):
        self.populate_rows()
        self.write_headers()
        self.write_rows()

    # Writes column names to file.
    def write_headers(self):
        self.write_row(self.col_names)

    # Writes all rows to file.
    def write_rows(self):
        for row in self.rows:
            self.write_row(row)

    # Writes a single row to file.
    def write_row(self, row):
        vals = []
        for col in self.cols:
            val = row.get(col, '')
            if val == None:
                val = ''
            vals.append(val)
        print(*vals, sep=',', file=self.file)


################################################################################
