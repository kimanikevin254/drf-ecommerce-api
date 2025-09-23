from django.test import TestCase
from decimal import Decimal

from catalog.models import Category, Product

class CategoryModelTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.root_category = Category.objects.create(name='Electronics')
        self.sub_category = Category.objects.create(
            name='Mobile Phones',
            parent=self.root_category
        )
        self.sub_sub_category = Category.objects.create(
            name='Smartphones',
            parent=self.sub_category
        )

    def test_category_str_representation(self):
        """Test category string representation"""
        self.assertEqual(str(self.root_category), 'Electronics')

    def test_get_full_path_root_category(self):
        """Test full path for root category"""
        self.assertEqual(self.root_category.get_full_path(), 'Electronics')

    def test_get_full_path_nested_category(self):
        """Test full path for nested category"""
        expected_path = 'Electronics > Mobile Phones > Smartphones'
        self.assertEqual(self.sub_sub_category.get_full_path(), expected_path)

    def test_get_all_children_with_nested_structure(self):
        """Test getting all children recursively"""
        children = self.root_category.get_all_children()
        
        self.assertEqual(len(children), 2)
        self.assertIn(self.sub_category, children)
        self.assertIn(self.sub_sub_category, children)

    def test_get_all_children_leaf_category(self):
        """Test getting children of leaf category"""
        children = self.sub_sub_category.get_all_children()
        self.assertEqual(len(children), 0)

class ProductModelTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            name='iPhone 15',
            description='Latest iPhone model',
            price=Decimal('999.99'),
            category=self.category,
            stock_quantity=10
        )

    def test_product_str_representation(self):
        """Test product string representation"""
        expected = 'iPhone 15 - $999.99'
        self.assertEqual(str(self.product), expected)

    def test_product_default_values(self):
        """Test product default field values"""
        self.assertTrue(self.product.is_active)
        self.assertIsNotNone(self.product.created_at)
        self.assertIsNotNone(self.product.updated_at)
