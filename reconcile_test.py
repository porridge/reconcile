#!/usr/bin/python3
"""A program for reconciling ledger file with reality."""
# Copyright (C) 2023 Marcin Owsiany <marcin@owsiany.pl>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest

import reconcile

class TestRetrieveData(unittest.TestCase):

    def test_retrieve_data(self):
        curr, data, other = reconcile.retrieve_data("cat test_data/simple.dat")
        self.assertEqual(curr, 'PLN')
        self.assertEqual(data, {
            'Assets:Shop': 4103.72,
            'Assets:Bank2': 0,
            'Assets:Bank1:ROR': 294.65,
            'Assets:Cash:Car': 105.00,
            'Assets:Cash:Her': 304.00,
            'Assets:Cash:Him': 204.00,
            'Assets:Cash:Safe': 275.00,
            'Assets:Exchange': 200.00,
            'Assets:Bank3': 1701.59})
        self.assertEqual(other, [
            ('EUR', {'Assets:Cash:Safe': 123.88}),
            ('USD', {'Assets:Cash:Safe': 321.01,
                     'Assets:Exchange': 404.24})]
        )


if __name__ == '__main__':
    unittest.main()
