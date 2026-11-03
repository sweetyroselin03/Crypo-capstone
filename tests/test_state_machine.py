import unittest
import os
import sys
import time
from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import init_db, SessionLocal, Transfer, Base, engine
from state_machine import ReceiverStateMachine, ReceiverState, StateMachineError


class TestStateMachine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = "test-secret-key-12345"
        self.transfer_id = "tr-state-test-001"

        # Create dummy transfer record
        db = SessionLocal()
        # Clean up any previous test row
        db.query(Transfer).filter(Transfer.id == self.transfer_id).delete()
        t = Transfer(
            id=self.transfer_id,
            original_filename="contract.xlsx",
            file_size_bytes=1024,
            cipher_type="AES",
            encrypted_file_path="data/dummy.enc",
            password_hash="dummy_hash",
            password_salt="dummy_salt",
            qr_payload="dummy_qr",
            qr_image_path="data/dummy.png",
            failed_password_attempts=0,
            failed_eye_attempts=0
        )
        db.add(t)
        db.commit()
        db.close()

    def test_orderly_flow_succeeds(self):
        with self.app.test_request_context("/"):
            ReceiverStateMachine.reset()
            self.assertEqual(ReceiverStateMachine.get_current_state(), ReceiverState.INITIAL)

            # Step 1: QR_OK
            ReceiverStateMachine.transition_to(ReceiverState.QR_OK, self.transfer_id)
            self.assertEqual(ReceiverStateMachine.get_current_state(), ReceiverState.QR_OK)

            # Step 2: PASSWORD_OK
            ReceiverStateMachine.transition_to(ReceiverState.PASSWORD_OK, self.transfer_id)
            self.assertEqual(ReceiverStateMachine.get_current_state(), ReceiverState.PASSWORD_OK)

            # Step 3: KEY_SHOWN
            ReceiverStateMachine.transition_to(ReceiverState.KEY_SHOWN, self.transfer_id)
            self.assertEqual(ReceiverStateMachine.get_current_state(), ReceiverState.KEY_SHOWN)

            # Step 4: EYE_ENROLLED
            ReceiverStateMachine.transition_to(ReceiverState.EYE_ENROLLED, self.transfer_id)
            self.assertEqual(ReceiverStateMachine.get_current_state(), ReceiverState.EYE_ENROLLED)

            # Step 5: EYE_VERIFIED
            ReceiverStateMachine.transition_to(ReceiverState.EYE_VERIFIED, self.transfer_id)
            self.assertEqual(ReceiverStateMachine.get_current_state(), ReceiverState.EYE_VERIFIED)

            # Step 6: DATA_VIEW
            ReceiverStateMachine.transition_to(ReceiverState.DATA_VIEW, self.transfer_id)
            self.assertEqual(ReceiverStateMachine.get_current_state(), ReceiverState.DATA_VIEW)

    def test_out_of_order_step_blocked_with_403(self):
        with self.app.test_request_context("/"):
            ReceiverStateMachine.reset()

            # Attempt to jump straight to DATA_VIEW from INITIAL
            with self.assertRaises(StateMachineError) as ctx:
                ReceiverStateMachine.transition_to(ReceiverState.DATA_VIEW, self.transfer_id)
            self.assertEqual(ctx.exception.status_code, 403)

            # Perform Step 1: QR_OK
            ReceiverStateMachine.transition_to(ReceiverState.QR_OK, self.transfer_id)

            # Attempt to jump to EYE_VERIFIED skipping Password, Key, and Eye Enrollment
            with self.assertRaises(StateMachineError) as ctx2:
                ReceiverStateMachine.transition_to(ReceiverState.EYE_VERIFIED, self.transfer_id)
            self.assertEqual(ctx2.exception.status_code, 403)

    def test_lockout_detection(self):
        with self.app.test_request_context("/"):
            ReceiverStateMachine.reset()
            ReceiverStateMachine.transition_to(ReceiverState.QR_OK, self.transfer_id)

            # Simulate 15 minute lockout on database transfer
            db = SessionLocal()
            t = db.query(Transfer).filter(Transfer.id == self.transfer_id).first()
            t.eye_locked_until = time.time() + 900.0  # 15 minutes
            db.commit()
            db.close()

            # Next call must trigger 423 lockout
            with self.assertRaises(StateMachineError) as ctx:
                ReceiverStateMachine.check_lockout(self.transfer_id)
            self.assertEqual(ctx.exception.status_code, 423)
            self.assertIn("locked", ctx.exception.message.lower())


if __name__ == "__main__":
    unittest.main()

