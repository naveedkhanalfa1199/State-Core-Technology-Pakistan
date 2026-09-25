# FuTuRe FLoW - admin se control hone wali website

Public side normal website hai (Home, About, Services, Portfolio, Contact). Sab content `/admin` se badalta hai.

## Structure
- `app.py` - poori Flask app, models, admin routes (tables `db.create_all()` se khud ban jate hain)
- `seed_data.py` - pehli baar sample content (sirf tab jab database khali ho)
- `templates/` public pages, `templates/admin/` admin panel, `static/` CSS aur JS

## Local chalana
```
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
`DATABASE_URL` na ho to local SQLite use hoti hai. Local admin: `admin` / `change-me-now` (ya `.env` wale ADMIN_* values). Admin panel: http://127.0.0.1:5000/admin

## Supabase (database)
1. Supabase project banao, phir **Connect** mein **Session pooler** ki URI copy karo (Render IPv4 use karta hai, isliye direct connection ki jagah pooler lo).
2. `[YOUR-PASSWORD]` ki jagah apna database password lagao. Yehi `DATABASE_URL` hai.
3. Images ke liye Supabase **Storage** mein *public* bucket banao, image upload karo, **Get public URL** copy karo, aur admin panel mein "Image link" mein paste kar do.

## Render (hosting)
1. Code GitHub par push karo.
2. Render: **New > Blueprint** (ye `render.yaml` parh lega) ya **New > Web Service**.
3. Environment variables set karo: `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` (`SECRET_KEY` khud ban jati hai).
4. Pehli baar chalne par tables ban jate hain aur pehla admin aur sample content ban jata hai.
5. `/admin` par login karo, phir **Change password** se password badal do.

## Zaroori baatein
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` sirf pehla admin banate waqt use hote hain. Baad mein password panel se badlo.
- `create_all()` naye tables banata hai, purane tables mein naye columns nahi jodta. Baad mein models badlo to Flask-Migrate (Alembic) use karna.
- Admin login 5 galat koshishon ke baad 15 minute ke liye lock ho jata hai.
- Sample testimonials, projects aur prices sirf namoona hain. Apne asli content se badal do.
