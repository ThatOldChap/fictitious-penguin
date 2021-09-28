#!/usr/bin/env python
from app.main.routes import test_equipment
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
    
    def test_update_calibration_records(self):
        c = CalibrationRecord(
            calibration_date=datetime(2021, 4, 30),
            calibration_due_date=datetime(2022, 3, 25))
        t = TestEquipment(name="Oscilloscope")
        db.session.add_all([c, t])
        db.session.commit()

        # Check that a CalibrationRecord can be added and checked if it exists
        t.add_calibration_record(c)
        db.session.commit()
        self.assertTrue(t.has_calibration_record(c))

        # Check to make sure that duplicate CalibrationRecords can't be added
        t.add_calibration_record(c)
        db.session.commit()
        self.assertEqual(t.calibration_records.count(), 1)

        # Check to make sure a CalibrationRecord can be removed
        t.remove_calibration_record(c)
        db.session.commit()
        self.assertEqual(t.calibration_records.count(), 0)

        # Check to make sure that non-linked CalibrationRecords can't be removed
        t.remove_calibration_record(c)
        db.session.commit()
        self.assertEqual(t.calibration_records.count(), 0)

    def test_due_date(self):
        # Create multiple CalibrationRecords with different calibration_due_date values
        c1 = CalibrationRecord(
            calibration_date=datetime(2021, 4, 30),
            calibration_due_date=datetime(2022, 3, 25))
        c2 = CalibrationRecord(
            calibration_date=datetime(2021, 6, 20),
            calibration_due_date=datetime(2022, 5, 12))
        t = TestEquipment(name="Oscilloscope")
        db.session.add_all([c1, c2, t])
        db.session.commit()

        # Add the two CalibrationRecords to the TestEquipment
        t.add_calibration_record(c1)
        t.add_calibration_record(c2)
        db.session.commit()

        # Check that the calibration_due_date with the most time until expiry is returned
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

    def test_update_test_equipment(self):
        te = TestEquipment(name="Oscilloscope")
        t = TestEquipmentType(name="Oscilloscope")
        db.session.add_all([t, te])
        db.session.commit()

        # Check that a TestEquipment can be added and checked if it exists
        t.add_test_equipment(te)
        db.session.commit()
        self.assertTrue(t.has_test_equipment(te))

        # Check to make sure that a duplicate TestEquipment can't be added
        t.add_test_equipment(te)
        db.session.commit()
        self.assertEqual(t.test_equipment.count(), 1)

        # Check to make sure a TestEquipment can be removed
        t.remove_test_equipment(te)
        db.session.commit()
        self.assertEqual(t.test_equipment.count(), 0)

        # Check to make sure that non-linked TestEquipment can't be removed
        t.remove_test_equipment(te)
        db.session.commit()
        self.assertEqual(t.test_equipment.count(), 0)


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

    def test_update_employees(self):
        u = User(username='michael')
        c = Company(name="MDS", category=CompanyCategory.SUPPLIER.value)
        db.session.add_all([u, c])
        db.session.commit()

        # Check that a User can be added and checked if it exists
        c.add_employee(u)
        db.session.commit()
        self.assertTrue(c.has_employee(u))

        # Check to make sure that duplicate Users can't be added
        c.add_employee(u)
        db.session.commit()
        self.assertEqual(c.employees.count(), 1)

        # Check to make sure a User can be removed
        c.remove_employee(u)
        db.session.commit()
        self.assertEqual(c.employees.count(), 0)

        # Check to make sure that non-linked Users can't be removed
        c.remove_employee(u)
        db.session.commit()
        self.assertEqual(c.employees.count(), 0)

    def test_suppliers(self):
        # Create 2 Suppliers and 1 Client
        c1 = Company(name="MDS", category=CompanyCategory.SUPPLIER.value)
        c2 = Company(name="MDS UK", category=CompanyCategory.SUPPLIER.value)
        c3 = Company(name="Roll-Royce", category=CompanyCategory.CLIENT.value)
        db.session.add_all([c1, c2, c3])
        db.session.commit()

        # Check that only the Suppliers are returned
        self.assertEqual(Company.suppliers(), [c1, c2])

    def test_clients(self):
        # Create 1 Supplier and 2 Clients
        c1 = Company(name="MDS", category=CompanyCategory.SUPPLIER.value)
        c2 = Company(name="GE", category=CompanyCategory.CLIENT.value)
        c3 = Company(name="Roll-Royce", category=CompanyCategory.CLIENT.value)
        db.session.add_all([c1, c2, c3])
        db.session.commit()

        # Check that only the Suppliers are returned
        self.assertEqual(Company.clients(), [c2, c3])


class TestPointModel(unittest.TestCase):

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

    def test_positive_calc_error(self):
        t = TestPoint(nominal_test_value=2.0000, measured_test_value=1.9953)
        db.session.add(t)
        db.session.commit()
        self.assertEqual(t.calc_error(), 2.0000-1.9953)

    def test_negative_calc_error(self):
        t = TestPoint(nominal_test_value=2.0000, measured_test_value=2.0084)
        db.session.add(t)
        db.session.commit()
        self.assertEqual(t.calc_error(), 2.0000-2.0084)
    
    def test_calc_max_error_eng_units(self):
        c = Channel(error_type=ErrorType.ENG_UNITS.value, max_error=1.5)
        t = TestPoint()
        db.session.add_all([c, t])
        db.session.commit()

        # Add the TestPoint to the Channel
        c.add_testpoint(t)
        db.session.commit()

        # Check the Channel's max_error is returned
        self.assertEqual(c.max_error, t.calc_max_error())

    def test_calc_max_error_percent_full_scale(self):
        c = Channel(error_type=ErrorType.PERCENT_FULL_SCALE.value, max_error=0.05,
            full_scale_range=250)
        t = TestPoint()
        db.session.add_all([c, t])
        db.session.commit()

        # Add the TestPoint to the Channel
        c.add_testpoint(t)
        db.session.commit()

        # Check the Channel's max error is calculated properly
        self.assertEqual(t.calc_max_error(), 0.125)

    def test_calc_max_error_percent_reading(self):
        c = Channel(error_type=ErrorType.PERCENT_READING.value, max_error=0.1)
        t = TestPoint(nominal_test_value=15)
        db.session.add_all([c, t])
        db.session.commit()

        # Add the TestPoint to the Channel
        c.add_testpoint(t)
        db.session.commit()

        # Check the Channel's max error is calculated properly when None
        self.assertEqual(t.calc_max_error(), 0.015)

        # Check the Channel's max error when a value has been measured
        t.measured_test_value = 15.5
        db.session.commit()
        self.assertEqual(t.calc_max_error(), 0.0155)

    def test_upper_and_lower_limits(self):
        c = Channel(error_type=ErrorType.ENG_UNITS.value, max_error=1.5)
        t = TestPoint(nominal_test_value=15.5)
        db.session.add_all([c, t])
        db.session.commit()

        # Add the TestPoint to the Channel
        c.add_testpoint(t)
        db.session.commit()

        # Check the upper and lower limits
        self.assertEqual(t.upper_limit(), 17)
        self.assertEqual(t.lower_limit(), 14)


class ChannelModel(unittest.TestCase):

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

    def test_delete_channel(self):
        c = Channel()
        t1 = TestPoint(channel_id=1)
        t2 = TestPoint(channel_id=1)
        tet1 = TestEquipmentType()
        tet2 = TestEquipmentType()
        te1 = TestEquipment()
        te2 = TestEquipment()
        u1 = User()
        u2 = User()
        cp = Company(category=CompanyCategory.SUPPLIER.value)
        db.session.add_all([c, t1, t2, tet1, tet2, te1, te2, u1, u2, cp])
        db.session.commit()

        # Add the necessary records to the Channel
        c.add_test_equipment_type(tet1)
        c.add_test_equipment_type(tet2)
        tet1.add_test_equipment(te1)
        tet2.add_test_equipment(te2)
        cp.add_employee(u1)
        cp.add_employee(u2)
        db.session.commit()
        cer1 = ChannelEquipmentRecord(channel_id=1, test_equipment_type_id=1, test_equipment_id=1)
        cer2 = ChannelEquipmentRecord(channel_id=1, test_equipment_type_id=2, test_equipment_id=2)
        c.add_approval(u1)
        c.add_approval(u2)
        c.equipment_records.append(cer1)
        c.equipment_records.append(cer2)
        db.session.commit()

        # Confirm the records are in stored and linked properly
        self.assertEqual(c.testpoints.all(), [t1, t2])
        self.assertEqual(c.equipment_records.all(), [cer1, cer2])
        self.assertEqual(c.required_test_equipment.all(), [tet1, tet2])
        self.assertEqual(c.approval_records.count(), 2)

        # Delete the channel links and records
        c.delete_all_records()
        self.assertEqual(c.testpoints.all(), [])
        self.assertEqual(c.equipment_records.all(), [])
        self.assertEqual(c.required_test_equipment.all(), [])
        self.assertEqual(c.approval_records.all(), [])

    # Check that a User can be added and checked if it exists
    def test_update_testpoint(self):
        c = Channel()
        t = TestPoint()
        db.session.add_all([c, t])
        db.session.commit()

        # Add the TestPoint to the Channel
        c.add_testpoint(t)
        db.session.commit()
        self.assertTrue(c.has_testpoint(t))

        # Check to make sure a TestPoint can be removed
        c.remove_testpoint(t)
        db.session.commit()
        self.assertFalse(c.has_testpoint(t))

        # Check to make sure that non-linked TestPoints can't be removed
        c.remove_testpoint(t)
        db.session.commit()
        self.assertFalse(c.has_testpoint(t))

    def test_num_testpoints(self):
        c = Channel()
        t1 = TestPoint()
        t2 = TestPoint()
        t3 = TestPoint()
        db.session.add_all([c, t1, t2, t3])
        db.session.commit()

        # Add the TestPoints to the Channel
        c.add_testpoint(t1)
        c.add_testpoint(t2)
        c.add_testpoint(t3)
        db.session.commit()

        # Check the number of TestPoints added to the Channel
        self.assertEqual(c.num_testpoints(), 3)

    def test_measurement_range(self):
        c = Channel(min_range=-0.500, max_range=0.500)
        db.session.add(c)
        db.session.commit()

        # Check the measurement range
        self.assertEqual(c.measurement_range(), 1.000)

    def test_injection_range(self):
        c = Channel(min_injection_range=-0.500, max_injection_range=0.500)
        db.session.add(c)
        db.session.commit()

        # Check the measurement range
        self.assertEqual(c.injection_range(), 1.000)

    def test_build_custom_testpoint_list(self):
        c = Channel()
        db.session.add(c)
        db.session.commit()

        # Build the custom TestPoint list
        injection_value_list = [-0.500, 0, 0.500]
        test_value_list = [-10, 0, 10]
        c.build_testpoint_list(
            num_testpoints=3,
            testpoint_list_type=TestPointListType.CUSTOM.value,
            injection_value_list=injection_value_list,
            test_value_list=test_value_list
        )
        db.session.commit()

        # Check that the TestPoints were generated properly
        testpoints = c.testpoints.all()
        for i in range(len(testpoints)):
            self.assertEqual(testpoints[i].nominal_injection_value, injection_value_list[i])
            self.assertEqual(testpoints[i].nominal_test_value, test_value_list[i])

    def test_build_standard_testpoint_list(self):
        c = Channel(min_range=0, max_range=100,
            min_injection_range=-5, max_injection_range=5)
        db.session.add(c)
        db.session.commit()

        # Build the standard TestPoint list
        c.build_testpoint_list(
            num_testpoints=5,
            testpoint_list_type=TestPointListType.STANDARD.value,
            injection_value_list=[],
            test_value_list=[]
        )
        db.session.commit()

        # Check that the TestPoints were generated properly
        injection_values = [-5, -2.5, 0, 2.5, 5]
        test_values = [0, 25, 50, 75, 100]
        testpoints = c.testpoints.all()
        for i in range(len(testpoints)):
            self.assertEqual(testpoints[i].nominal_injection_value, injection_values[i])
            self.assertEqual(testpoints[i].nominal_test_value, test_values[i]) 

    def test_testpoint_stats(self):
        c = Channel()
        t1 = TestPoint(channel_id=1, test_result=TestResult.UNTESTED.value)
        t2 = TestPoint(channel_id=1, test_result=TestResult.FAIL.value)
        t3 = TestPoint(channel_id=1, test_result=TestResult.FAIL.value)
        t4 = TestPoint(channel_id=1, test_result=TestResult.PASS.value)
        t5 = TestPoint(channel_id=1, test_result=TestResult.PASS.value)
        t6 = TestPoint(channel_id=1, test_result=TestResult.PASS.value)
        db.session.add_all([c, t1, t2, t3, t4, t5, t6])
        db.session.commit()

        # Check the TestPoint stats of the channel
        stats = c.testpoint_stats()
        self.assertEqual(stats[TestResult.UNTESTED.value], 1)
        self.assertEqual(stats[TestResult.FAIL.value], 2)
        self.assertEqual(stats[TestResult.PASS.value], 3)
    
    def test_update_status_untested(self):
        c = Channel()
        t1 = TestPoint(channel_id=1, test_result=TestResult.UNTESTED.value)
        t2 = TestPoint(channel_id=1, test_result=TestResult.UNTESTED.value)
        db.session.add_all([c, t1, t2])
        db.session.commit()

        # Check that the status should be UNTESTED
        c.update_status()
        db.session.commit()
        self.assertEqual(c.status, TestResult.UNTESTED.value)
    
    def test_update_status_pass(self):
        c = Channel()
        t1 = TestPoint(channel_id=1, test_result=TestResult.PASS.value)
        t2 = TestPoint(channel_id=1, test_result=TestResult.PASS.value)
        db.session.add_all([c, t1, t2])
        db.session.commit()

        # Check that the status should be PASS
        c.update_status()
        db.session.commit()
        self.assertEqual(c.status, TestResult.PASS.value)

    def test_update_status_fail(self):
        c = Channel()
        t1 = TestPoint(channel_id=1, test_result=TestResult.UNTESTED.value)
        t2 = TestPoint(channel_id=1, test_result=TestResult.FAIL.value)
        db.session.add_all([c, t1, t2])
        db.session.commit()

        # Check that the status should be FAIL
        c.update_status()
        db.session.commit()
        self.assertEqual(c.status, TestResult.FAIL.value)
    
    def test_update_status_in_progress(self):
        c = Channel()
        t1 = TestPoint(channel_id=1, test_result=TestResult.UNTESTED.value)
        t2 = TestPoint(channel_id=1, test_result=TestResult.PASS.value)
        db.session.add_all([c, t1, t2])
        db.session.commit()

        # Check that the status should be IN_PROGRESS
        c.update_status()
        db.session.commit()
        self.assertEqual(c.status, Status.IN_PROGRESS.value)

    def test_testpoint_progress(self):
        c = Channel()
        t1 = TestPoint(channel_id=1, test_result=TestResult.UNTESTED.value)        
        db.session.add_all([c, t1])
        db.session.commit()

        # Check the TestPoint progress so far
        progress = c.testpoint_progress()
        self.assertEqual(progress["percent_untested"], 100)
        self.assertEqual(progress["percent_passed"], 0)
        self.assertEqual(progress["percent_failed"], 0)

        # Add some additional TestPoints
        t2 = TestPoint(channel_id=1, test_result=TestResult.FAIL.value)
        t3 = TestPoint(channel_id=1, test_result=TestResult.PASS.value)
        t4 = TestPoint(channel_id=1, test_result=TestResult.PASS.value)
        db.session.add_all([t2, t3, t4])
        db.session.commit()

        # Check the TestPoint progress again
        progress = c.testpoint_progress()
        self.assertEqual(progress["percent_untested"], 25)
        self.assertEqual(progress["percent_passed"], 50)
        self.assertEqual(progress["percent_failed"], 25)

    def test_update_each_parent_status(self):
        pass

    def test_update_test_equipment_type(self):
        c = Channel()
        t = TestEquipmentType()
        db.session.add_all([c, t])
        db.session.commit()

        # Check that a TestEquipmentType can be added and checked if it exists
        c.add_test_equipment_type(t)
        db.session.commit()
        self.assertTrue(c.has_test_equipment_type(t))

        # Check to make sure that a duplicate TestEquipmentType can't be added
        c.add_test_equipment_type(t)
        db.session.commit()
        self.assertEqual(c.required_test_equipment.count(), 1)

        # Check to make sure a TestEquipmentType can be removed
        c.remove_test_equipment_type(t)
        db.session.commit()
        self.assertEqual(c.required_test_equipment.count(), 0)

        # Check to make sure that non-linked TestEquipmentTypes can't be removed
        c.remove_test_equipment_type(t)
        db.session.commit()
        self.assertEqual(c.required_test_equipment.count(), 0)

    def test_current_test_equipment(self):
        tet = TestEquipmentType()
        c = Channel()
        db.session.add_all([tet, c])

        # Check to make sure no TestEquipment is returned if one isn't assigned yet
        self.assertEqual(c.current_test_equipment(tet.id), None)

        # Create the TestEquipment and ChannelEquipmentRecords
        te1 = TestEquipment(test_equipment_type_id=1)
        te2 = TestEquipment(test_equipment_type_id=1)        
        cer1 = ChannelEquipmentRecord(timestamp=datetime(2021, 5, 10),
            channel_id=1, test_equipment_type_id=1, test_equipment_id=1)
        cer2 = ChannelEquipmentRecord(timestamp=datetime(2021, 8, 23),
            channel_id=1, test_equipment_type_id=1, test_equipment_id=2)
        db.session.add_all([te1, te2, cer1, cer2])
        db.session.commit()

        # Check to make sure the most recent ChannelEquipmentRecord is returned
        self.assertEqual(c.current_test_equipment(tet.id), te2)

    def test_update_required_supplier_approval(self):
        c = Channel(group_id=1)
        g = Group(job_id=1)
        j = Job(phase=JobPhase.COMMISSIONING.value)
        db.session.add_all([c, g, j])
        db.session.commit()

        # Update the approvals
        c.update_required_approvals()

        # Check the updated approval
        self.assertTrue(c.required_supplier_approval)
        self.assertFalse(c.required_client_approval)

    def test_update_required_client_approval(self):
        c = Channel(group_id=1)
        g = Group(job_id=1)
        j = Job(phase=JobPhase.ATP.value)
        db.session.add_all([c, g, j])
        db.session.commit()

        # Update the approvals
        c.update_required_approvals()

        # Check the updated approval
        self.assertTrue(c.required_supplier_approval)
        self.assertTrue(c.required_client_approval)

    def test_update_approval_records(self):
        cc = Company(category=CompanyCategory.SUPPLIER.value)
        c = Channel()
        u = User(company_id=1)
        db.session.add_all([cc, c, u])
        db.session.commit()

        # Check that an ApprovalRecord can be added and check that it exists
        c.add_approval(u)
        db.session.commit()
        self.assertTrue(c.has_approval_from_user(u))

        # Check to make sure that more than 1 ApprovalRecord can't be added
        c.add_approval(u)
        db.session.commit()
        self.assertEqual(c.approval_records.count(), 1)

        # Check to make sure that an ApprovalRecord can be removed
        c.remove_approval(u)
        db.session.commit()
        self.assertEqual(c.approval_records.count(), 0)

        # Check to make sure that non-linked ApprovalRecords can't be removed
        c.remove_approval(u)
        db.session.commit()
        self.assertEqual(c.approval_records.count(), 0)

    def test_supplier_and_client_approval_records(self):
        cc1 = Company(category=CompanyCategory.SUPPLIER.value)
        cc2 = Company(category=CompanyCategory.CLIENT.value)
        c = Channel()
        u1 = User(company_id=1)
        u2 = User(company_id=2)
        db.session.add_all([cc1, cc2, c, u1, u2])
        db.session.commit()

        # Add the ApprovalRecords for each user
        c.add_approval(u1)
        c.add_approval(u2)
        db.session.commit()

        # Check for each type of ApprovalRecord
        self.assertEqual(c.supplier_approval_record().user, u1)
        self.assertEqual(c.client_approval_record().user, u2)


class GroupModel(unittest.TestCase):

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

    def test_num_channels(self):
        g = Group()
        c1 = Channel(group_id=1)
        c2 = Channel(group_id=1)
        db.session.add_all([g, c1, c2])
        db.session.commit()

        # Check the number of Channels in the Group
        self.assertEqual(g.num_channels(), 2)

    def test_channel_stats(self):
        g = Group()
        db.session.add(g)
        db.session.commit()

        # Check the stats of the Group with no Channels
        stats = g.channel_stats()
        self.assertEqual(stats[TestResult.UNTESTED.value], 0)
        self.assertEqual(stats[TestResult.PASS.value], 0)
        self.assertEqual(stats[TestResult.FAIL.value], 0)
        self.assertEqual(stats[Status.IN_PROGRESS.value], 0)

        # Add some Channels to the Group
        c1 = Channel(group_id=1, status=TestResult.UNTESTED.value)
        c2 = Channel(group_id=1, status=TestResult.PASS.value)
        c3 = Channel(group_id=1, status=TestResult.PASS.value)
        c4 = Channel(group_id=1, status=TestResult.FAIL.value)
        c5 = Channel(group_id=1, status=Status.IN_PROGRESS.value)
        c6 = Channel(group_id=1, status=Status.IN_PROGRESS.value)
        db.session.add_all([c1, c2, c3, c4, c5, c6])
        db.session.commit()

        # Check the generated Channel status
        stats = g.channel_stats()
        self.assertEqual(stats[TestResult.UNTESTED.value], 1)
        self.assertEqual(stats[TestResult.PASS.value], 2)
        self.assertEqual(stats[TestResult.FAIL.value], 1)
        self.assertEqual(stats[Status.IN_PROGRESS.value], 2)

    def test_channel_progress(self):
        g = Group()
        db.session.add(g)
        db.session.commit()

        # Check the progress of the Channels in the Group with no Channels
        progress = g.channel_progress()
        self.assertEqual(progress["percent_untested"], 100)
        self.assertEqual(progress["percent_passed"], 0)
        self.assertEqual(progress["percent_failed"], 0)
        self.assertEqual(progress["percent_in_progress"], 0)

        # Add some Channels to the Group
        c1 = Channel(group_id=1, status=TestResult.UNTESTED.value)
        c2 = Channel(group_id=1, status=TestResult.PASS.value)
        c3 = Channel(group_id=1, status=TestResult.PASS.value)
        c4 = Channel(group_id=1, status=TestResult.FAIL.value)
        c5 = Channel(group_id=1, status=Status.IN_PROGRESS.value)
        db.session.add_all([c1, c2, c3, c4, c5])
        db.session.commit()

        # Check the progress of the Group with a list of Channels
        progress = g.channel_progress()
        self.assertEqual(progress["percent_untested"], 20)
        self.assertEqual(progress["percent_passed"], 40)
        self.assertEqual(progress["percent_failed"], 20)
        self.assertEqual(progress["percent_in_progress"], 20)

    def test_update_status(self):
        g = Group()
        c1 = Channel(group_id=1, status=TestResult.UNTESTED.value)
        db.session.add_all([g, c1])
        db.session.commit()

        # Check that the new status is NOT_STARTED
        g.update_status()
        self.assertEqual(g.status, Status.NOT_STARTED.value)

        # Add some Channels to the Group
        c2 = Channel(group_id=1, status=TestResult.PASS.value)
        c3 = Channel(group_id=1, status=TestResult.PASS.value)
        c4 = Channel(group_id=1, status=TestResult.FAIL.value)
        c5 = Channel(group_id=1, status=Status.IN_PROGRESS.value)
        db.session.add_all([c2, c3, c4, c5])
        db.session.commit()

        # Check that the new status is IN_PROGRESS
        g.update_status()
        self.assertEqual(g.status, Status.IN_PROGRESS.value)

        # Update the Channels to be all Passed
        c1.status = TestResult.PASS.value
        c4.status = TestResult.PASS.value
        c5.status = TestResult.PASS.value
        db.session.commit()

        # Check that the new status is COMPLETE
        g.update_status()
        self.assertEqual(g.status, Status.COMPLETE.value)


class JobModel(unittest.TestCase):

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

    def test_channels(self):
        j = Job()
        g1 = Group(job_id=1)
        g2 = Group(job_id=1)
        db.session.add_all([j, g1, g2])
        db.session.commit()

        # Check for the list of Channels under the job if no Channels are added
        self.assertEqual(j.channels(), [])

        # Add some Channels into the Job's Groups
        c1 = Channel(group_id=1)
        c2 = Channel(group_id=1)
        c3 = Channel(group_id=2)
        db.session.add_all([c1, c2, c3])
        db.session.commit()

        # Check for the total list of Channels under the Job
        self.assertEqual(j.channels(), [c1, c2, c3])

    def test_num_channels(self):
        j = Job()
        g1 = Group(job_id=1)
        g2 = Group(job_id=1)
        c1 = Channel(group_id=1)
        c2 = Channel(group_id=1)
        c3 = Channel(group_id=2)
        db.session.add_all([j, g1, g2, c1, c2, c3])
        db.session.commit()

        # Check for the total number of channels
        self.assertEqual(j.num_channels(), 3)

    def test_channel_stats(self):
        j = Job()
        g1 = Group(job_id=1)
        g2 = Group(job_id=1)
        db.session.add_all([j, g1, g2])
        db.session.commit()

        # Check the stats of the Job with no Channels
        stats = j.channel_stats()
        self.assertEqual(stats[TestResult.UNTESTED.value], 0)
        self.assertEqual(stats[TestResult.PASS.value], 0)
        self.assertEqual(stats[TestResult.FAIL.value], 0)
        self.assertEqual(stats[Status.IN_PROGRESS.value], 0)

        # Add some Channels to the Job's Groups
        c1 = Channel(group_id=1, status=TestResult.UNTESTED.value)
        c2 = Channel(group_id=1, status=TestResult.PASS.value)
        c3 = Channel(group_id=1, status=TestResult.PASS.value)
        c4 = Channel(group_id=2, status=TestResult.FAIL.value)
        c5 = Channel(group_id=2, status=Status.IN_PROGRESS.value)
        c6 = Channel(group_id=2, status=Status.IN_PROGRESS.value)
        db.session.add_all([c1, c2, c3, c4, c5, c6])
        db.session.commit()

        # Check the generated Channel status
        stats = j.channel_stats()
        self.assertEqual(stats[TestResult.UNTESTED.value], 1)
        self.assertEqual(stats[TestResult.PASS.value], 2)
        self.assertEqual(stats[TestResult.FAIL.value], 1)
        self.assertEqual(stats[Status.IN_PROGRESS.value], 2)
    
    def test_channel_progress(self):
        j = Job()
        g1 = Group(job_id=1)
        g2 = Group(job_id=1)
        db.session.add_all([j, g1, g2])
        db.session.commit()

        # Check the progress of the Channels in the Job with no Channels
        progress = j.channel_progress()
        self.assertEqual(progress["percent_untested"], 100)
        self.assertEqual(progress["percent_passed"], 0)
        self.assertEqual(progress["percent_failed"], 0)
        self.assertEqual(progress["percent_in_progress"], 0)

        # Add some Channels to the Job's Groups
        c1 = Channel(group_id=1, status=TestResult.UNTESTED.value)
        c2 = Channel(group_id=1, status=TestResult.PASS.value)
        c3 = Channel(group_id=1, status=TestResult.PASS.value)
        c4 = Channel(group_id=2, status=TestResult.FAIL.value)
        c5 = Channel(group_id=2, status=Status.IN_PROGRESS.value)
        db.session.add_all([c1, c2, c3, c4, c5])
        db.session.commit()

        # Check the progress of the Job with a list of Channels
        progress = j.channel_progress()
        self.assertEqual(progress["percent_untested"], 20)
        self.assertEqual(progress["percent_passed"], 40)
        self.assertEqual(progress["percent_failed"], 20)
        self.assertEqual(progress["percent_in_progress"], 20)

    def test_update_status(self):
        j = Job()
        g1 = Group(job_id=1)
        g2 = Group(job_id=1)
        c1 = Channel(group_id=1, status=TestResult.UNTESTED.value)
        db.session.add_all([j, g1, g2, c1])
        db.session.commit()

        # Check that the new status is NOT_STARTED
        j.update_status()
        self.assertEqual(j.status, Status.NOT_STARTED.value)

        # Add some additional Channels to the Groups
        c2 = Channel(group_id=1, status=TestResult.PASS.value)
        c3 = Channel(group_id=1, status=TestResult.PASS.value)
        c4 = Channel(group_id=2, status=TestResult.FAIL.value)
        c5 = Channel(group_id=2, status=Status.IN_PROGRESS.value)
        db.session.add_all([c2, c3, c4, c5])
        db.session.commit()

        # Check that the new status is IN_PROGRESS
        j.update_status()
        self.assertEqual(j.status, Status.IN_PROGRESS.value)

        # Update the Channels to be all Passed
        c1.status = TestResult.PASS.value
        c4.status = TestResult.PASS.value
        c5.status = TestResult.PASS.value
        db.session.commit()

        # Check that the new status is COMPLETE
        j.update_status()
        self.assertEqual(j.status, Status.COMPLETE.value)


class ProjectModel(unittest.TestCase):

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

    def test_update_company(self):
        p = Project()
        c = Company()
        db.session.add_all([p, c])
        db.session.commit()

        # Check that a Company can be added to the Project and checked if it exists
        p.add_company(c)
        db.session.commit()
        self.assertTrue(p.has_company(c))

        # Check to make sure that a duplicate Company can't be added
        p.add_company(c)
        db.session.commit()
        self.assertEqual(p.companies.count(), 1)

        # Check to make sure a Company can be removed from the Company Projects table
        p.remove_company(c)
        db.session.commit()
        self.assertEqual(p.companies.count(), 0)

        # Check to make sure that non-linked Company can't be removed
        p.remove_company(c)
        db.session.commit()
        self.assertEqual(p.companies.count(), 0)

    def test_supplier_and_client(self):
        p = Project()
        c1 = Company(category=CompanyCategory.CLIENT.value)
        c2 = Company(category=CompanyCategory.SUPPLIER.value)        
        db.session.add_all([p, c1, c2])
        db.session.commit()

        # Check that no Company is returned when no Project is added
        self.assertEqual(p.supplier(), None)
        self.assertEqual(p.client(), None)

        # Add each Company to the Project
        p.add_company(c1)
        p.add_company(c2)
        db.session.commit()

        # Check that the correct Company is returned
        self.assertEqual(p.supplier(), c2)
        self.assertEqual(p.client(), c1)

    def test_channels(self):
        p = Project()
        j1 = Job(project_id=1)
        j2 = Job(project_id=1)
        g1 = Group(job_id=1)
        g2 = Group(job_id=2)
        db.session.add_all([p, j1, j2, g1, g2])
        db.session.commit()

        # Check for the list of Channels under the Project if no Channels are added
        self.assertEqual(p.channels(), [])

        # Add some Channels into the Project's Job's Groups
        c1 = Channel(group_id=1)
        c2 = Channel(group_id=1)
        c3 = Channel(group_id=2)
        db.session.add_all([c1, c2, c3])
        db.session.commit()

        # Check for the total list of Channels under the Job
        self.assertEqual(p.channels(), [c1, c2, c3])

    def test_num_channels(self):
        p = Project()
        j1 = Job(project_id=1)
        j2 = Job(project_id=1)
        g1 = Group(job_id=1)
        g2 = Group(job_id=2)
        c1 = Channel(group_id=1)
        c2 = Channel(group_id=1)
        c3 = Channel(group_id=2)
        db.session.add_all([p, j1, j2, g1, g2, c1, c2, c3])
        db.session.commit()

        # Check for the total number of channels
        self.assertEqual(p.num_channels(), 3)

    def test_channel_stats(self):
        p = Project()
        j1 = Job(project_id=1)
        j2 = Job(project_id=1)
        g1 = Group(job_id=1)
        g2 = Group(job_id=2)
        db.session.add_all([p, j1, j2, g1, g2])
        db.session.commit()

        # Check the stats of the Project with no Channels
        stats = p.channel_stats()
        self.assertEqual(stats[TestResult.UNTESTED.value], 0)
        self.assertEqual(stats[TestResult.PASS.value], 0)
        self.assertEqual(stats[TestResult.FAIL.value], 0)
        self.assertEqual(stats[Status.IN_PROGRESS.value], 0)

        # Add some Channels to the Job's Groups
        c1 = Channel(group_id=1, status=TestResult.UNTESTED.value)
        c2 = Channel(group_id=1, status=TestResult.PASS.value)
        c3 = Channel(group_id=1, status=TestResult.PASS.value)
        c4 = Channel(group_id=2, status=TestResult.FAIL.value)
        c5 = Channel(group_id=2, status=Status.IN_PROGRESS.value)
        c6 = Channel(group_id=2, status=Status.IN_PROGRESS.value)
        db.session.add_all([c1, c2, c3, c4, c5, c6])
        db.session.commit()

        # Check the generated Channel status
        stats = p.channel_stats()
        self.assertEqual(stats[TestResult.UNTESTED.value], 1)
        self.assertEqual(stats[TestResult.PASS.value], 2)
        self.assertEqual(stats[TestResult.FAIL.value], 1)
        self.assertEqual(stats[Status.IN_PROGRESS.value], 2)

    def test_channel_progress(self):
        p = Project()
        j1 = Job(project_id=1)
        j2 = Job(project_id=1)
        g1 = Group(job_id=1)
        g2 = Group(job_id=2)
        db.session.add_all([p, j1, j2, g1, g2])
        db.session.commit()

        # Check the progress of the Channels in the Job with no Channels
        progress = p.channel_progress()
        self.assertEqual(progress["percent_untested"], 100)
        self.assertEqual(progress["percent_passed"], 0)
        self.assertEqual(progress["percent_failed"], 0)
        self.assertEqual(progress["percent_in_progress"], 0)

        # Add some Channels to the Job's Groups
        c1 = Channel(group_id=1, status=TestResult.UNTESTED.value)
        c2 = Channel(group_id=1, status=TestResult.PASS.value)
        c3 = Channel(group_id=1, status=TestResult.PASS.value)
        c4 = Channel(group_id=2, status=TestResult.FAIL.value)
        c5 = Channel(group_id=2, status=Status.IN_PROGRESS.value)
        db.session.add_all([c1, c2, c3, c4, c5])
        db.session.commit()

        # Check the progress of the Job with a list of Channels
        progress = p.channel_progress()
        self.assertEqual(progress["percent_untested"], 20)
        self.assertEqual(progress["percent_passed"], 40)
        self.assertEqual(progress["percent_failed"], 20)
        self.assertEqual(progress["percent_in_progress"], 20)
    
    def test_update_status(self):
        p = Project()
        j1 = Job(project_id=1)
        j2 = Job(project_id=1)
        g1 = Group(job_id=1)
        g2 = Group(job_id=2)
        c1 = Channel(group_id=1, status=TestResult.UNTESTED.value)
        c2 = Channel(group_id=1, status=TestResult.UNTESTED.value)
        db.session.add_all([p, j1, j2, g1, g2, c1, c2])
        db.session.commit()

        # Check that the new status is NOT_STARTED
        p.update_status()
        self.assertEqual(p.status, Status.NOT_STARTED.value)

        # Add some additional Channels to the Groups
        c3 = Channel(group_id=1, status=TestResult.PASS.value)
        c4 = Channel(group_id=1, status=TestResult.PASS.value)
        c5 = Channel(group_id=2, status=TestResult.FAIL.value)
        c6 = Channel(group_id=2, status=Status.IN_PROGRESS.value)
        db.session.add_all([c3, c4, c5, c6])
        db.session.commit()

        # Check that the new status is IN_PROGRESS
        p.update_status()
        self.assertEqual(p.status, Status.IN_PROGRESS.value)

        # Update the Channels to be all Passed
        c1.status = TestResult.PASS.value
        c2.status = TestResult.PASS.value
        c5.status = TestResult.PASS.value
        c6.status = TestResult.PASS.value
        db.session.commit()

        # Check that the new status is COMPLETE
        p.update_status()
        self.assertEqual(p.status, Status.COMPLETE.value)

    def test_update_members(self):
        p = Project()
        u1 = User()
        u2 = User()
        u3 = User()
        db.session.add_all([p, u1, u2, u3])
        db.session.commit()

        # Check that a User can be added and checked if it exists
        p.add_member(u1)
        db.session.commit()
        self.assertTrue(p.has_member(u1))

        # Check to make sure that duplicate Users can't be added
        p.add_members([u1, u2, u3])
        db.session.commit()
        self.assertEqual(p.members.count(), 3)

        # Check to make sure a User can be removed
        p.remove_member(u3)
        db.session.commit()
        self.assertEqual(p.members.count(), 2)

        # Check to make sure that non-linked Users can't be removed
        p.remove_members([u1, u2, u3])
        db.session.commit()
        self.assertEqual(p.members.count(), 0)

    def test_update_test_equipment(self):
        p = Project()
        t = TestEquipment()
        db.session.add_all([p, t])
        db.session.commit()

        # Check that a TestEquipment can be added and checked if it exists
        p.add_test_equipment(t)
        db.session.commit()
        self.assertTrue(p.has_test_equipment(t))

        # Check to make sure that a duplicate TestEquipment can't be added
        p.add_test_equipment(t)
        db.session.commit()
        self.assertEqual(p.test_equipment.count(), 1)

        # Check to make sure a TestEquipment can be removed
        p.remove_test_equipment(t)
        db.session.commit()
        self.assertEqual(p.test_equipment.count(), 0)

        # Check to make sure that non-linked TestEquipment can't be removed
        p.remove_test_equipment(t)
        db.session.commit()
        self.assertEqual(p.test_equipment.count(), 0)

    def test_has_test_equipment_of_type(self):
        p = Project()
        te = TestEquipment(test_equipment_type_id=1, name="Oscilloscope")
        tet = TestEquipmentType(name="Oscilloscope")
        db.session.add_all([p, te, tet])
        db.session.commit()

        # Check that there are no TestEquipment to begin with
        self.assertEqual(p.test_equipment_of_type(tet), [])
        self.assertFalse(p.has_test_equipment_of_type(tet))

        # Add the TestEquipment to the Project
        p.add_test_equipment(te)
        db.session.commit()

        # Check the Project has the TestEquipment of the specified TestEquipmentType
        self.assertEqual(p.test_equipment_of_type(tet), [te])
        self.assertTrue(p.has_test_equipment_of_type(tet))


class TestUtils(unittest.TestCase):

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

    def test_channel_stats(self):
        c1 = Channel(status=TestResult.UNTESTED.value)
        c2 = Channel(status=TestResult.PASS.value)
        c3 = Channel(status=TestResult.PASS.value)
        c4 = Channel(status=TestResult.FAIL.value)
        c5 = Channel(status=Status.IN_PROGRESS.value)
        c6 = Channel(status=Status.IN_PROGRESS.value)
        db.session.add_all([c1, c2, c3, c4, c5, c6])
        db.session.commit()

        # Check the generated Channel status
        channels = [c1, c2, c3, c4, c5, c6]
        stats = channel_stats(channels)
        self.assertEqual(stats[TestResult.UNTESTED.value], 1)
        self.assertEqual(stats[TestResult.PASS.value], 2)
        self.assertEqual(stats[TestResult.FAIL.value], 1)
        self.assertEqual(stats[Status.IN_PROGRESS.value], 2)

    def test_channel_progress(self):
        g = Group()
        db.session.add(g)
        db.session.commit()

        # Check the progress of the Channels in the Group with no Channels
        progress = channel_progress(g)
        self.assertEqual(progress["percent_untested"], 100)
        self.assertEqual(progress["percent_passed"], 0)
        self.assertEqual(progress["percent_failed"], 0)
        self.assertEqual(progress["percent_in_progress"], 0)

        # Add some Channels to the Group
        c1 = Channel(group_id=1, status=TestResult.UNTESTED.value)
        c2 = Channel(group_id=1, status=TestResult.PASS.value)
        c3 = Channel(group_id=1, status=TestResult.PASS.value)
        c4 = Channel(group_id=1, status=TestResult.FAIL.value)
        c5 = Channel(group_id=1, status=Status.IN_PROGRESS.value)
        db.session.add_all([c1, c2, c3, c4, c5])
        db.session.commit()

        # Check the progress of the Channels in the Group with several Channels
        progress = channel_progress(g)
        self.assertEqual(progress["percent_untested"], 20)
        self.assertEqual(progress["percent_passed"], 40)
        self.assertEqual(progress["percent_failed"], 20)
        self.assertEqual(progress["percent_in_progress"], 20)

    def test_none_if_empty(self):
        self.assertEqual(none_if_empty(""), None)
        self.assertEqual(none_if_empty("Test"), "Test")
        self.assertEqual(none_if_empty(4.223), 4.223)

    def test_calc_percent(self):
        self.assertEqual(calc_percent(3, 5), 60)
        self.assertEqual(calc_percent(0, 5), 0)
        self.assertEqual(calc_percent(7, 26), 27)

    def test_number_list_choices_one_digit(self):
        self.assertEqual(number_list_choices(1, 3, 1), [(1, 1), (2, 2), (3, 3)])
        self.assertEqual(number_list_choices(1, 3, 2), [(1, '01'), (2, '02'), (3, '03')])
        self.assertEqual(number_list_choices(1, 3, 3), [(1, '001'), (2, '002'), (3, '003')])


if __name__ == '__main__':
    unittest.main(verbosity=2)