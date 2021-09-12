#!/usr/bin/env python
import unittest
from app import create_app, db
from app.models import *
from app.utils import *
from config import Config
from datetime import datetime

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'


class UserModelCase(unittest.TestCase):

    # Special method for enabling the Test Config
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    # Special method for stopping the Test Config
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_hashing(self):
        u = User(username='michael')
        u.set_password('doggo')
        self.assertFalse(u.check_password('cat'))
        self.assertTrue(u.check_password('doggo'))

    def test_avatar(self):
        u = User(username='michael', email='michael@example.com')
        self.assertEqual(u.avatar(128),
            ('https://www.gravatar.com/avatar/'
            '03ea78c0884c9ac0f73e6af7b9649e90'
            '?d=retro&s=128'))

    def test_full_name(self):
        u = User(first_name='Michael', last_name='Chaplin')
        self.assertEqual(u.full_name(), 'Michael Chaplin')
    
    def test_first_letter_last_name(self):
        u = User(first_name='Michael', last_name='Chaplin')
        self.assertEqual(u.first_letter_last_name(), 'M. Chaplin')


class TestEquipmentModel(unittest.TestCase):

    # Special method for enabling the Test Config
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    # Special method for stopping the Test Config
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_add_calibration_record(self):
        c = CalibrationRecord(id=1,
            calibration_date=datetime(2021, 4, 30),
            calibration_due_date=datetime(2022, 3, 25))
        t = TestEquipment(id=1, name="Oscilloscope")
        db.session.add_all([c, t])
        db.session.commit()
        self.assertEqual(t.calibration_records.all(), [])

        t.add_calibration_record(c)
        db.session.commit()
        self.assertEqual(t.calibration_records.count(), 1)

    def test_remove_calibration_record(self):
        c = CalibrationRecord(id=1,
            calibration_date=datetime(2021, 4, 30),
            calibration_due_date=datetime(2022, 3, 25))
        t = TestEquipment(id=1, name="Oscilloscope")
        db.session.add_all([c, t])
        db.session.commit()

        t.add_calibration_record(c)
        db.session.commit()
        self.assertEqual(t.calibration_records.count(), 1)

        t.remove_calibration_record(c)
        db.session.commit()
        self.assertEqual(t.calibration_records.all(), [])

    def test_due_date(self):
        c1 = CalibrationRecord(id=1,
            calibration_date=datetime(2021, 4, 30),
            calibration_due_date=datetime(2022, 3, 25))
        c2 = CalibrationRecord(id=2,
            calibration_date=datetime(2021, 6, 20),
            calibration_due_date=datetime(2022, 5, 12))
        t = TestEquipment(id=1, name="Oscilloscope")
        db.session.add_all([c1, c2, t])
        db.session.commit()

        t.add_calibration_record(c1)
        t.add_calibration_record(c2)
        db.session.commit()
        self.assertEqual(t.due_date(), datetime(2022, 5, 12))


class TestEquipmentTypeModel(unittest.TestCase):

    # Special method for enabling the Test Config
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    # Special method for stopping the Test Config
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_add_test_equipment(self):
        te = TestEquipment(id=1, name="Oscilloscope")
        t = TestEquipmentType(name="Oscilloscope")
        db.session.add_all([t, te])
        db.session.commit()

        t.add_test_equipment(te)
        db.session.commit()
        self.assertEqual(t.test_equipment.count(), 1)

    def test_remove_test_equipment(self):
        te = TestEquipment(id=1, name="Oscilloscope")
        t = TestEquipmentType(name="Oscilloscope")
        db.session.add_all([t, te])
        db.session.commit()

        t.add_test_equipment(te)
        db.session.commit()
        self.assertEqual(t.test_equipment.count(), 1)

        t.remove_test_equipment(te)
        db.session.commit()
        self.assertEqual(t.test_equipment.all(), [])

    def test_has_test_equipment(self):
        te = TestEquipment(id=1, name="Oscilloscope")
        t = TestEquipmentType(name="Oscilloscope")
        db.session.add_all([t, te])
        db.session.commit()

        t.add_test_equipment(te)
        db.session.commit()
        self.assertTrue(t.has_test_equipment(te))


class CompanyModel(unittest.TestCase):

    # Special method for enabling the Test Config
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    # Special method for stopping the Test Config
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_add_employee(self):
        u = User(username='michael', company_id=1)
        c = Company(name="MDS", category=CompanyCategory.SUPPLIER.value, id=1)
        db.session.add_all([u, c])
        db.session.commit()

        c.add_employee(u)
        db.session.commit()
        self.assertEqual(c.employees.count(), 1)



    
if __name__ == '__main__':
    unittest.main(verbosity=2)