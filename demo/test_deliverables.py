import json
import tempfile
import unittest
from pathlib import Path

import demo_real_cluster as cluster
import yaml


class DeliveryArtifactsTest(unittest.TestCase):
    def test_manifest_separates_canonical_and_runtime_ids(self):
        manifest = cluster.build_offering_manifest(
            {"offering_id": "runtime-offering", "spec_id": "runtime-spec"},
            "2026-08-11T00:00:00Z",
        )

        self.assertEqual(
            manifest["canonicalOffering"]["id"],
            "urn:dssc:service-offering:building-energy-hourly-v1",
        )
        self.assertEqual(manifest["deployment"]["productOfferingId"], "runtime-offering")
        self.assertEqual(manifest["deployment"]["productSpecificationId"], "runtime-spec")

    def test_writer_emits_utf8_json(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "artifact.json"
            cluster.write_json(output, {"provider": "能源数据提供方"})

            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8")),
                {"provider": "能源数据提供方"},
            )

    def test_profile_contains_no_secret_material(self):
        profile = cluster.build_provider_profile("2026-08-11T00:00:00Z", True)

        self.assertFalse(profile["containsSensitiveCredentials"])
        serialized = json.dumps(profile).lower()
        self.assertNotIn("password", serialized)
        self.assertNotIn("access_token", serialized)

    def test_real_cluster_openapi_describes_energy_delivery_fields(self):
        spec_path = cluster.DELIVERABLES_DIR / "openapi-scorpio.yaml"
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
        properties = spec["components"]["schemas"]["BuildingEntity"]["properties"]

        self.assertIn("datasetId", properties)
        self.assertIn("readings", properties)


if __name__ == "__main__":
    unittest.main()
