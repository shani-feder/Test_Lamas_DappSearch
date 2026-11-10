# Deep Search mini

שירות קטן שמדגים את ליבת מערכת Deep Search: תשאול מובנה של נתוני תעסוקה ושכר, בלי כתיבת SQL.

השירות נכתב בספרינט האחרון בעזרת סוכן AI.

## הרצה

נדרש Python 3.11 ומעלה. לא נדרש ניסיון קודם ב-FastAPI.

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload
```

Windows:

```
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --reload
```

תיעוד אינטראקטיבי של ה-API: http://localhost:8000/docs
ב-Windows נוח יותר לשלוח את הבקשות משם מאשר ב-curl.

## בדיקות

```bash
.venv/bin/python -m pytest          # Windows: .venv\Scripts\python -m pytest
```

## נתונים

הקובץ `data/person_year.csv` נטען לבסיס נתונים SQLite בזיכרון כשהשירות מתחיל לרוץ. הנתונים סינתטיים.

הקובץ בקידוד UTF-8. כדי לפתוח אותו ב-Excel בלי שהעברית תשתבש: Data > From Text/CSV, ולבחור קידוד UTF-8.

| עמודה | תיאור |
| --- | --- |
| id | מזהה רשומה |
| year | שנה, 2020 עד 2024 |
| gender | F או M |
| age | גיל |
| city | עיר |
| employed | 1 אם מועסק/ת, אחרת 0 |
| monthly_income | שכר חודשי בש"ח. ריק כשהאדם אינו מועסק |

## API

כתובות ה-API ומבנה התשובות משמשים את צד הלקוח. אפשר להוסיף שדות, אבל לא לשנות או להסיר קיימים.

### הרצת שאילתה מובנית

`POST /api/query/run`

```json
{
  "measure": "average",
  "filters": { "gender": "F", "city": "ירושלים", "ageFrom": 25, "ageTo": 35, "yearFrom": 2021, "yearTo": 2024 },
  "groupBy": "year"
}
```

- `measure`: `average` (שכר ממוצע), `sum` (סך השכר), `count` (מספר הרשומות).
- `filters`: כל השדות אופציונליים. טווחי הגיל והשנים כוללים את שני הקצוות.
- `groupBy`: `year`, `gender` או `city`.

### שאלה בשפה חופשית

`POST /api/ask`

```json
{ "text": "מה השכר הממוצע של נשים בירושלים בשנים 2021-2024 לפי שנה" }
```

רכיב ה-LLM ממיר את השאלה להגדרת שאילתה. בסביבת הפיתוח פועל במקומו `MockLLMParser`.

### שאילתות שמורות

אפשר לשמור שאילתה בשם ולהריץ אותה שוב.

- `GET /api/saved`: רשימת השאילתות השמורות.
- `POST /api/saved`: שמירה. גוף הבקשה: `{ "name": "...", "owner": "...", "query": { הגדרת שאילתה } }`.
- `POST /api/saved/{id}/run`: הרצה של שאילתה שמורה.

הקובץ `data/saved_queries.json` מכיל את השאילתות שנשמרו במהלך הפיילוט. השדה `owner` הוא שם המשתמש ששמר את השאילתה.

## בעיות שהתגלו בפיילוט

בקובץ `ISSUES.md`. את הסקירה כותבים בקובץ `REVIEW.md`.

## מבנה

```
app/main.py            נקודות הקצה
app/query_builder.py   בניית ה-SQL מהגדרת השאילתה
app/free_text.py       מענה לשאלה בשפה חופשית
app/llm_parser.py      המרת שאלה חופשית להגדרת שאילתה
app/saved_queries.py   שמירה והרצה של שאילתות שמורות
app/phrasing.py        ניסוח קריא של השאלה
app/db.py              גישה לבסיס הנתונים
tests/                 בדיקות
```
