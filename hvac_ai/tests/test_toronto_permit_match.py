import unittest

from scripts.match_invoice_addresses_to_toronto_permits import (
    InvoiceLocation,
    PermitCandidate,
    equipment_hits,
    is_plausible_single_home_gfa,
    normalize_street_tokens,
    parse_invoice_address,
)


class AddressNormalizationTests(unittest.TestCase):
    def test_parses_unit_and_postal_code(self):
        street, city, postal, has_unit, exact, relaxed = parse_invoice_address(
            "10 Cardwell Avenue #2, Scarborough, ON M1S 4Z2 Canada"
        )
        self.assertEqual(street, "10 Cardwell Avenue #2")
        self.assertEqual(city, "SCARBOROUGH")
        self.assertEqual(postal, "M1S4Z2")
        self.assertTrue(has_unit)
        self.assertEqual(exact, "10|CARDWELL AVE")
        self.assertEqual(relaxed, "10|CARDWELL")

    def test_normalizes_saint_and_street_suffix(self):
        invoice = normalize_street_tokens("Saint Lawrence Street", relaxed=False)
        permit = normalize_street_tokens("ST LAWRENCE ST", relaxed=False)
        self.assertEqual(invoice, permit)


class EquipmentFilterTests(unittest.TestCase):
    def test_recognizes_furnace_and_central_ac_models(self):
        furnace, _ = equipment_hits(
            {
                "Item Name": "24X50",
                "Item Code": "EL297UH070XV36B",
                "Model on Invoice": "EL297UH070XV36B",
            }
        )
        ac, _ = equipment_hits(
            {
                "Item Name": "14J02/28X08",
                "Item Code": "ML14XC1S024-230",
                "Model on Invoice": "ML14XC1S024-230",
            }
        )
        self.assertEqual(furnace, {"furnace"})
        self.assertEqual(ac, {"air_conditioner"})

    def test_does_not_classify_heat_pump_only_model_as_ac(self):
        equipment, _ = equipment_hits(
            {
                "Item Name": "23A03",
                "Item Code": "EL17XP1-030",
                "Model on Invoice": "EL17XP1-030",
            }
        )
        self.assertEqual(equipment, set())

    def test_does_not_classify_bradford_white_water_heater_as_furnace(self):
        equipment, _ = equipment_hits(
            {
                "Item Name": "BRWRG1PV50S6N19457",
                "Item Code": "RG1PV50S6N-457",
                "Model on Invoice": "RG1PV50S6N-457",
            }
        )
        self.assertEqual(equipment, set())


class GfaClassificationTests(unittest.TestCase):
    def test_requires_new_detached_house_without_unit(self):
        location = InvoiceLocation(
            raw_address="1 Example Road, Toronto, ON M1M 1M1 Canada",
            street_line="1 Example Road",
            city="TORONTO",
            postal="M1M1M1",
            has_unit=False,
            exact_key="1|EXAMPLE RD",
            relaxed_key="1|EXAMPLE",
        )
        candidate = PermitCandidate(
            source="cleared",
            permit_num="1",
            revision_num="00",
            permit_type="Small Residential Projects",
            structure_type="SFD - Detached",
            work="New Building",
            postal="M1M",
            status="Closed",
            description="New house",
            current_use="",
            proposed_use="Single Family Dwelling",
            residential_sqm=200,
            match_method="exact_normalized_address",
        )
        self.assertTrue(is_plausible_single_home_gfa(location, candidate))
        location.has_unit = True
        self.assertFalse(is_plausible_single_home_gfa(location, candidate))


if __name__ == "__main__":
    unittest.main()
