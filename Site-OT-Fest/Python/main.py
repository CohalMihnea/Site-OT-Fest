from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from routers import auth_routes, account_routes, submission_routes, admin_routes
from config import HTML_DIR, STATIC_DIR
from database import Base, engine


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Overthink Film Fest API",
    version="1.0.0"
)
app.include_router(auth_routes.router)
app.include_router(account_routes.router)
app.include_router(submission_routes.router)
app.include_router(admin_routes.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if STATIC_DIR.exists():
    app.mount(
        "/Foto",
        StaticFiles(directory=STATIC_DIR / "FOTO"),
        name="foto"
    )


def serve_html_file(filename: str):
    file_path = HTML_DIR / filename

    if not file_path.exists():
        return {
            "detail": f"Fișierul {filename} nu există în folderul html."
        }

    return FileResponse(file_path)


@app.get("/")
def home():
    return serve_html_file("index.html")


@app.get("/index.html")
def index_page():
    return serve_html_file("index.html")


@app.get("/contact.html")
def contact_page():
    return serve_html_file("contact.html")


@app.get("/program.html")
def program_page():
    return serve_html_file("program.html")


@app.get("/inscriere.html")
def inscriere_page():
    return serve_html_file("inscriere.html")


@app.get("/auth.html")
def auth_page():
    return serve_html_file("auth.html")


@app.get("/cont.html")
def cont_page():
    return serve_html_file("cont.html")


@app.get("/admin.html")
def admin_page():
    return serve_html_file("admin.html")


@app.get("/parteneri-admin.html")
def partners_admin_page():
    return serve_html_file("parteneri-admin.html")


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "message": "Overthink Film Fest API funcționează."
    }
