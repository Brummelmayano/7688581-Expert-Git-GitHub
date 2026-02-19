from pathlib import Path
import sys
import tempfile

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app as kinapp



def test_products_with_stock():
    with tempfile.TemporaryDirectory() as tmp:
        kinapp.DB_PATH = Path(tmp) / 'test.db'
        kinapp.init_db()
        products = kinapp.products_with_stock()
        assert len(products) == 4
        assert all('stock' in p for p in products)


def test_checkout_consumes_code_and_creates_order():
    with tempfile.TemporaryDirectory() as tmp:
        kinapp.DB_PATH = Path(tmp) / 'test.db'
        kinapp.init_db()

        status, data = kinapp.process_checkout(
            {
                'buyer_name': 'Client Test',
                'buyer_email': 'client@example.com',
                'product_id': 'netflix',
                'payment_method': 'M-Pesa',
            }
        )
        assert status == 200
        assert 'order_reference' in data

        with kinapp.get_db_connection() as conn:
            used = conn.execute("SELECT COUNT(*) AS c FROM gift_codes WHERE product_id = 'netflix' AND is_used = 1").fetchone()['c']
            orders = conn.execute('SELECT COUNT(*) AS c FROM orders').fetchone()['c']

        assert used == 1
        assert orders == 1