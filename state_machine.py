from enum import Enum
import time
from flask import session, jsonify
from database import SessionLocal, Transfer, log_audit


class ReceiverState(str, Enum):
    INITIAL = "INITIAL"
    QR_OK = "QR_OK"
    PASSWORD_OK = "PASSWORD_OK"
    KEY_SHOWN = "KEY_SHOWN"
    EYE_ENROLLED = "EYE_ENROLLED"
    EYE_VERIFIED = "EYE_VERIFIED"
    DATA_VIEW = "DATA_VIEW"


# Allowed sequential order: step -> required prerequisite step
STATE_PREREQUISITES = {
    ReceiverState.QR_OK: [ReceiverState.INITIAL, ReceiverState.QR_OK],
    ReceiverState.PASSWORD_OK: [ReceiverState.QR_OK],
    ReceiverState.KEY_SHOWN: [ReceiverState.PASSWORD_OK, ReceiverState.KEY_SHOWN],
    ReceiverState.EYE_ENROLLED: [ReceiverState.KEY_SHOWN, ReceiverState.EYE_ENROLLED],
    ReceiverState.EYE_VERIFIED: [ReceiverState.EYE_ENROLLED],
    ReceiverState.DATA_VIEW: [ReceiverState.EYE_VERIFIED, ReceiverState.DATA_VIEW]
}

STATE_RANKS = {
    ReceiverState.INITIAL: 0,
    ReceiverState.QR_OK: 1,
    ReceiverState.PASSWORD_OK: 2,
    ReceiverState.KEY_SHOWN: 3,
    ReceiverState.EYE_ENROLLED: 4,
    ReceiverState.EYE_VERIFIED: 5,
    ReceiverState.DATA_VIEW: 6
}


class StateMachineError(Exception):
    def __init__(self, message: str, status_code: int = 403):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ReceiverStateMachine:
    """
    Server-side session-backed state machine for the 6-step receiver flow.
    Enforces that steps cannot be bypassed or called out of order.
    """

    SESSION_STATE_KEY = "receiver_state"
    SESSION_TRANSFER_KEY = "receiver_transfer_id"

    @classmethod
    def get_current_state(cls) -> ReceiverState:
        state_str = session.get(cls.SESSION_STATE_KEY, ReceiverState.INITIAL.value)
        try:
            return ReceiverState(state_str)
        except ValueError:
            return ReceiverState.INITIAL

    @classmethod
    def get_current_transfer_id(cls) -> str | None:
        return session.get(cls.SESSION_TRANSFER_KEY)

    @classmethod
    def reset(cls):
        session[cls.SESSION_STATE_KEY] = ReceiverState.INITIAL.value
        session.pop(cls.SESSION_TRANSFER_KEY, None)
        session.pop("unwrapped_key", None)
        session.pop("unwrapped_iv", None)
        session.pop("unwrapped_cipher", None)

    @classmethod
    def check_lockout(cls, transfer_id: str):
        """
        Checks if transfer is currently locked due to failed password or biometric attempts.
        """
        db = SessionLocal()
        try:
            transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
            if not transfer:
                raise StateMachineError("Transfer record not found", 404)

            now = time.time()
            if transfer.password_locked_until and transfer.password_locked_until > now:
                rem_mins = int((transfer.password_locked_until - now) / 60) + 1
                raise StateMachineError(f"Transfer locked: Too many failed password attempts. Try again in {rem_mins} min.", 423)

            if transfer.eye_locked_until and transfer.eye_locked_until > now:
                rem_mins = int((transfer.eye_locked_until - now) / 60) + 1
                raise StateMachineError(f"Transfer locked: Too many failed eye verification attempts. Try again in {rem_mins} min.", 423)
        finally:
            db.close()

    @classmethod
    def require_step(cls, required_state: ReceiverState, transfer_id: str = None):
        """
        Validates that the session is in the correct state to perform or view the step.
        If out of order, raises StateMachineError (HTTP 403).
        """
        current_state = cls.get_current_state()
        curr_tid = cls.get_current_transfer_id()

        if transfer_id and curr_tid and curr_tid != transfer_id:
            raise StateMachineError("Transfer ID mismatch in active session. Please start from QR scan.", 403)

        effective_tid = transfer_id or curr_tid
        if effective_tid:
            cls.check_lockout(effective_tid)

        allowed_prereqs = STATE_PREREQUISITES.get(required_state, [])
        if current_state not in allowed_prereqs:
            log_audit(
                step=required_state.value,
                status="OUT_OF_ORDER",
                details=f"Blocked attempt to access step {required_state.value} from current state {current_state.value}",
                transfer_id=effective_tid
            )
            raise StateMachineError(
                f"Access denied: Step '{required_state.value}' is out of order. Current state: '{current_state.value}'",
                403
            )

    @classmethod
    def transition_to(cls, target_state: ReceiverState, transfer_id: str = None):
        """
        Transitions session to target_state after validating prerequisites.
        """
        cls.require_step(target_state, transfer_id)
        session[cls.SESSION_STATE_KEY] = target_state.value
        if transfer_id:
            session[cls.SESSION_TRANSFER_KEY] = transfer_id

        log_audit(
            step=target_state.value,
            status="SUCCESS",
            details=f"State machine transitioned successfully to {target_state.value}",
            transfer_id=transfer_id or cls.get_current_transfer_id()
        )

