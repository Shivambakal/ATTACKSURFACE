import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(".env")
from app.db import SessionLocal
from sqlalchemy import func, text
from app.models import Change, ResearchSignal, Target, Company, Asset
from app.models.source_registry import RawSourceSnapshot, SourceCollectionRun, CompanySource
db = SessionLocal()
print("=== GROUND TRUTH FROM SUPABASE ===")
print("Companies:", db.query(func.count(Company.id)).scalar())
print("Targets:", db.query(func.count(Target.id)).scalar())
print("Assets:", db.query(func.count(Asset.id)).scalar())
print("Changes:", db.query(func.count(Change.id)).scalar())
print("Research_Signals:", db.query(func.count(ResearchSignal.id)).scalar())
print("Raw_Snapshots:", db.query(func.count(RawSourceSnapshot.id)).scalar())
print("Collection_Runs:", db.query(func.count(SourceCollectionRun.id)).scalar())
print("Source_Configs:", db.query(func.count(CompanySource.id)).scalar())
print()
print("=== ALL TABLES IN PUBLIC SCHEMA ===")
tables = db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).fetchall()
for t in tables:
    name = t[0]
    try:
        cnt = db.execute(text(f"SELECT count(*) FROM {name}")).scalar()
        print(f"  {name}: {cnt}")
    except Exception as e:
        print(f"  {name}: ERROR {e}")
db.close()
