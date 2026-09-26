from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from tests.fixtures.figures import front_figure

PASSWORD = "correct horse battery staple"


def image_bytes(image: Image.Image, fmt: str = "PNG", **save_kwargs) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format=fmt, **save_kwargs)
    return buffer.getvalue()


def register(client: TestClient, email: str, name: str = "Test User", password: str = PASSWORD):
    return client.post("/api/auth/register", json={"email": email, "password": password, "full_name": name})


def login(client: TestClient, email: str, password: str = PASSWORD):
    return client.post("/api/auth/token", data={"username": email, "password": password})


def auth_headers(client: TestClient, email: str = "alice@example.com", name: str = "Alice Example") -> dict:
    assert register(client, email, name).status_code == 201
    response = login(client, email)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def upload(
    client: TestClient,
    headers: dict,
    data: bytes | None = None,
    filename: str = "photo.png",
    content_type: str = "image/png",
    **fields,
):
    data = data if data is not None else image_bytes(front_figure())
    form = {k: str(v) for k, v in fields.items() if v is not None}
    return client.post("/api/analyses", headers=headers, files={"image": (filename, data, content_type)}, data=form)
