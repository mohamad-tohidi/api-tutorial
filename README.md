# RAG Arena

دو سامانه‌ی راگ را با هم مقایسه می‌کند: برای هر سوال دو پاسخ (سمت راست و چپ) نشان می‌دهد و کاربر بدون این‌که بداند هر پاسخ از کدام سامانه است، به آن رأی می‌دهد.

## اجرا

```
uv sync
RAG_API_A_URL=http://host-a:8001 RAG_API_B_URL=http://host-b:8002 uv run app.py
```

بعد `http://localhost:8000` را باز کن.

## فایل‌ها

- `app.py` — روت‌های FastAPI و سرو کردن صفحه‌ی static
- `rag.py` — اتصال به دو API راگ (SSE)
- `db.py` — ذخیره‌سازی SQLite
- `precompute.py` — پیش‌محاسبه‌ی سوالات
- `test_db.py` — تست شمارش رأی‌ها
- `static/` — صفحه‌ی frontend (HTML/CSS و یک فایل کوچک JS)

## پیش‌محاسبه

یک فایل `questions.txt` بساز که هر خطش یک سوال است، بعد:

```
uv run precompute.py questions.txt 4
```

سوالات قبلی دوباره محاسبه نمی‌شوند، پس اجرای مجدد بی‌خطر است.

## روت‌ها

1. `GET /question?index=0` — یک سوال پیش‌محاسبه‌شده با دو پاسخ
   `{"index": 0, "total": 100, "id": 5, "question": "...", "answers": [{"id": 0, "text": "..."}, {"id": 1, "text": "..."}]}`
2. `POST /vote` — `{"id": 5, "choice": "0"|"1"|"both"|"neither"}`
3. `GET /results` — امتیاز سامانه A و B

هر کاربر از مرورگر خودش پیش می‌رود؛ رأی‌ها جمع می‌شوند و در تصویر نتیجه ذخیره می‌شوند.

## تست

```
uv run test_db.py
```
