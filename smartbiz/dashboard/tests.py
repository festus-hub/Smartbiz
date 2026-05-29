from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch
from django.db import OperationalError

from .models import Business, ContactMessage, Customer, Payment, Product, Sales, StockAlert, StockMovement, User


class RoleAccessTests(TestCase):
    def test_landing_contact_form_saves_message(self):
        response = self.client.post(
            reverse('landing'),
            {
                'name': 'Alice Sender',
                'email': 'alice@example.com',
                'subject': 'Need help',
                'message': 'Please show me how to get started.',
            },
        )

        self.assertRedirects(response, f"{reverse('landing')}#contact", fetch_redirect_response=False)
        message = ContactMessage.objects.get()
        self.assertEqual(message.name, 'Alice Sender')
        self.assertEqual(message.email, 'alice@example.com')
        self.assertEqual(message.subject, 'Need help')

    @patch('dashboard.views.ContactMessageForm.save', side_effect=OperationalError('no such table'))
    def test_landing_contact_form_handles_storage_failure(self, _mock_save):
        response = self.client.post(
            reverse('landing'),
            {
                'name': 'Alice Sender',
                'email': 'alice@example.com',
                'subject': 'Need help',
                'message': 'Please show me how to get started.',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, f"{reverse('landing')}#contact")
        self.assertContains(
            response,
            "Your message was received, but we could not store it in the local database right now.",
        )

    def test_registration_creates_business_owner_account(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'Alice Owner',
                'email': 'owner@example.com',
                'password': 'testpass123',
                'confirm_password': 'testpass123',
            },
        )

        self.assertRedirects(response, reverse('dashboard'))
        user = User.objects.get(username='owner@example.com')
        self.assertEqual(user.first_name, 'Alice Owner')
        self.assertEqual(user.role, User.BUSINESS_OWNER)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.id)

    def test_invalid_login_redirects_back_to_login(self):
        User.objects.create_user(
            username='owner@example.com',
            email='owner@example.com',
            password='testpass123',
            role=User.BUSINESS_OWNER,
        )

        response = self.client.post(
            reverse('login'),
            {
                'username': 'owner@example.com',
                'password': 'wrong-password',
            },
        )

        self.assertRedirects(response, reverse('login'))

    def test_employee_cannot_access_manager_only_report_page(self):
        user = User.objects.create_user(
            username='employee@example.com',
            email='employee@example.com',
            password='testpass123',
            role=User.EMPLOYEE,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('reports'))

        self.assertEqual(response.status_code, 403)

    def test_cashier_can_access_sales_page(self):
        user = User.objects.create_user(
            username='cashier@example.com',
            email='cashier@example.com',
            password='testpass123',
            role=User.CASHIER,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('sales'))

        self.assertEqual(response.status_code, 200)


class ApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='owner@example.com',
            email='owner@example.com',
            password='testpass123',
            role=User.BUSINESS_OWNER,
        )
        self.business = Business.objects.create(
            name='Owner Shop',
            owner=self.user,
        )
        self.customer = Customer.objects.create(
            name='Jane Customer',
            email='jane@example.com',
            phone='0712345678',
        )
        self.product = Product.objects.create(
            name='Phone',
            category='electronics',
            price='100.00',
            stock_quantity=5,
        )

    def test_register_api_creates_business_owner(self):
        response = self.client.post(
            reverse('api-register'),
            {
                'name': 'New Owner',
                'email': 'newowner@example.com',
                'password': 'securepass123',
                'confirm_password': 'securepass123',
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username='newowner@example.com').exists())

    def test_authenticated_user_can_list_products(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('api-product-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)

    def test_authenticated_user_can_create_sale(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('api-sale-list'),
            {
                'customer_id': self.customer.id,
                'product_id': self.product.id,
                'quantity': 2,
                'price': '100.00',
            },
        )

        self.assertEqual(response.status_code, 201)
        sale = Sales.objects.get()
        self.assertEqual(sale.customer, self.customer)
        self.assertEqual(sale.product, self.product)

    def test_payment_create_auto_generates_business_for_user(self):
        self.business.delete()
        self.client.force_login(self.user)
        sale = Sales.objects.create(
            customer=self.customer,
            product=self.product,
            quantity=1,
            price='100.00',
        )

        response = self.client.post(
            reverse('api-payment-list'),
            {
                'sale': sale.id,
                'amount': '100.00',
                'payment_method': 'cash',
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Business.objects.filter(owner=self.user).exists())
        payment = Payment.objects.get()
        self.assertEqual(payment.business.owner, self.user)

    @patch('dashboard.api_views.initiate_stk_push')
    def test_mpesa_payment_triggers_stk_push_and_stores_checkout_ids(self, mock_initiate_stk_push):
        self.client.force_login(self.user)
        sale = Sales.objects.create(
            customer=self.customer,
            product=self.product,
            quantity=1,
            price='100.00',
        )
        mock_initiate_stk_push.return_value = {
            'MerchantRequestID': 'merchant-123',
            'CheckoutRequestID': 'checkout-123',
            'ResponseCode': '0',
            'ResponseDescription': 'Success. Request accepted for processing',
            'CustomerMessage': 'Success',
        }

        response = self.client.post(
            reverse('api-payment-list'),
            {
                'sale': sale.id,
                'amount': '100.00',
                'payment_method': 'mpesa',
                'phone_number': '0712345678',
            },
        )

        self.assertEqual(response.status_code, 201)
        payment = Payment.objects.get()
        self.assertEqual(payment.business, self.business)
        self.assertEqual(payment.status, Payment.STATUS_PENDING)
        self.assertEqual(payment.checkout_request_id, 'checkout-123')
        self.assertEqual(payment.merchant_request_id, 'merchant-123')
        mock_initiate_stk_push.assert_called_once()

    def test_mpesa_callback_marks_payment_successful(self):
        payment = Payment.objects.create(
            sale=Sales.objects.create(
                customer=self.customer,
                product=self.product,
                quantity=1,
                price='100.00',
            ),
            business=self.business,
            amount='100.00',
            payment_method='mpesa',
            phone_number='254712345678',
            checkout_request_id='checkout-123',
            merchant_request_id='merchant-123',
            status=Payment.STATUS_PENDING,
        )

        response = self.client.post(
            reverse('api-mpesa-callback'),
            data={
                'Body': {
                    'stkCallback': {
                        'MerchantRequestID': 'merchant-123',
                        'CheckoutRequestID': 'checkout-123',
                        'ResultCode': 0,
                        'ResultDesc': 'The service request is processed successfully.',
                        'CallbackMetadata': {
                            'Item': [
                                {'Name': 'Amount', 'Value': 100},
                                {'Name': 'MpesaReceiptNumber', 'Value': 'RCP123456'},
                                {'Name': 'PhoneNumber', 'Value': 254712345678},
                            ]
                        },
                    }
                }
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_SUCCESS)
        self.assertEqual(payment.transaction_id, 'RCP123456')
        self.assertEqual(payment.result_code, '0')

    def test_dashboard_summary_requires_authentication(self):
        response = self.client.get(reverse('api-dashboard-summary'))

        self.assertEqual(response.status_code, 403)

    def test_low_stock_alerts_endpoint_returns_authenticated_results(self):
        self.client.force_login(self.user)
        StockAlert.objects.create(product=self.product, message='Phone is low on stock.')

        response = self.client.get(reverse('api-low-stock-alerts'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['product_name'], 'Phone')


class InventoryWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier@example.com',
            email='cashier@example.com',
            password='testpass123',
            role=User.CASHIER,
        )
        self.customer = Customer.objects.create(
            name='Jane Customer',
            email='jane2@example.com',
            phone='0712345678',
        )
        self.product = Product.objects.create(
            name='Router',
            category='electronics',
            price='2500.00',
            stock_quantity=6,
            low_stock_threshold=3,
        )

    def test_add_sale_creates_stock_out_movement_and_updates_inventory(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('add_sale'),
            {
                'customer_name': self.customer.name,
                'phone_number': self.customer.phone,
                'email': self.customer.email,
                'product': self.product.id,
                'quantity': 2,
                'price': '2500.00',
            },
        )

        self.assertRedirects(response, reverse('sales'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 4)
        movement = StockMovement.objects.get()
        self.assertEqual(movement.movement_type, StockMovement.MOVEMENT_OUT)

    def test_stock_movement_page_records_stock_in_and_creates_restock_alert(self):
        self.product.stock_quantity = 2
        self.product.save(update_fields=['stock_quantity'])
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('Stock_movement'),
            {
                'product': self.product.id,
                'movement_type': StockMovement.MOVEMENT_IN,
                'quantity': 3,
                'note': 'Supplier delivery',
            },
        )

        self.assertRedirects(response, reverse('Stock_movement'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertTrue(StockAlert.objects.filter(product=self.product, message__icontains='restocked').exists())

    def test_stock_movement_page_rejects_stock_out_above_available_quantity(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('Stock_movement'),
            {
                'product': self.product.id,
                'movement_type': StockMovement.MOVEMENT_OUT,
                'quantity': 20,
                'note': 'Bad request',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 6)
        self.assertEqual(StockMovement.objects.count(), 0)
