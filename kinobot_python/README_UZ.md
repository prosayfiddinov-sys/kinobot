# Kino bot — Python (Gift Hub)

## O‘rnatish
1. ZIP faylni oching.
2. `.env.example` faylidan nusxa olib `.env` deb nomlang.
3. `.env` ichiga yangi Telegram bot tokeni, admin ID va kanal ma’lumotlarini kiriting.
4. Gift Hub Python hostingida loyiha fayllarini yuklang.
5. Build/install komandasi: `pip install -r requirements.txt`
6. Start komandasi: `python bot.py`

## Muhim sozlamalar
- `BOT_TOKEN`: BotFather tokeni. PHP faylda ochiq turgan eski tokenni ishlatmang.
- `ADMIN_IDS`: admin Telegram ID raqamlari.
- `MOVIE_CHANNEL`: kino postlari chiqadigan kanal. Botga kanal admin huquqini bering.
- `REQUIRED_CHANNELS`: majburiy obuna kanallari, vergul bilan ajrating.

## Hozirgi Python portidagi funksiyalar
- `/start` va foydalanuvchi menyusi
- Kod orqali kino/multfilm olish
- Majburiy obuna tekshiruvi
- Top 10 va tasodifiy kino
- Admin panel: film/multfilm yuklash, o‘chirish, xabarnoma, statistika
- Kino kanaliga video shablon va yuklab olish tugmasi bilan post chiqarish
- Yuklanishlar sonini hisoblash

## Eslatma
Bu PHP manbaning Python uchun qayta yozilgan porti. PHP dagi barcha eski menyu va ichki holatlar birma-bir aynan ko‘chirilmagan; bu paketda yuqorida sanalgan asosiy oqimlar qayta tashkil qilindi. Avval test bot va yopiq kanal bilan sinab ko‘ring.
