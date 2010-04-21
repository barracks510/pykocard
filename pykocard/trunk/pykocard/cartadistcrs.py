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

import serial # On Debian/Ubuntu : apt-get install python-serial

class CartadisTCRS :
    """A class to manage Cartadis TCRS vending card readers.

       Documentation was found in a Cartadis TCRS reader's paper manual.

       Cartadis is a registered trademark from Copie Monnaie France (C.M.F.)
    """
    def __init__(self, device, timeout=5.0, debug=False) :
        """Initializes the connection to the reader."""
        self.device = device
        self.timeout = timeout
        self.debug = debug

        self.lastcommand = None
        self.tcrsprompt = chr(13) + chr(10) + '$' # the prompt
        self.eoc = chr(13) # end of command

        # Each Cartadis vending card contain the following informations :
        #
        # the card can only be read on readers for which this group number
        # was specifically allowed.
        self.group = None
        # the number of credits on the card.
        self.value = None
        # the two following fields allow the card
        # to be assigned to a particular individual.
        # only plastic cards can use such attributes,
        # for throw-away cards, these values should both be set to 0
        self.department = None
        self.account = None
        # transaction number. Max 3000 for plastic cards, else 500.
        self.trnum = None

        # opens the connection to the reader
        self.tcrs = serial.Serial(device,
                                  baudrate=9600,
                                  bytesize=serial.EIGHTBITS,
                                  parity=serial.PARITY_NONE,
                                  stopbits=serial.STOPBITS_ONE,
                                  xonxoff=False,
                                  rtscts=True,
                                  timeout=timeout)

        # cleans up any data waiting to be read
        self.tcrs.flushInput()

    def __del__(self) :
        """Ensures the serial link is closed on deletion."""
        self.close()

    def close(self) :
        """Closes the serial link if it is open."""
        if self.tcrs is not None :
            self.tcrs.close()
            self.tcrs = None

    def logDebug(self, message) :
        """Logs a debug message."""
        if self.debug :
            sys.stderr.write("%s\n" % message)
            sys.stderr.flush()

    def sendCommand(self, cmd, param=None) :
        """Sends a command to the reader."""
        if param is not None :
            command = "%s %s%s" % (cmd, param, self.eoc)
        else :
            command = "%s%s" % (cmd, self.eoc)
        self.logDebug("Sending %s to reader" % repr(command))
        self.tcrs.write(command)
        self.tcrs.flush()
        self.lastcommand = command


