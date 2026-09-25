from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", include_in_schema=False)
async def home():
    return RedirectResponse(url="/rooms", status_code=303)

@app.get("/rooms", response_class=HTMLResponse)
async def rooms(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="rooms.html",
        context={},
        )