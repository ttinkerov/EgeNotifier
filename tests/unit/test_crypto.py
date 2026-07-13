from egebot.security.crypto import FieldEncryptor


def test_encrypt_decrypt_roundtrip() -> None:
    key = FieldEncryptor.generate_key()
    crypto = FieldEncryptor(key)
    assert crypto.enabled
    token = "ParticipantSecretToken"
    encrypted = crypto.encrypt(token)
    assert encrypted is not None
    assert encrypted != token
    assert crypto.decrypt(encrypted) == token


def test_decrypt_accepts_legacy_plaintext() -> None:
    key = FieldEncryptor.generate_key()
    crypto = FieldEncryptor(key)
    assert crypto.decrypt("legacy-plain-token") == "legacy-plain-token"


def test_without_key_is_passthrough() -> None:
    crypto = FieldEncryptor.noop()
    assert not crypto.enabled
    assert crypto.encrypt("abc") == "abc"
    assert crypto.decrypt("abc") == "abc"


def test_decrypt_keeps_value_on_key_mismatch() -> None:
    key = FieldEncryptor.generate_key()
    other = FieldEncryptor(FieldEncryptor.generate_key())
    encrypted = FieldEncryptor(key).encrypt("secret")
    assert encrypted is not None
    assert other.decrypt(encrypted) == encrypted
