from ninja import NinjaAPI, Schema

api = NinjaAPI(title="Buditel API", version="0.1.0")


class HealthOut(Schema):
    status: str


@api.get("/health", response=HealthOut, auth=None)
def health(request) -> HealthOut:  # type: ignore[no-untyped-def]
    return HealthOut(status="ok")
