import unittest
from unittest.mock import MagicMock
from app.api.configure_lot import *


class TestConfigureLot(unittest.TestCase):
    def test_create_user(self):
        mock_db = MagicMock(spec=Session)
        client_name = "test_client_name"
        result = create_user(client_name, mock_db)
        self.assertEqual(result.status_code, 201)

    def test_generate_token(self):
        mock_db = MagicMock(spec=Session)
        result = generate_token('test_client_id', 'test_client_secret', 1, mock_db)
        self.assertEqual(result.status_code, 200)

    def test_check_lot_existence(self):
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=base.User)
        result = check_lot_existence(1, mock_user, mock_db)
        self.assertEqual(result.status_code, 200)

    def test_get_all_events(self):
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=base.User)
        result = get_all_events(mock_user, mock_db)
        self.assertEqual(result.status_code, 200)

    def test_get_providers(self):
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=base.User)
        result = get_providers(mock_user, mock_db)
        self.assertEqual(result.status_code, 200)

    def test_get_all_features(self):
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=base.User)
        result = get_all_features(mock_db, mock_user)
        self.assertEqual(result.status_code, 200)

    def provider_parkinglot_attach(self):
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=base.User)
        result = provider_parkinglot_attach(1, mock_user, mock_db)
        self.assertEqual(result.status_code, 200)

    def test_detach_feature_with_parkinglot(self):
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=base.User)
        result = detach_feature_with_parkinglot(1, 1, 1, mock_user, mock_db)
        self.assertEqual(result.status_code, 200)

    def test_detach_provider_with_parkinglot(self):
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=base.User)
        result = detach_provider_with_parkinglot(schema.DeleteConnection(deletions=[]), mock_user, mock_db)
        self.assertEqual(result.status_code, 200)
