"""
Repară interactiv conturile create greșit ca voluntari.

Ce face:
- caută conturile recente care au role='voluntar';
- pentru fiecare cont îți arată ID, nume, email și data creării;
- te întreabă dacă acel cont trebuie să primească/rămână cu rolul de voluntar;
- dacă răspunzi DA: setează role='voluntar' și îi pune toate departamentele de festival;
- dacă răspunzi NU: setează role='participant';
- dacă răspunzi SKIP: nu modifică acel cont.

Nu șterge conturi, înscrieri sau ore.

Exemple:
  python fix_recent_volunteers_interactive.py --last 10
  python fix_recent_volunteers_interactive.py --after-id 123
"""

import argparse
import json
from datetime import datetime

from database import SessionLocal
from models import User, VolunteerProfile

FESTIVAL_DEPARTMENTS = [
    "Productie",
    "Marketing",
    "Directie artistica si continut",
    "Decor",
]


def parse_departments(value):
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def ask_choice(user):
    print("\n----------------------------------------")
    print(f"ID: #{user.id}")
    print(f"Nume: {user.name}")
    print(f"Email: {user.email}")
    print(f"Telefon: {user.phone or '-'}")
    print(f"Rol actual: {user.role}")
    print(f"Creat la: {user.created_at}")

    while True:
        answer = input("Primește/rămâne cu rolul de voluntar? [d/n/s] d=da, n=nu, s=sari: ").strip().lower()

        if answer in ["d", "da", "y", "yes"]:
            return "yes"

        if answer in ["n", "nu", "no"]:
            return "no"

        if answer in ["s", "skip", "sar", "sari"]:
            return "skip"

        print("Răspuns invalid. Scrie d, n sau s.")


def ensure_volunteer_profile(db, user):
    profile = (
        db.query(VolunteerProfile)
        .filter(VolunteerProfile.user_id == user.id)
        .first()
    )

    if not profile:
        profile = VolunteerProfile(user_id=user.id)
        db.add(profile)

    current_club_departments = parse_departments(profile.club_departments)

    profile.festival_departments = json.dumps(FESTIVAL_DEPARTMENTS, ensure_ascii=False)
    profile.club_departments = json.dumps(current_club_departments, ensure_ascii=False)
    profile.updated_at = datetime.utcnow()

    return profile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--last", type=int, default=None, help="Verifică doar ultimele N conturi cu role='voluntar'.")
    parser.add_argument("--after-id", type=int, default=None, help="Verifică doar conturile cu ID mai mare sau egal cu acest ID.")
    parser.add_argument("--include-participants", action="store_true", help="Include și conturile recente cu role='participant', dacă vrei să activezi manual voluntari.")
    args = parser.parse_args()

    db = SessionLocal()

    try:
        if args.include_participants:
            query = db.query(User).filter(User.role.in_(["voluntar", "participant"]))
        else:
            query = db.query(User).filter(User.role == "voluntar")

        if args.after_id is not None:
            query = query.filter(User.id >= args.after_id)

        query = query.order_by(User.created_at.desc())

        if args.last is not None:
            query = query.limit(args.last)

        users = query.all()

        if not users:
            print("Nu am găsit conturi pentru criteriile date.")
            return

        yes_count = 0
        no_count = 0
        skip_count = 0

        print(f"Am găsit {len(users)} conturi de verificat.")
        print("Pentru fiecare cont, alegi dacă trebuie să fie voluntar.")

        for user in users:
            choice = ask_choice(user)

            if choice == "yes":
                user.role = "voluntar"
                user.updated_at = datetime.utcnow()
                ensure_volunteer_profile(db, user)
                yes_count += 1
                print(f"OK: {user.name} va avea rol de voluntar și toate departamentele de festival.")

            elif choice == "no":
                user.role = "participant"
                user.updated_at = datetime.utcnow()
                no_count += 1
                print(f"OK: {user.name} va rămâne participant.")

            else:
                skip_count += 1
                print(f"Sărit: {user.name} nu a fost modificat.")

        confirm = input("\nAplic modificările în baza de date? [da/nu]: ").strip().lower()

        if confirm in ["da", "d", "yes", "y"]:
            db.commit()
            print("\nGata. Modificări aplicate.")
            print(f"Voluntari activați/reparați: {yes_count}")
            print(f"Setați ca participanți: {no_count}")
            print(f"Săriți: {skip_count}")
        else:
            db.rollback()
            print("\nAnulat. Nu s-a modificat nimic în baza de date.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
