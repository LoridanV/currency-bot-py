import os
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
API = "https://open.er-api.com/v6/latest"

CURRENCIES = {
    "RON": "lei românești 🇷🇴",
    "MDL": "lei moldovenești 🇲🇩",
    "UAH": "hrivne ucrainene 🇺🇦",
    "RUB": "ruble rusești 🇷🇺",
    "EUR": "euro 🇪🇺",
    "USD": "dolari americani 🇺🇸",
    "GBP": "lire sterline 🇬🇧",
}

ALIASES = {
    "LEI": "RON",
    "LEU": "RON",
    "HRIVNA": "UAH",
    "HRIVNE": "UAH",
    "RUBLA": "RUB",
    "RUBLE": "RUB",
    "EURO": "EUR",
    "DOLAR": "USD",
    "DOLARI": "USD",
}


def norm(code: str) -> str:
    """Transformă 'hrivna' -> 'UAH', 'eur' -> 'EUR'."""
    code = code.upper()
    return ALIASES.get(code, code)


async def get_rate(base: str, to: str):
    """Ia cursul de schimb de la API."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{API}/{base}")
        r.raise_for_status()
        data = r.json()
        if data.get("result") != "success":
            raise ValueError("Monedă invalidă")
        rate = data["rates"][to]  # KeyError dacă moneda nu există
        date = data["time_last_update_utc"][:16]
        return rate, date


def parse_convert(text: str):
    """Parsează '100 eur ron' -> (100.0, 'EUR', 'RON') sau None."""
    parts = text.strip().split()
    if len(parts) != 3:
        return None
    try:
        amount = float(parts[0].replace(",", "."))
    except ValueError:
        return None
    if amount <= 0:
        return None
    return amount, norm(parts[1]), norm(parts[2])


async def convert(update: Update, text: str):
    parsed = parse_convert(text)
    if not parsed:
        await update.message.reply_text("Folosește: /convert 100 EUR RON")
        return

    amount, base, to = parsed
    try:
        rate, date = await get_rate(base, to)
    except Exception:
        await update.message.reply_text(
            "❌ Nu am găsit una dintre monede. Încearcă /monede pentru listă."
        )
        return

    result = round(amount * rate, 2)
    await update.message.reply_text(
        f"💱 {amount} {base} = {result} {to}\n"
        f"Curs: 1 {base} = {rate} {to}\n"
        f"Actualizat: {date}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salut! Sunt botul tău de convertor valutar 💱\n\n"
        "/rate EUR RON – cursul curent\n"
        "/convert 100 EUR RON – convertește o sumă\n"
        "/monede – lista monedelor principale\n\n"
        "Poți scrie și direct: 100 uah ron"
    )


async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Folosește: /rate EUR RON")
        return
    await convert(update, f"1 {context.args[0]} {context.args[1]}")


async def convert_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await convert(update, " ".join(context.args))


async def monede(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [f"{code} – {name}" for code, name in CURRENCIES.items()]
    await update.message.reply_text(
        "Monede principale:\n"
        + "\n".join(lines)
        + "\n\nPoți folosi orice cod ISO de 3 litere (CHF, PLN etc.)."
    )


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if parse_convert(text):
        await convert(update, text)
    else:
        await update.message.reply_text("Nu am înțeles. Încearcă: 100 eur ron sau /start")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rate", rate))
    app.add_handler(CommandHandler("convert", convert_cmd))
    app.add_handler(CommandHandler("monede", monede))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    print("Botul rulează...")
    app.run_polling()


if __name__ == "__main__":
    main()