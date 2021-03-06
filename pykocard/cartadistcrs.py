# -*- coding: utf-8 -*-
#
# PyKoCard
#
# PyKoCard : Smart Card / Vending Card managing library
#
# (c) 2010 Jerome Alet <alet@librelogiciel.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# $Id$
#

import sys
import time

import serial # On Debian/Ubuntu : apt-get install python-serial

# Some constants : names are mine, not Cartadis.
#
# Write errors
NOERROR = 0
ERRWRITEERROR = -1
ERRNOCARD = -2
ERRCARDBLOCKED = -3
ERRUNKNOWNCARD = -4
ERRINVALID = -5
ERRMAXTRANSACTION = -6
ERRVALUETOOHIGH = -7
ERRGROUPNOTALLOWED = -8
ERRWRITEBEFOREREAD = -9
ERRREADBEFOREWRITE = -10
ERRCOMPARISON = -11
#
# Read errors
ERRREADERROR = -1
#
# Other errors
ERRILLEGALGROUP = -1
ERRNOTADMIN = -9
ERRLISTFULL = -10
ERRADMINNOTALLOWED = -11

# Sensor
SENSORNOCARD=0     # No card present
SENSORUNKNOWN1=1   # Partially inside the TCRS
SENSORCARDINSIDE=2 # Card is inside the TCRS
SENSORUNKNOWN3=3   # Partially inside the TCRS

# Waiting loop delay
WAITDELAY=1.0 # 1 second

class Terminal :
    """Base class for all terminals."""
    def __init__(self, device, timeout=1.0, debug=False) :
        """Must be implemented elsewhere."""
        raise NotImplementedError

    def __del__(self) :
        """Ensures the serial link is closed on deletion."""
        self.close()

    def logError(self, message) :
        """Logs an error message."""
        sys.stderr.write("%s\n" % message)
        sys.stderr.flush()

    def logDebug(self, message) :
        """Logs a debug message."""
        if self.debug :
            self.logError(message)

class CartadisTCRS(Terminal) :
    """A class to manage Cartadis TCRS vending card readers.

       Documentation was found in a Cartadis TCRS reader's paper manual.

       Cartadis is a registered trademark from Copie Monnaie France (C.M.F.)
    """
    def __init__(self, device, timeout=1.0, debug=False) :
        """Initializes the connection to the TCRS."""
        self.device = device
        self.timeout = timeout
        self.debug = debug

        self.debitCardTypes = (3, 5, 6, 7) # TODO : define some constants for these card types

        self.lastcommand = None
        self.shortprompt = '$'
        self.sol = chr(13) + chr(10) # start of line (begins each answer)
        self.sollen = len(self.sol)
        self.prompt = chr(13) + chr(10) + self.shortprompt # the prompt
        self.promptlen = len(self.prompt)
        self.eoc = chr(13) # end of command

        # Each Cartadis vending card contain the following informations :
        self.cardcontent = { "group" : None, # the card can only be read on a TCRS for which this group number was specifically allowed.
                             "value" : None, # the number of credits on the card.
                             "department" : None, # these two fields can be used to identify the owner of the card
                             "account" : None,
                             "trnum" : None  # Transaction number : Max 3000 for plastic cars, else 500.
                           }

        # opens the connection to the TCRS
        self.tcrs = serial.Serial(device,
                                  baudrate=9600,
                                  bytesize=serial.EIGHTBITS,
                                  parity=serial.PARITY_NONE,
                                  stopbits=serial.STOPBITS_ONE,
                                  xonxoff=False,
                                  rtscts=True,
                                  timeout=timeout)

        # cleans up any data waiting to be read or written
        try :
            self.tcrs.flushInput()
            self.tcrs.flushOutput()
        except serial.serialutil.SerialException, msg :
            self.logError(msg)
            self.close()
        else :
            # Identifies the terminal
            self.versionNumber = self.version()
            self.serialNumber = self.serial()
            self.logDebug("%s TCRS detected on device %s with serial number %s" \
                              % (self.versionNumber,
                                 self.device,
                                 self.serialNumber))

    def _sendCommand(self, cmd, param=None) :
        """Sends a command to the TCRS."""
        if self.tcrs is not None :
            if param is not None :
                command = "%s %s%s" % (cmd, param, self.eoc)
            else :
                command = "%s%s" % (cmd, self.eoc)
            self.logDebug("Sending %s to TCRS" % repr(command))
            self.tcrs.write(command)
            self.tcrs.flush()
            self.lastcommand = command
            #
            # IMPORTANT : the following code doesn't work because currently
            # PySerial doesn't allow an EOL marker to be several chars long.
            # I've just sent a patch for this to PySerial's author, and we'll
            # see what happens. If not accepted, I'll write it another way.
            answer = self.tcrs.readline(eol=self.prompt)
            self.logDebug("TCRS answered %s" % repr(answer))
            if answer.startswith(self.shortprompt) :
                answer = answer[len(self.shortprompt):]
            if answer.startswith(command) :
                answer = answer[len(command):]
            if answer.startswith(self.sol) and answer.endswith(self.prompt) :
                return answer[self.sollen:-self.promptlen]
            else :
                if answer and (answer != self.sol) :
                    self.logError("Unknown answer %s" % repr(answer))
                return None
        else :
            self.logError("Device %s is not open" % self.device)

    # Device specific calls
    def help(self) :
        """Returns the list of commands supported by the TCRS."""
        return self._sendCommand("help")

    def version(self) :
        """Returns the TCRS' version string."""
        return self._sendCommand("version")

    def serial(self) :
        """Returns the TCRS' serial number.'"""
        return self._sendCommand("serial")

    def read(self) :
        """Reads the card's content to the TCRS. Returns the type of card or an error value."""
        return int(self._sendCommand("read") or -1)

    def write(self) :
        """Writes the TCRS values to the card. Returns 0 or error value."""
        return int(self._sendCommand("write"))

    def sensor(self) :
        """Returns 0 if there's no card in TCRS, else 1, 2 or 3."""
        return int(self._sendCommand("sensor"))

    def eject(self) :
        """Ejects the card from the TCRS."""
        return self._sendCommand("eject")

    def trnum(self) :
        """Returns the number of transactions made with this card."""
        return int(self._sendCommand("trnum"))

    def value(self, value=None) :
        """Returns the last value read, or sets the new value of the card, but doesn't write it to the card yet."""
        if value is None :
            return int(self._sendCommand("value"))
        else :
            return self._sendCommand("value", str(value))

    def account(self, account=None) :
        """Returns the last account number read, or sets the account number, but doesn't write it to the card yet.'"""
        if account is None :
            return int(self._sendCommand("account"))
        else :
            return self._sendCommand("account", str(account))

    def department(self, department=None) :
        """Returns the last department number read, or sets the department number, but doesn't write it to the card yet.'"""
        if department is None :
            return int(self._sendCommand("department"))
        else :
            return self._sendCommand("department", str(department))

    def group(self, group=None) :
        """Returns the last group number read, or sets the group number, but doesn't write it to the card yet.'"""
        if group is None :
            return int(self._sendCommand("group"))
        else :
            return self._sendCommand("group", str(group))

    def addgrp(self, group=None) :
        """Adds the group to the list of allowed ones. If no group, the one on the admin card is used."""
        return int(self._sendCommand("addgrp", str(group)))

    def listgrp(self) :
        """Returns the list of allowed group numbers."""
        return [int(g) for g in self._sendCommand("listgrp").split()]

    def delgrp(self, group) :
        """Deletes the group from the list of allowed groups."""
        return int(self._sendCommand("delgrp", str(group)))

    def cardtype(self, cardtype=None) :
        """Returns the type of card, or sets it (not clear in the doc if a write call is needed or not)."""
        # TODO : doesn't seem to return a meaningful answer
        if cardtype is None :
            answer = self._sendCommand("cardtype")
        else :
            answer = self._sendCommand("cardtype", str(cardtype))
        try :
            return int(answer)
        except ValueError :
            self.logError("Unknown card type %s" % repr(answer))
            return None

    def display(self, text) :
        """Displays a string of text on the TCRS' screen."""
        return self._sendCommand("display", text)

    def echo(self, echo) :
        """Changes the type of echo for the TCRS' keyboard."""
        raise NotImplementedError

    def key(self, key) :
        """Not really clear what it does..."""
        raise NotImplementedError

    def getstr(self) :
        """Returns a string from keyboard or -1 if buffer is empty."""
        raise NotImplementedError

    def getkey(self) :
        """Returns the value of the key pressed, or -1 if no key was hit."""
        raise NotImplementedError

    def prompt1(self, prompt1) :
        """Changes the 'Introduce card' message."""
        raise NotImplementedError

    def prompt2(self, prompt2) :
        """Changes the 'Credit:' message."""
        raise NotImplementedError

    def prompt3(self, prompt3) :
        """Changes the text displayed after the value of the card (e.g. 'EURO')."""
        raise NotImplementedError

    # Public API
    def close(self) :
        """Closes the serial link if it is open."""
        if self.tcrs is not None :
            self.logDebug("Closing serial link...")
            self.tcrs.close()
            self.tcrs = None
            self.logDebug("Serial link closed.")

    def waitForCard(self) :
        """Waits for the card to be inserted into the terminal."""
        while tcrs.sensor() != SENSORCARDINSIDE :
            time.sleep(WAITDELAY)

class CreditCard :
    """A class for cards."""
    def __init__(self, terminal) :
        """Initializes a card present in the terminal."""
        self.terminal = terminal
        self.value = None
        terminal.waitForCard()
        if terminal.read() in terminal.debitCardTypes :
            self.value = terminal.value()

    def releaseCard(self) :
        """Ejects the card from the terminal."""
        result = self.terminal.eject()
        self.value = None
        return result

    def __int__(self) :
        """Returns the number of credits on the card as an integer."""
        return int(self.value)

    def __float__(self) :
        """Returns the number of credits on the card as a float."""
        return float(self.value)

    def __iadd__(self, other) :
        """Increases the number of credits on a card with 'card += amount'."""
        newvalue = self.value + other
        writtenvalue = self.terminal.value(newvalue)
        if writtenvalue == newvalue :
            if self.terminal.write() == NOERROR :
                # TODO : should we return 'writtenvalue' or read from the card again to be sure ?
                # Is another read() call needed before ? TODO : check this again with the real card reader.
                self.value = self.terminal.value()
                return self.value
        raise ValueError, "Unable to read or write the card"

    def __isub__(self, other) :
        """Decreases the number of credits on a card with 'card -= amount'."""
        newvalue = self.value - other
        writtenvalue = self.terminal.value(newvalue)
        if writtenvalue == newvalue :
            if self.terminal.write() == NOERROR :
                # TODO : should we return 'writtenvalue' or read from the card again to be sure ?
                # Is another read() call needed before ? TODO : check this again with the real card reader.
                self.value = self.terminal.value()
                return self.value
        raise ValueError, "Unable to read or write the card"

if __name__ == "__main__" :
    # Minimal testing
    tcrs = CartadisTCRS("/dev/ttyS0", debug=True)
    try :
        sys.stdout.write("%s TCRS detected on device %s with serial number %s\n" \
                              % (tcrs.versionNumber,
                                 tcrs.device,
                                 tcrs.serialNumber))


        sys.stdout.write("This Cartadis TCRS supports the following commands :\n%s\n" % tcrs.help())
        sys.stdout.write("Allowed groups : %s\n" % tcrs.listgrp())

        sys.stdout.write("Please insert your card into the TCRS...")
        sys.stdout.flush()
        tcrs.waitForCard()
        sys.stdout.write("\n")

        sys.stdout.write("Card read status : %s\n" % tcrs.read())
        sys.stdout.write("Group : %s\n" % tcrs.group())
        value = tcrs.value()
        tcrs.display("Card has %s credits" % value)
        sys.stdout.write("Card has %s credits\n" % value)
        sys.stdout.write("Department : %s\n" % tcrs.department())
        sys.stdout.write("Account : %s\n" % tcrs.account())
        sys.stdout.write("Transaction # : %s\n" % tcrs.trnum())
        #
        # This block commented out because I don't have many credits for testing ;-)
        # It seems to work anyway.
        # Now we decrement the number of credits
        #tcrs.value(value-1)
        # And we flush the card's content to the card
        #sys.stdout.write("Card write status : %s\n" % tcrs.write())
        # Now we read it back
        #tcrs.read()
        #sys.stdout.write("Card now has %s credits\n" % tcrs.value())
        #
        tcrs.eject()
        #
        # And now some higher level API
        creditcard = CreditCard(tcrs) # Waits until card is inserted
        creditcard += 5 # This one will fail with my terminal, but won't consume my credits :-)
        # creditcard -= 1 # This one would work with my terminal, but would consume my credits :-)
        creditcard.release()
    finally :
        tcrs.close()
