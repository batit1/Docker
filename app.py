from aiohttp import web, ClientSession
import os
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CACHE_KEY = "fact"


def get_redis_client():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


async def fetch_remote_fact():
    url = "https://catfact.ninja/fact"
    async with ClientSession() as session:
        async with session.get(url, timeout=10) as response:
            data = await response.json()
            return data["fact"]


async def health(request):
    return web.json_response({"status": "ok"})


async def fact(request):
    r = get_redis_client()
    try:
        cached = r.get(CACHE_KEY)

        if cached:
            return web.json_response({
                "source": "cache",
                "fact": cached
            })

        remote_fact = await fetch_remote_fact()
        r.setex(CACHE_KEY, 30, remote_fact)

        return web.json_response({
            "source": "remote",
            "fact": remote_fact
        })

    except redis.exceptions.ConnectionError:
        return web.json_response(
            {"error": "No se pudo conectar con Redis"},
            status=500
        )
    except Exception as e:
        return web.json_response(
            {"error": "Ha ocurrido un error", "details": str(e)},
            status=500
        )


def create_app():
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/fact", fact)
    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8080)