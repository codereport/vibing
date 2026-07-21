import unittest

from scripts.fit_historical_install_formula import (
    decode_cooling_tons,
    decode_furnace_input_btu,
)


class CapacityDecoderTests(unittest.TestCase):
    def test_decodes_observed_cooling_families(self):
        self.assertEqual(decode_cooling_tons("ML14XC1S030-230"), 2.5)
        self.assertEqual(decode_cooling_tons("GLXS3BN3610"), 3.0)
        self.assertEqual(decode_cooling_tons("ALXS5BA6010"), 5.0)
        self.assertEqual(decode_cooling_tons("YCG24B21S"), 2.0)

    def test_decodes_observed_furnace_families(self):
        self.assertEqual(decode_furnace_input_btu("EL297UH070XV36B"), 70000)
        self.assertEqual(decode_furnace_input_btu("GRVT961005CN"), 100000)
        self.assertEqual(decode_furnace_input_btu("TM9Y080B12MP11"), 80000)

    def test_rejects_bradford_white_water_heater(self):
        self.assertIsNone(decode_furnace_input_btu("RG1PV50S6N-457"))


if __name__ == "__main__":
    unittest.main()
