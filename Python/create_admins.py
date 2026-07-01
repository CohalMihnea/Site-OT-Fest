from database import SessionLocal, Base, engine
from models import User
from auth import hash_password


Base.metadata.create_all(bind=engine)


ADMINS = [
    {
        "name": "Mihnea",
        "email": "cohalmihnea@gmail.com",
        "phone": "0773746372",
        "password": "2105790630.Mihnea"
    },
    {
        "name": "Rares",
        "email": "frogcrazy664@gmail.com",
        "phone": "0773819026",
        "password": "Microunde_portocala"
    },
    {
        "name": "Matei",
        "email": "elisei.mateiandrei@gmail.com",
        "phone": "0742415898",
        "password": "MateiAdmin1"
    }
]


def create_admins():
    db = SessionLocal()

    try:
        for admin in ADMINS:
            email = admin["email"].strip().lower()

            existing_user = db.query(User).filter(User.email == email).first()

            if existing_user:
                existing_user.name = admin["name"]
                existing_user.phone = admin["phone"]
                existing_user.password_hash = hash_password(admin["password"])
                existing_user.role = "admin"
                existing_user.is_admin = True
                existing_user.is_verified = True
                existing_user.is_disabled = False

                print(f"Admin actualizat: {email}")
            else:
                new_admin = User(
                    name=admin["name"],
                    email=email,
                    phone=admin["phone"],
                    password_hash=hash_password(admin["password"]),
                    role="admin",
                    is_admin=True,
                    is_verified=True,
                    is_disabled=False
                )

                db.add(new_admin)
                print(f"Admin creat: {email}")

        db.commit()

        print("\nGata. Adminii au fost creați/actualizați.")
        print("IMPORTANT: schimbă parolele după primul test sau setează parole mai bune direct în script.")

    finally:
        db.close()


if __name__ == "__main__":
    create_admins()