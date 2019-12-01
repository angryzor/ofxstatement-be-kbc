from ofxstatement.plugin import Plugin
from ofxstatement.parser import CsvStatementParser
from ofxstatement.statement import StatementLine, BankAccount
from ofxstatement.exceptions import ParseError
import csv
import re


LINELENGTH = 18
HEADER_START = "Rekeningnummer"

class KbcBePlugin(Plugin):
    """Belgian KBC Bank plugin for ofxstatement
    """

    def get_parser(self, filename):
        f = open(filename, 'r')
        parser = KbcBeParser(f)
        return parser


class KbcBeParser(CsvStatementParser):

    date_format = "%d/%m/%Y"

    mappings = {
        'memo': 6,
        'date': 5,
        'amount': 8,
        'payee': 14,
    }

    line_nr = 0

    def parse_float(self, value):
        """Return a float from a string with ',' as decimal mark.
        """
        return float(value.replace(',','.'))

    def split_records(self):
        """Return iterable object consisting of a line per transaction
        """
        return csv.reader(self.fin, delimiter=';', skipinitialspace=True)

    def parse_record(self, line):
        """Parse given transaction line and return StatementLine object
        """
        self.line_nr += 1
        if line[0] == HEADER_START:
            return None
        elif len(line) != LINELENGTH:
            raise ParseError(self.line_nr,
                             'Wrong number of fields in line! ' +
                             'Found ' + str(len(line)) + ' fields ' +
                             'but should be ' + str(LINELENGTH) + '!')

        # Check the account id. Each line should be for the same account!
        if self.statement.account_id:
            if line[0] != self.statement.account_id:
                raise ParseError(self.line_nr,
                                 'AccountID does not match on all lines! ' +
                                 'Line has ' + line[0] + ' but file ' +
                                 'started with ' + self.statement.account_id)
        else:
            self.statement.account_id = line[0]

        # Check the currency. Each line should be for the same currency!
        if self.statement.currency:
            if line[3] != self.statement.currency:
                raise ParseError(self.line_nr,
                                 'Currency does not match on all lines! ' +
                                 'Line has ' + line[3] + ' but file ' +
                                 'started with ' + self.statement.currency)
        else:
            self.statement.currency = line[3]

        stmt_ln = super(KbcBeParser, self).parse_record(line)

        if line[12] != None and line[12] != '':
            stmt_ln.bank_account_to = BankAccount('', line[12])
        elif line[6].startswith('AUTOMATISCH SPAREN'):
            payee_match = re.match('AUTOMATISCH SPAREN\s+\d\d\-\d\d\s+(?:NAAR|VAN) (\w\w\d\d(?: \d{4}){3})', line[6])
            if payee_match == None:
                raise ParseError(self.line_nr,
                                 'Cannot parse savings info. (' + line[6] + ')')
            stmt_ln.bank_account_to = BankAccount('', payee_match.group(1))


        if stmt_ln.payee == None or stmt_ln.payee == '':
            if line[6].startswith('BETALING AANKOPEN VIA '):
                payee_match = re.match('BETALING AANKOPEN VIA (?:.+), (.+) MET KBC\-(?:BANK|DEBET)KAART', line[6])
                if payee_match == None:
                    raise ParseError(self.line_nr,
                                    'Cannot parse maestro/bancontact transaction info. (' + line[6] + ')')
                stmt_ln.payee = payee_match.group(1)
            elif line[6].startswith('AUTOMATISCH SPAREN'):
                payee_match = re.match('AUTOMATISCH SPAREN\s+\d\d\-\d\d\s+(?:NAAR|VAN) (\w\w\d\d(?: \d{4}){3})', line[6])
                if payee_match == None:
                    raise ParseError(self.line_nr,
                                    'Cannot parse savings info. (' + line[6] + ')')
                stmt_ln.payee = payee_match.group(1)

        return stmt_ln
