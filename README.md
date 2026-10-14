این یک کد ساده برای آموزش و تمارین ما است

ما در این مخزن کد کدهایی مینویسیم که برنامه نویسیمان قوی تر شود.

ما از uv استفاده میکنیم


```
uv sync
```

با زدن دستور بالا تمام نیازمندی های پروژه خود به خود نصب میشوند

البته باید یووی را نصب داشته باشید از قب


```
uv run api-tutorial.py
```

## پلتفرم مقایسه دو RAG

آدرس دو API را با env مشخص کن:

```
RAG_API_A_URL=http://host-a:8001 RAG_API_B_URL=http://host-b:8002 uv run api-tutorial.py
```

مراحل:

1. `POST /ask` — `{"question": "..."}` → `{"id": 0, "answers": [{"id": 0, "text": "..."}, {"id": 1, "text": "..."}]}`
2. `POST /vote` — `{"id": 0, "choice": "0"|"1"|"both"|"neither"}`
3. `GET /results` — امتیاز هر API

ترتیب دو API به‌صورت تصادفی (blind) انتخاب می‌شود و در `data.txt` ذخیره می‌شود.
تست تجمیع رأی‌ها: `uv run test_results.py`
و تمام