################################################################################
# ciscoparserbase.py
################################################################################


# Base cisco configuration parser provides basic methods and properties
# to open/close file, read lines, update line info, generate tokens, and
# perform error handling.
class CiscoParserBase():
    def __init__(self):
        self.line = None        # current line
        self.lines = []         # previous lines read
        self.lines_saved = 10   # number of previous lines to save in lines
        self.line_number = 0    # current line number
        self.lines_read = 0     # total number of lines read
        self.putback_lines = 0  # number of lines to read from saved lines
        self.tokens = None      # lines split by delimiter
        self.delim = None       # delim to split line, None is any whitespace
        self.indent = None      # col of first non-whitespace char in line
        self.errors = []        # list of parsing errors
        self.filename = None    # name of input file
        self.file = None        # input file
        self.eof = False        # indicates end of file found

    def __del__(self):
        self.close()

    # Opens given file for reading.
    def open(self, filename):
        self.file = open(filename, 'r')
        self.filename = filename

    # Closes file if it is open.
    def close(self):
        if self.file != None:
            self.file.close()

    # Reads the next line of the input file and updates all current data.
    # If putback is set to True the only change will be that putback is set
    # to False.
    def next(self):
        if self.putback_lines > 0:
            self.putback_lines -= 1
            self.line = self.lines[self.putback_lines]
            self.line_number = self.lines_read - self.putback_lines
        else:
            self.line = self.file.readline()
            self.update_lines(self.line)
            self.line_number = self.lines_read
        self.update()

    # Updates all properties from new line read.
    def update(self):
        self.tokens = self.tokenize(self.line)
        self.indent = self.get_indent(self.line)

    # Updates the list of previously saved lines.
    def update_lines(self, line):
        if self.line == '':        # empty string indicates EOF
            self.eof = True
            return
        self.line = self.line
        self.line = self.line.rstrip()
        self.lines_read += 1
        self.lines.insert(0, line)
        while len(self.lines) > self.lines_saved:
            self.lines.pop()

    # Returns the col number of the first non-whitespace char in given line.
    def get_indent(self, line):
        indent = 0
        for c in list(line):
            if c.isspace():
                indent += 1
            else:
                return indent

    # Returns a list of tokens derived from given line.
    def tokenize(self, line):
        return line.split(self.delim)

    # Backs parser up nlines lines. If putback_lines exceeds the total number
    # of lines saved a ValueError is raised.
    def putback(self, nlines=1):
        if self.putback_lines + nlines > len(self.lines):
            raise ValueError('putback lines greater than saved lines.')
        self.putback_lines += nlines

    # Appends an error message to the list of errors. Filename and current
    # line number are prefixed to the message.
    def error(self, msg):
        err = f'{self.filename}:{self.line_number}:\n{msg}\n{self.line}'
        self.errors.append(err)

    # Returns true if self.tokens begins with the given tokens.
    # An optional match function can be given to perform the match.
    # It should receive a variable number of args and return a bool.
    # i.e. match = lambda *args: True|False
    def match(self, *tokens, match=None):
        if match == None:
            return self.tokens[:len(tokens)] == list(tokens)
        else:
            return match(*tokens)

    # Returns an re match object if given pattern matches the current line and
    # None otherwise. If a mismatch occurs an error message is appended to
    # errors.
    def re_match(self, pattern):
        match = pattern.fullmatch(self.line)
        if match == None:
            self.error(f're mismatch: {pattern}')
        return match

    # Performs parsing with the given parse map and an optional stop function.
    # The parse map must be a list of 2-tuples where each tuple contains a
    # tuple of tokens to match and a function to call on the match. The stop
    # function is called on each read. When the stop function returns true
    # parsing will stop and return to caller.
    def parse_map(self, map, stop=None, putback=False, default=None):
        if stop == None:                 # default stop func never stops
            stop = lambda: False
        if self.line == None:
            self.next()
        match = False
        while not self.eof and not stop():
            for entry in map:
                if self.match(*entry[0]):
                    match = True
                    entry[1]()
                    break
            if default != None and match == False:  # call default if no match
                default()
            self.next()
        if putback:
            self.putback()

    # Performs parsing with the given parse map and an optional stop function.
    # The parse map must be a list of 2-tuples where each tuple contains a
    # tuple of tokens to match and a function to call on the match. The stop
    # function is called on the read. When the stop function returns true
    # parsing will stop and return to caller. Only reads one line.
    def parse_map_once(self, map, stop=None, putback=False):
        if stop == None:
            stop = lambda: False
        if self.line == None:
            self.next()
        if not self.eof and not stop():
            for entry in map:
                if self.match(*entry[0]):
                    entry[1]()
                    break
        if not putback:
            self.next()

    # Prints current line number and line.
    def print_line(self):
        print(f'{self.filename}:{self.line_number}: {self.line}')

    # Returns the token at the given index or None if index out of range of
    # tokens. If index is out of range an error message is appended to errors.
    def token_at(self, index):
        if index >= len(self.tokens):
            self.error('index out of range of tokens')
            return None
        else:
            return self.tokens[index]

    # Returns a string by joining the tokens from the given indices by the
    # given join character or None if any index is out of range. If any index
    # is out of range an error message is appended to errors.
    def join_tokens(self, start=0, end=None, chr=' '):
        if end == None:
            end = len(self.tokens)
        if start >= len(self.tokens) or end > len(self.tokens):
            self.error('indices out of range of tokens')
            return None
        else:
            return chr.join(self.tokens[start:end])

################################################################################
