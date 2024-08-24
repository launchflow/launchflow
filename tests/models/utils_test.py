import unittest

from launchflow.models.enums import DeploymentProduct, ResourceProduct
from launchflow.models.utils import (
    RESOURCE_PRODUCTS_TO_RESOURCES,
    SERVICE_PRODUCTS_TO_SERVICES,
)


class ModelUtilsTest(unittest.TestCase):
    def test_resource_product_to_resource_mapping(self):
        """Make sure that the resource product to resource mapping is comprehensive and correct."""

        self.assertEqual(
            set(RESOURCE_PRODUCTS_TO_RESOURCES.keys()), set(ResourceProduct)
        )

        for product, resource_cls in RESOURCE_PRODUCTS_TO_RESOURCES.items():
            self.assertEqual(product, resource_cls.product)

    def test_service_product_to_service_mapping(self):
        """Make sure that the service product to service mapping is comprehensive and correct."""

        self.assertEqual(
            set(SERVICE_PRODUCTS_TO_SERVICES.keys()), set(DeploymentProduct)
        )

        for product, service_cls in SERVICE_PRODUCTS_TO_SERVICES.items():
            self.assertEqual(product, service_cls.product)


if __name__ == "__main__":
    unittest.main()
