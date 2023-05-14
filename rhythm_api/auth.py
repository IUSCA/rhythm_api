import json
import time
from pathlib import Path

from jwcrypto.jwt import JWT, JWK

from rhythm_api.config import config


def load_key(key_filename: Path | str) -> JWK:
    # Load the key from the PEM file
    with open(key_filename, 'rb') as f:
        key_pem = f.read()
    return JWK.from_pem(key_pem)


public_key_path = Path('.').resolve() / config['auth']['jwt']['pub']
public_key = load_key(public_key_path)

private_key_path = Path('.').resolve() / config['auth']['jwt']['key']
private_key = load_key(private_key_path)


def issue_JWT(sub: str, expires_in: int = None) -> str:
    header = {"alg": "RS256", "typ": "JWT"}

    iss = config['auth']['jwt']['iss']
    now = int(time.time())

    claims = {
        "iat": now,
        "iss": iss,
        "sub": sub,
        "source": "microservice"
    }
    if expires_in is not None and expires_in > 0:
        claims["exp"] = now + expires_in

    token = JWT(header=header, claims=claims)
    token.make_signed_token(private_key)
    return token.serialize()


def validate_JWT(token: str) -> dict:
    iss = config['auth']['jwt']['iss']
    jwt = JWT()
    jwt.deserialize(token)
    jwt.validate(public_key)
    decoded_token = json.loads(jwt.claims)

    assert 'iss' in decoded_token and decoded_token['iss'] == iss, 'Invalid iss'
    assert 'sub' in decoded_token and decoded_token['sub'], 'Invalid token: sub is either missing or empty.'

    return decoded_token


if __name__ == '__main__':
    token = ''
    claims = validate_JWT(token)
    print(claims)
