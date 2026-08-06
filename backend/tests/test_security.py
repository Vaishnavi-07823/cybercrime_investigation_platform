from app.core.security import hash_password, verify_password


def test_password_round_trip() -> None:
    encoded = hash_password("Correct-Horse-Battery-123")
    assert verify_password("Correct-Horse-Battery-123", encoded)
    assert not verify_password("wrong-password", encoded)
