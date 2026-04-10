#!/usr/bin/env python3
"""CLI script to onboard a new club to RFAF Analytics.

Usage:
    python backend/scripts/onboard_club.py \
        --nombre "CD Cuarte" \
        --email "entrenador@cdcuarte.es" \
        --plan profesional \
        --admin-name "Carlos García" \
        --admin-password "temporal123"
"""

import argparse
import asyncio
import sys

from passlib.hash import bcrypt

sys.path.insert(0, ".")

from backend.database import async_session, create_tables
from backend.models import Club, PlanType, User, UserRole


async def onboard_club(
    nombre: str,
    email: str,
    plan: str,
    admin_name: str,
    admin_password: str,
) -> None:
    await create_tables()

    try:
        plan_type = PlanType(plan.lower())
    except ValueError:
        print(f"Error: Plan '{plan}' no válido. Opciones: basico, profesional, federado")
        sys.exit(1)

    async with async_session() as session:
        from sqlalchemy import select

        existing = await session.execute(select(Club).where(Club.email == email))
        if existing.scalar_one_or_none():
            print(f"Error: Ya existe un club con email {email}")
            sys.exit(1)

        club = Club(name=nombre, email=email, plan=plan_type, active=True)
        session.add(club)
        await session.flush()

        password_hash = bcrypt.hash(admin_password)
        user = User(
            club_id=club.id,
            email=email,
            password_hash=password_hash,
            name=admin_name,
            role=UserRole.ADMIN,
        )
        session.add(user)
        await session.commit()

        print(f"""
Club onboarded:
  Club:     {nombre}
  Email:    {email}
  Plan:     {plan_type.value}
  Club ID:  {club.id}
  Admin:    {admin_name}
  User ID:  {user.id}
""")

        try:
            from backend.services.email_service import RESEND_API_KEY

            if RESEND_API_KEY and RESEND_API_KEY != "re_...":
                import resend

                resend.api_key = RESEND_API_KEY
                resend.Emails.send({
                    "from": "RFAF Analytics <noreply@rfaf-analytics.es>",
                    "to": [email],
                    "subject": f"Bienvenido a RFAF Analytics, {nombre}",
                    "html": f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #1a237e;">Bienvenido a RFAF Analytics</h2>
                        <p>Hola {admin_name},</p>
                        <p>Tu club <b>{nombre}</b> ya tiene acceso a la plataforma.</p>
                        <p><b>Plan:</b> {plan_type.value.capitalize()}</p>
                        <p>Accede a <a href="https://rfaf-analytics.es">rfaf-analytics.es</a>
                           con tu email y contraseña.</p>
                    </div>
                    """,
                })
                print("Email de bienvenida enviado")
            else:
                print("RESEND_API_KEY no configurada - email no enviado")
        except Exception as e:
            print(f"Error enviando email: {e}")


def main():
    parser = argparse.ArgumentParser(description="Onboard a new club to RFAF Analytics")
    parser.add_argument("--nombre", required=True, help="Club name")
    parser.add_argument("--email", required=True, help="Club/admin email")
    parser.add_argument("--plan", default="basico", choices=["basico", "profesional", "federado"])
    parser.add_argument("--admin-name", default="Entrenador", help="Admin user name")
    parser.add_argument("--admin-password", default="rfaf2026!", help="Initial password")
    args = parser.parse_args()

    asyncio.run(onboard_club(
        nombre=args.nombre,
        email=args.email,
        plan=args.plan,
        admin_name=args.admin_name,
        admin_password=args.admin_password,
    ))


if __name__ == "__main__":
    main()
